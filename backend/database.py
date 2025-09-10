"""
Robust database configuration and session management.
Supports PostgreSQL with SQLite fallback, connection pooling, retry logic, and health checks.
"""

import os
import time
import logging
from typing import Generator, Dict, Any, Optional
from contextlib import contextmanager
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import (
    OperationalError, DisconnectionError, ProgrammingError, 
    IntegrityError, DatabaseError
)
from sqlalchemy.engine import Engine
from sqlalchemy.engine.events import PoolEvents

from config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Database configuration constants
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2
HEALTH_CHECK_TIMEOUT = 5

# Database engine configuration for PostgreSQL
postgresql_engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "pool_pre_ping": True,  # Verify connections before use
    "echo": settings.DEBUG,  # Log SQL queries in debug mode
    "connect_args": {
        "connect_timeout": 10,
        "application_name": "mindbridge_ai"
    }
}

# Database engine configuration for SQLite
sqlite_engine_kwargs = {
    "poolclass": StaticPool,
    "pool_size": 1,
    "max_overflow": 0,
    "pool_timeout": 30,
    "pool_recycle": -1,
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
    "connect_args": {
        "check_same_thread": False,
        "timeout": 20
    }
}

def test_database_connection(database_url: str, engine_kwargs: Dict[str, Any]) -> bool:
    """Test database connection with timeout."""
    try:
        test_engine = create_engine(database_url, **engine_kwargs)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return True
    except Exception as e:
        logger.debug(f"Connection test failed: {e}")
        return False

