"""
Authentication API routes with JWT token management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.core.database.connection_manager import get_db_session
from app.core.logging.system_logger import SystemLogger
from app.modules.auth.services.auth_service import AuthService
from datetime import datetime

logger = SystemLogger("auth_routes")
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., max_length=255)
    department: Optional[str] = Field(None, max_length=255)


class RegisterResponse(BaseModel):
    """User registration response"""
    id: str
    username: str
    email: str
    full_name: str
    role: str
    message: str


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """User login response"""
    access_token: str
    refresh_token: str
    token_type: str
    user: dict


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response"""
    access_token: str
    token_type: str


class UserProfileResponse(BaseModel):
    """User profile response"""
    id: str
    username: str
    email: str
    full_name: str
    role: str
    department: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Register a new user"""
    try:
        user_data = await auth_service.register_user(
            session=session,
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role="viewer",
            department=request.department
        )
        
        await session.commit()
        
        return RegisterResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            message="User registered successfully"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Authenticate user and return JWT tokens"""
    try:
        user = await auth_service.authenticate_user(
            session=session,
            email=request.email,
            password=request.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        access_token = auth_service.create_access_token(
            user_id=user["id"],
            role=user["role"]
        )
        
        refresh_token = auth_service.create_refresh_token(
            user_id=user["id"]
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: TokenRefreshRequest):
    """Refresh expired access token"""
    try:
        payload = auth_service.verify_token(request.refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        new_access_token = auth_service.create_access_token(
            user_id=payload["sub"],
            role=payload.get("role", "viewer")
        )
        
        return TokenRefreshResponse(
            access_token=new_access_token,
            token_type="bearer"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current authenticated user profile"""
    try:
        payload = auth_service.verify_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        user_data = await auth_service.get_user_by_id(session, user_id)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfileResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            department=user_data.get("department"),
            is_active=user_data["is_active"],
            is_verified=user_data["is_verified"],
            created_at=user_data["created_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )
