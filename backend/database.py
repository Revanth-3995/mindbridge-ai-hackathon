"""
Database configuration and session management.
Supports PostgreSQL with SQLite fallback, connection pooling, and retry logic.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging
from typing import Generator
import time
from contextlib import contextmanager

from config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Database engine configuration
engine_kwargs = {
    "poolclass": QueuePool,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "pool_pre_ping": True,  # Verify connections before use
    "echo": settings.DEBUG,  # Log SQL queries in debug mode
}

# Create database engine with retry logic
def create_database_engine():
    """Create database engine with retry logic and fallback."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Try PostgreSQL first
            if not settings.USE_SQLITE_FALLBACK:
                engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
                # Test connection
                with engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to PostgreSQL database")
                return engine
            else:
                # Use the database URL from settings (which handles fallback)
                engine = create_engine(settings.database_url, **engine_kwargs)
                # Test connection
                with engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("SELECT 1"))
                db_type = "SQLite" if "sqlite" in settings.database_url else "PostgreSQL"
                logger.info(f"Successfully connected to {db_type} database")
                return engine
                
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                if settings.USE_SQLITE_FALLBACK and "sqlite" not in str(e):
                    logger.error("PostgreSQL connection failed, falling back to SQLite")
                    try:
                        engine = create_engine(settings.SQLITE_URL, **engine_kwargs)
                        with engine.connect() as conn:
                            from sqlalchemy import text
                            conn.execute(text("SELECT 1"))
                        logger.info("Successfully connected to SQLite fallback database")
                        return engine
                    except Exception as sqlite_error:
                        logger.error(f"SQLite fallback also failed: {sqlite_error}")
                        raise sqlite_error
                else:
                    raise e

# Create engine
engine = create_database_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Connection event listeners for better error handling
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance and compatibility."""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=1000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout events."""
    logger.debug("Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin events."""
    logger.debug("Connection checked in to pool")

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Provides automatic session management with error handling.
    """
    db = SessionLocal()
    try:
        yield db
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Provides explicit session management.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    try:
        # Import all models to ensure they are registered
        from models import User, ChatSession, Message, AIResponse
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def check_db_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))

        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def get_db_info() -> dict:
    """Get database connection information."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT version()")).fetchone()

            return {
                "connected": True,
                "version": result[0] if result else "Unknown",
                "url": str(engine.url).replace(engine.url.password or "", "***") if engine.url.password else str(engine.url)
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "url": str(engine.url).replace(engine.url.password or "", "***") if engine.url.password else str(engine.url)
        }
