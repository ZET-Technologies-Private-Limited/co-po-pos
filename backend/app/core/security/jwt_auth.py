"""
JWT authentication and token management
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from pydantic import BaseModel
from app.core.config.settings import get_settings
from app.core.database.connection_manager import get_session
from app.core.database.models import User


class TokenPayload(BaseModel):
    sub: str  # subject (user_id)
    user_id: str
    username: str
    role: str
    exp: datetime
    iat: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class JWTManager:
    """JWT token generation and validation"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def create_tokens(
        self,
        user_id: str,
        username: str,
        role: str,
    ) -> TokenResponse:
        """Create access and refresh tokens"""
        access_token = self._create_access_token(
            data={"sub": user_id, "username": username, "role": role}
        )
        refresh_token = self._create_refresh_token(
            data={"sub": user_id}
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_expire_minutes * 60,
        )
    
    def _create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.settings.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.secret_key,
            algorithm=self.settings.jwt_algorithm
        )
        
        return encoded_jwt
    
    def _create_refresh_token(
        self,
        data: Dict[str, Any]
    ) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=self.settings.refresh_token_expire_days
        )
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.secret_key,
            algorithm=self.settings.jwt_algorithm
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            # Support both token formats used in the codebase:
            # - JWTManager: {sub, username, role, exp, iat}
            # - AuthService: {user_id, exp}
            user_id: str = payload.get("sub") or payload.get("user_id")
            username: str = payload.get("username") or ""
            role: str = payload.get("role") or "faculty"
            
            if user_id is None:
                return None

            exp_value = payload.get("exp")
            iat_value = payload.get("iat") or datetime.utcnow().timestamp()

            if exp_value is None:
                return None

            exp_dt = exp_value if isinstance(exp_value, datetime) else datetime.fromtimestamp(exp_value)
            iat_dt = iat_value if isinstance(iat_value, datetime) else datetime.fromtimestamp(iat_value)
            
            return TokenPayload(
                sub=user_id,
                user_id=user_id,
                username=username,
                role=role,
                exp=exp_dt,
                iat=iat_dt,
            )
        
        except (JWTError, TypeError, ValueError):
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token from a valid refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                self.settings.secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("sub")
            username = payload.get("username", "")
            role = payload.get("role", "viewer")

            return self._create_access_token(
                data={"sub": user_id, "username": username, "role": role}
            )

        except JWTError:
            return None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
jwt_manager = JWTManager()


def _get_role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role).lower()


def _is_faculty_authoring_path(path: str) -> bool:
    governance_exceptions = (
        "/co-defaults",
        "/co-unlock",
    )
    if any(path.endswith(suffix) for suffix in governance_exceptions):
        return False

    return (
        path == "/api/v1/courses"
        or path.startswith("/api/v1/courses/")
        or path.startswith("/api/v1/exams/")
        or (path.startswith("/api/v1/marks/") and path.endswith("/submit"))
    )


def _is_marks_approval_path(path: str) -> bool:
    return path.startswith("/api/v1/marks/") and (path.endswith("/approve") or path.endswith("/unlock"))


def _is_po_pso_master_mutation(path: str) -> bool:
    return path.startswith("/api/v1/programs/") and ("/outcomes" in path or "/pso" in path)


def _is_attainment_management_path(path: str) -> bool:
    return path.startswith("/api/v1/attainment/")


def _enforce_rbac_policy(user: User, method: str, path: str) -> None:
    role = _get_role_value(user)
    is_mutation = method in {"POST", "PUT", "PATCH", "DELETE"}

    if path == "/api/v1/chatbot/message" and method == "POST" and role not in {"faculty", "hod", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can use chatbot generation endpoints",
        )

    # Faculty authoring endpoints are faculty-only by matrix.
    if _is_faculty_authoring_path(path) and is_mutation and role != "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can perform academic authoring actions",
        )

    # Marks approval workflow is for lead/hod/admin only.
    if _is_marks_approval_path(path) and role not in {"accreditation_officer", "hod", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lead/hod/admin can approve or unlock marks",
        )

    # PO/PSO master management is for hod/admin only.
    if _is_po_pso_master_mutation(path) and is_mutation and role not in {"hod", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HOD/Admin can modify PO/PSO masters",
        )

    # Admin bypass for non-overridden policy areas.
    if role == "admin":
        return

    # Student/viewer role: read-only, limited student-safe surface.
    if role == "viewer":
        viewer_allowed = (
            (method == "GET" and path == "/api/v1/courses")
            or (method == "GET" and path.startswith("/api/v1/courses/"))
            or (method == "GET" and path.startswith("/api/v1/attainment/course/"))
            or (method == "GET" and path.startswith("/api/v1/visualization/"))
        )
        if not viewer_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewer role has read-only student-limited access",
            )
        return

    # Course Lead (mapped to accreditation_officer): approval and analytics, no authoring.
    if role == "accreditation_officer":
        if path in {"/api/v1/map-co-po", "/api/v1/map-co-pso"} and method == "POST":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Course lead cannot create CO-PO/PSO mappings",
            )

        return

    # Faculty: can author course/exam/marks; route-level ownership checks apply.
    if role == "faculty":
        return

    # HOD: full academic control allowed for current API surface.
    if role == "hod":
        return


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the authenticated user from bearer token."""
    payload = jwt_manager.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await session.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    _enforce_rbac_policy(user, request.method, request.url.path)

    return user


def create_tokens(user_id: str, email: str, role: str) -> Dict[str, Any]:
    """Compatibility helper used by legacy auth routes."""
    tokens = jwt_manager.create_tokens(user_id=user_id, username=email, role=role)
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
    }


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """Generate a new access token from a refresh token."""
    try:
        payload = jwt.decode(
            refresh_token,
            jwt_manager.settings.secret_key,
            algorithms=[jwt_manager.settings.jwt_algorithm],
        )

        if payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        username = payload.get("username", "")
        role = payload.get("role", "viewer")

        return jwt_manager._create_access_token(
            data={"sub": user_id, "username": username, "role": role}
        )

    except JWTError:
        return None
