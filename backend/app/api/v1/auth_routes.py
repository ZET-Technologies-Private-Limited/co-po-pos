"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database.connection_manager import get_session
from app.core.security.jwt_auth import create_tokens, get_current_user
from app.core.database.models import User
from app.core.config.settings import get_settings
from app.modules.user.services.user_service import UserService
from app.api.schemas import (
    UserLoginRequest, UserRegisterRequest, UserResponse, TokenResponse
)
from app.core.logging.system_logger import SystemLogger

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = SystemLogger("auth_routes")
user_service = UserService()
settings = get_settings()


@router.post("/register", response_model=UserResponse)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_session)
) -> UserResponse:
    """Register new user"""
    try:
        logger.info(f"Registration attempt for {request.email}")
        
        # Create user
        user = await user_service.create_user(
            session,
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
            department=request.department
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed. Email may already exist."
            )
        
        await session.commit()
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            department=user.department,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """User login"""
    try:
        logger.info(f"Login attempt for {request.email}")
        
        # Authenticate user
        user = await user_service.authenticate_user(
            session,
            request.email,
            request.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create tokens
        tokens = create_tokens(
            user_id=user.id,
            email=user.email,
            role=user.role
        )
        
        return TokenResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            expires_in=int(settings.access_token_expire_minutes * 60)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current user info"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Change password"""
    try:
        logger.info(f"Password change for user {current_user.id}")
        
        success = await user_service.change_password(
            session,
            current_user.id,
            old_password,
            new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change failed. Invalid old password."
            )
        
        await session.commit()
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/verify-email")
async def verify_email(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Verify user email"""
    try:
        success = await user_service.verify_user(session, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification failed"
            )
        
        await session.commit()
        
        return {
            "success": True,
            "message": "Email verified successfully"
        }
    
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Logout (client should discard token)"""
    logger.info(f"Logout for user {current_user.id}")
    return {
        "success": True,
        "message": "Logged out successfully"
    }
