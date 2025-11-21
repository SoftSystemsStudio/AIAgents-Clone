"""
API Authentication - JWT tokens and customer verification.

Provides secure authentication for the Gmail cleanup API.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.domain.customer import Customer, CustomerStatus

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_USE_LONG_RANDOM_STRING")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer()


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


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(customer: Customer, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token for customer.
    
    Args:
        customer: Customer to create token for
        expires_delta: Token expiration time (default 24 hours)
        
    Returns:
        JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(customer.id),  # Subject (customer ID)
        "email": customer.email,
        "plan_tier": customer.plan_tier.value,
        "exp": expire,
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    # TODO: Add customer_repository dependency here
) -> Customer:
    """
    Get current authenticated customer from JWT token.
    
    This is a FastAPI dependency that:
    1. Extracts JWT from Authorization header
    2. Verifies token signature
    3. Loads customer from database
    4. Returns Customer object
    
    Usage in endpoints:
        @app.get("/api/v1/me")
        async def get_me(customer: Customer = Depends(get_current_customer)):
            return {"email": customer.email}
    
    Raises:
        HTTPException 401: If token invalid or customer not found
    """
    token = credentials.credentials
    token_data = decode_token(token)
    
    # TODO: Load customer from database
    # customer = await customer_repository.get_by_id(UUID(token_data.customer_id))
    # if not customer:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Customer not found"
    #     )
    # if customer.status != CustomerStatus.ACTIVE:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Account is suspended or cancelled"
    #     )
    # return customer
    
    # For now, return mock customer from token data
    # REPLACE THIS with actual database lookup
    from src.domain.customer import PlanTier
    return Customer(
        id=UUID(token_data.customer_id),
        email=token_data.email,
        name="Mock User",
        password_hash="",
        plan_tier=PlanTier(token_data.plan_tier),
        status=CustomerStatus.ACTIVE,
    )


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
