"""
API Authentication - JWT tokens and customer verification.

Authentication helpers for JWT and Supabase-backed flows.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

from src.domain.customer import Customer, CustomerStatus
from src.config import get_config

# HTTP Bearer token security
security = HTTPBearer()


def _auth_config():
    return get_config().auth


def _internal_secret_key() -> str:
    return _auth_config().jwt_secret_key


def _supabase_secret_key() -> str:
    auth = _auth_config()
    return auth.supabase_jwt_secret or auth.jwt_secret_key


class TokenData(BaseModel):
    """JWT token payload"""
    customer_id: str
    email: str
    plan_tier: str
    exp: datetime


class LoginRequest(BaseModel):
    """Login request payload"""
    email: str
    password: str


class SignupRequest(BaseModel):
    """Signup request payload"""
    email: str
    password: str
    name: Optional[str] = None


class TokenResponse(BaseModel):
    """API token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    customer: dict


class SupabaseUser(BaseModel):
    """Parsed Supabase JWT payload."""

    user_id: str
    email: Optional[str] = None
    role: Optional[str] = None
    aud: Optional[str] = None
    exp: datetime


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(customer: Customer, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token for customer.
    
    Args:
        customer: Customer to create token for
        expires_delta: Token expiration time (default 24 hours)
        
    Returns:
        JWT token string
    """
    auth = _auth_config()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=auth.access_token_expire_minutes
        )
    
    to_encode = {
        "sub": str(customer.id),  # Subject (customer ID)
        "email": customer.email,
        "plan_tier": customer.plan_tier.value,
        "exp": expire,
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        _internal_secret_key(),
        algorithm=auth.jwt_algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with customer info
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        auth = _auth_config()
        payload = jwt.decode(
            token,
            _internal_secret_key(),
            algorithms=[auth.jwt_algorithm],
        )
        customer_id: str = payload.get("sub")
        email: str = payload.get("email")
        plan_tier: str = payload.get("plan_tier")
        
        if customer_id is None or email is None:
            raise credentials_exception
        
        return TokenData(
            customer_id=customer_id,
            email=email,
            plan_tier=plan_tier,
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
    except JWTError:
        raise credentials_exception


def decode_supabase_token(token: str) -> SupabaseUser:
    """Decode and verify a Supabase-issued JWT token using the configured secret."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate Supabase credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    secret = _supabase_secret_key()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret is not configured",
        )

    try:
        auth = _auth_config()
        payload = jwt.decode(token, secret, algorithms=[auth.jwt_algorithm])
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        exp_value = payload.get("exp")
        if not user_id or not exp_value:
            raise credentials_exception

        return SupabaseUser(
            user_id=user_id,
            email=payload.get("email"),
            role=payload.get("role"),
            aud=payload.get("aud"),
            exp=datetime.fromtimestamp(exp_value),
        )
    except JWTError:
        raise credentials_exception


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Customer:
    """
    Get current authenticated customer from JWT token.
    
    This is a FastAPI dependency that:
    1. Extracts JWT from Authorization header
    2. Verifies token signature
    3. Loads customer from repository
    4. Returns Customer object
    
    Usage in endpoints:
        @app.get("/api/v1/me")
        async def get_me(customer: Customer = Depends(get_current_customer)):
            return {"email": customer.email}
    
    Raises:
        HTTPException 401: If token invalid or customer not found
    """
    from src.infrastructure.customer_repository import customer_repository
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    # Load customer from repository
    customer = customer_repository.get_by_id(UUID(token_data.customer_id))
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found"
        )
    
    if customer.status != CustomerStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or cancelled"
        )
    
    return customer


async def get_supabase_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> SupabaseUser:
    """Validate a Supabase-authenticated user via the Authorization bearer token."""

    token = credentials.credentials
    return decode_supabase_token(token)


def require_paid_plan(customer: Customer = Depends(get_current_customer)) -> Customer:
    """
    Dependency that requires customer to be on paid plan.
    
    Usage:
        @app.post("/api/v1/premium-feature")
        async def premium_feature(customer: Customer = Depends(require_paid_plan)):
            # Only paid customers can access this
            pass
    """
    if not customer.is_paid_plan():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a paid plan. Please upgrade."
        )
    return customer


def require_feature(feature_name: str):
    """
    Dependency factory that requires customer to have specific feature.
    
    Usage:
        @app.post("/api/v1/schedule-cleanup")
        async def schedule_cleanup(
            customer: Customer = Depends(require_feature("scheduled_cleanups"))
        ):
            pass
    """
    def check_feature(customer: Customer = Depends(get_current_customer)) -> Customer:
        if not customer.has_feature(feature_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature ({feature_name}) requires plan upgrade"
            )
        return customer
    return check_feature


# API Key authentication (alternative to JWT)
async def get_current_customer_from_api_key(
    api_key: str,
    # TODO: Add api_key_repository dependency
) -> Customer:
    """
    Authenticate customer using API key instead of JWT.
    
    Useful for:
    - Server-to-server integration
    - CLI tools
    - Webhook callbacks
    
    API keys should be stored hashed in database and rate-limited.
    """
    # TODO: Implement API key lookup
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key authentication not yet implemented"
    )