def create_database_engine() -> Engine:
    """Create database engine with robust retry logic and fallback."""
    logger.info("Initializing database connection...")
    
    # Check environment variables for database preference
    database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    use_sqlite_fallback = os.getenv("USE_SQLITE_FALLBACK", str(settings.USE_SQLITE_FALLBACK)).lower() == "true"
    
    # Try PostgreSQL first if not explicitly using SQLite
    if not use_sqlite_fallback and database_url.startswith("postgresql://"):
        logger.info("Attempting PostgreSQL connection...")
        
        for attempt in range(MAX_RETRIES):
            try:
                if test_database_connection(database_url, postgresql_engine_kwargs):
                    engine = create_engine(database_url, **postgresql_engine_kwargs)
                    logger.info("✅ Successfully connected to PostgreSQL database")
                    return engine
                else:
                    raise OperationalError("Connection test failed", None, None)
                    
            except Exception as e:
                retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"PostgreSQL connection attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("PostgreSQL connection failed after all retries")
                    if use_sqlite_fallback:
                        logger.info("Falling back to SQLite...")
                        break
                    else:
                        raise e
    
    # Fallback to SQLite
    logger.info("Attempting SQLite connection...")
    sqlite_url = os.getenv("SQLITE_URL", settings.SQLITE_URL)
    
    for attempt in range(MAX_RETRIES):
        try:
            if test_database_connection(sqlite_url, sqlite_engine_kwargs):
                engine = create_engine(sqlite_url, **sqlite_engine_kwargs)
                logger.info("✅ Successfully connected to SQLite database")
                return engine
            else:
                raise OperationalError("SQLite connection test failed", None, None)
                
        except Exception as e:
            retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
            logger.warning(f"SQLite connection attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("SQLite connection failed after all retries")
                raise e
    
    # This should never be reached, but just in case
    raise RuntimeError("Failed to establish any database connection")

# Create engine
engine = create_database_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Connection event listeners for better error handling and monitoring
@event.listens_for(engine, "connect")
def set_database_pragmas(dbapi_connection, connection_record):
    """Set database-specific pragmas and configurations."""
    if "sqlite" in str(dbapi_connection):
        # SQLite-specific optimizations
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=1000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            cursor.execute("PRAGMA optimize")
            logger.debug("SQLite pragmas configured")
        except Exception as e:
            logger.warning(f"Failed to set SQLite pragmas: {e}")
        finally:
            cursor.close()
    elif "postgresql" in str(dbapi_connection):
        # PostgreSQL-specific configurations
        logger.debug("PostgreSQL connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout events."""
    logger.debug("Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin events."""
    logger.debug("Connection checked in to pool")

@event.listens_for(engine, "invalidate")
def receive_invalidate(dbapi_connection, connection_record, exception):
    """Handle connection invalidation events."""
    logger.warning(f"Connection invalidated: {exception}")

@event.listens_for(engine, "soft_invalidate")
def receive_soft_invalidate(dbapi_connection, connection_record, exception):
    """Handle soft connection invalidation events."""
    logger.debug(f"Connection soft invalidated: {exception}")

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    Provides automatic session management with comprehensive error handling.
    """
    db = SessionLocal()
    try:
        yield db
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Database connection error: {e}")
        db.rollback()
        raise
    except (IntegrityError, ProgrammingError) as e:
        logger.error(f"Database integrity/programming error: {e}")
        db.rollback()
        raise
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Provides explicit session management with automatic commit/rollback.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
        logger.debug("Database transaction committed")
    except Exception as e:
        logger.error(f"Database error in context manager: {e}")
        db.rollback()
        logger.debug("Database transaction rolled back")
        raise
    finally:
        db.close()

@contextmanager
def get_db_transaction():
    """
    Context manager for database transactions.
    Provides explicit transaction control with rollback on exception.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
        logger.debug("Database transaction committed")
    except Exception as e:
        logger.error(f"Database error in transaction: {e}")
        db.rollback()
        logger.debug("Database transaction rolled back")
        raise
    finally:
        db.close()

def init_db():
    """Initialize database tables with comprehensive error handling."""
    try:
        # Import all models to ensure they are registered
        from models import User, EmotionRecord, PeerConnection, CrisisAlert, ChatMessage, AIResponse
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        expected_tables = ["users", "emotion_records", "peer_connections", "crisis_alerts", "chat_messages", "ai_responses"]
        
        missing_tables = [table for table in expected_tables if table not in table_names]
        if missing_tables:
            logger.warning(f"Some tables were not created: {missing_tables}")
        
        logger.info(f"✅ Database tables initialized successfully. Created: {len(table_names)} tables")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise

def check_db_connection() -> bool:
    """Comprehensive database health check."""
    try:
        with engine.connect() as conn:
            # Basic connectivity test
            conn.execute(text("SELECT 1"))
            
            # Test transaction capability
            trans = conn.begin()
            try:
                conn.execute(text("SELECT 1"))
                trans.rollback()
            except Exception:
                trans.rollback()
                raise
            
            # Test table access if tables exist
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            if table_names:
                # Test querying a table
                first_table = table_names[0]
                conn.execute(text(f"SELECT COUNT(*) FROM {first_table} LIMIT 1"))
        
        logger.debug("✅ Database health check passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False

def get_db_info() -> Dict[str, Any]:
    """Get comprehensive database connection information."""
    try:
        with engine.connect() as conn:
            # Get database version
            if "postgresql" in str(engine.url):
                result = conn.execute(text("SELECT version()")).fetchone()
                version = result[0] if result else "Unknown"
                db_type = "PostgreSQL"
            elif "sqlite" in str(engine.url):
                result = conn.execute(text("SELECT sqlite_version()")).fetchone()
                version = result[0] if result else "Unknown"
                db_type = "SQLite"
            else:
                version = "Unknown"
                db_type = "Unknown"
            
            # Get table count
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            
            # Get connection pool info
            pool = engine.pool
            pool_info = {
                "size": getattr(pool, 'size', lambda: 0)(),
                "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
                "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
                "overflow": getattr(pool, 'overflow', lambda: 0)(),
            }
            
            # Mask password in URL
            url_str = str(engine.url)
            if engine.url.password:
                url_str = url_str.replace(engine.url.password, "***")
            
            return {
                "connected": True,
                "type": db_type,
                "version": version,
                "url": url_str,
                "tables": table_names,
                "table_count": len(table_names),
                "pool": pool_info,
                "timestamp": time.time()
            }
            
    except Exception as e:
        url_str = str(engine.url)
        if engine.url.password:
            url_str = url_str.replace(engine.url.password, "***")
            
        return {
            "connected": False,
            "type": "Unknown",
            "version": "Unknown",
            "url": url_str,
            "error": str(e),
            "timestamp": time.time()
        }

def get_database_stats() -> Dict[str, Any]:
    """Get detailed database statistics."""
    try:
        with engine.connect() as conn:
            stats = {"connected": True}
            
            if "postgresql" in str(engine.url):
                # PostgreSQL-specific stats
                result = conn.execute(text("""
                    SELECT 
                        pg_database_size(current_database()) as db_size,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections
                """)).fetchone()
                
                if result:
                    stats.update({
                        "database_size_bytes": result[0],
                        "active_connections": result[1]
                    })
                    
            elif "sqlite" in str(engine.url):
                # SQLite-specific stats
                result = conn.execute(text("SELECT page_count * page_size as db_size FROM pragma_page_count(), pragma_page_size()")).fetchone()
                if result:
                    stats["database_size_bytes"] = result[0]
            
            # Get table sizes
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            table_stats = {}
            
            for table_name in table_names:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()
                    table_stats[table_name] = result[0] if result else 0
                except Exception as e:
                    table_stats[table_name] = f"Error: {e}"
            
            stats["table_counts"] = table_stats
            return stats
            
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }

def reset_database():
    """Reset database by dropping and recreating all tables."""
    try:
        logger.warning("⚠️ Resetting database - all data will be lost!")
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")
        
        # Recreate all tables
        init_db()
        logger.info("✅ Database reset completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise
