"""
Authentication and authorization module for Mind Bridge AI.
Handles JWT tokens, user authentication, and security middleware.
"""

import re
import logging
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status, Request, 
    BackgroundTasks, Response
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config import settings
from database import get_db
from models import User, MoodLevel

# Configure logging
logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis connection for rate limiting and token blacklisting
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Redis connection established for auth module")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# Pydantic Models
class UserRegister(BaseModel):
    """User registration request model."""
    email: EmailStr
    password: str
    baseline_mood: MoodLevel
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    privacy_settings: Optional[Dict[str, Any]] = None

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

    @validator('emergency_contact_phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and not re.match(r'^\+?[\d\s\-\(\)]{10,20}$', v):
            raise ValueError('Invalid phone number format')
        return v

class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserProfile(BaseModel):
    """User profile response model."""
    id: str
    email: str
    baseline_mood: str
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    is_active: bool
    email_verified: bool
    privacy_settings: Dict[str, Any]
    created_at: str
    updated_at: Optional[str]

class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str

class LogoutRequest(BaseModel):
    """Logout request model."""
    refresh_token: str

# JWT Utilities
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is blacklisted
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    if not redis_client:
        return False
    
    try:
        return redis_client.exists(f"blacklist:{token}") > 0
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        return False

def blacklist_token(token: str, expires_in: int = None) -> bool:
    """Add token to blacklist."""
    if not redis_client:
        return False
    
    try:
        if expires_in is None:
            # Get token expiration from JWT payload
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            expires_in = payload.get("exp", 0) - int(datetime.utcnow().timestamp())
        
        if expires_in > 0:
            redis_client.setex(f"blacklist:{token}", expires_in, "1")
            return True
        return False
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        return False

# Password Utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

# Rate Limiting
def check_rate_limit(identifier: str, limit: int, window: int) -> bool:
    """Check if request is within rate limit."""
    if not redis_client:
        return True  # Allow if Redis is not available
    
    try:
        key = f"rate_limit:{identifier}"
        current = redis_client.incr(key)
        
        if current == 1:
            redis_client.expire(key, window)
        
        return current <= limit
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Allow if check fails

# Input Sanitization
def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks."""
    if not text:
        return text
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text)
    # Limit length
    return sanitized[:1000]

# Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

# Security Middleware
class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for input sanitization and basic protection."""
    
    async def dispatch(self, request: Request, call_next):
        # Sanitize query parameters
        if request.query_params:
            sanitized_params = {}
            for key, value in request.query_params.items():
                sanitized_params[key] = sanitize_input(value)
            request._query_params = sanitized_params
        
        response = await call_next(request)
        return response

# Rate Limiting Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Check rate limit
        if not check_rate_limit(client_ip, self.calls, self.period):
            return Response(
                content="Rate limit exceeded",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(self.period)}
            )
        
        response = await call_next(request)
        return response

# Router
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            baseline_mood=user_data.baseline_mood,
            emergency_contact_name=sanitize_input(user_data.emergency_contact_name) if user_data.emergency_contact_name else None,
            emergency_contact_phone=user_data.emergency_contact_phone,
            privacy_settings=user_data.privacy_settings or {},
            is_active=True,
            email_verified=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(new_user.id)})
        refresh_token = create_refresh_token(data={"sub": str(new_user.id)})
        
        logger.info(f"User registered successfully: {new_user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Dict[str, Any])
async def login(
    user_credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens."""
    # Get client IP for rate limiting
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    # Check rate limit for login attempts
    if not check_rate_limit(f"login:{client_ip}", settings.LOGIN_RATE_LIMIT_REQUESTS, settings.LOGIN_RATE_LIMIT_WINDOW):
        logger.warning(f"Login rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(settings.LOGIN_RATE_LIMIT_WINDOW)}
        )
    
    try:
        # Find user
        user = db.query(User).filter(User.email == user_credentials.email).first()
        if not user or not verify_password(user_credentials.password, user.password_hash):
            logger.warning(f"Failed login attempt for email: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is deactivated"
            )
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": UserProfile(**user.to_dict())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify user still exists and is active
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=token_data.refresh_token,  # Keep the same refresh token
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout")
async def logout(
    token_data: LogoutRequest,
    current_user: User = Depends(get_current_user)
):
    """Logout user and blacklist refresh token."""
    try:
        # Blacklist the refresh token
        blacklist_token(token_data.refresh_token)
        
        logger.info(f"User logged out: {current_user.email}")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return UserProfile(**current_user.to_dict())

@router.put("/profile", response_model=UserProfile)
async def update_profile(
    profile_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    try:
        # Sanitize input data
        sanitized_data = {}
        for key, value in profile_data.items():
            if isinstance(value, str):
                sanitized_data[key] = sanitize_input(value)
            else:
                sanitized_data[key] = value
        
        # Update allowed fields
        allowed_fields = [
            'baseline_mood', 'emergency_contact_name', 
            'emergency_contact_phone', 'privacy_settings'
        ]
        
        for field in allowed_fields:
            if field in sanitized_data:
                setattr(current_user, field, sanitized_data[field])
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Profile updated for user: {current_user.email}")
        
        return UserProfile(**current_user.to_dict())
        
    except Exception as e:
        db.rollback()
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )

# Health check endpoint
@router.get("/health")
async def auth_health():
    """Health check for auth module."""
    redis_status = "connected" if redis_client and redis_client.ping() else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "jwt_algorithm": settings.ALGORITHM,
        "token_expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
    }