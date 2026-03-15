from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid
from datetime import datetime, timedelta
import jwt

from app.core.database.models import User
from app.core.config.constants import UserRole
from app.core.security.password_hashing import hash_password, verify_password
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("auth_service")
settings = get_settings()


ROLE_ALIASES = {
    "student": UserRole.VIEWER.value,
    "lead": UserRole.ACCREDITATION_OFFICER.value,
    "course_lead": UserRole.ACCREDITATION_OFFICER.value,
}


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def register_user(
        self, username: str, email: str, password: str,
        full_name: str, role: str = "faculty", department: str | None = None
    ) -> User:
        normalized_role = self._normalize_role(role)

        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"User with email {email} already exists")
        
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=normalized_role,
            department=department,
        )
        self.session.add(user)
        await self.session.commit()
        logger.info(f"User registered: {user.id} ({email})")
        return user

    @staticmethod
    def _normalize_role(role: str) -> str:
        raw_role = (role or "faculty").strip().lower()
        mapped_role = ROLE_ALIASES.get(raw_role, raw_role)
        valid_roles = {r.value for r in UserRole}
        if mapped_role not in valid_roles:
            raise ValueError(
                f"Invalid role '{role}'. Allowed roles: {', '.join(sorted(valid_roles))}. "
                f"Aliases: {', '.join(sorted(ROLE_ALIASES.keys()))}."
            )
        return mapped_role
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt for {email}")
            return None
        
        logger.info(f"User authenticated: {user.id}")
        return user
    
    def create_access_token(self, user_id: str, expires_delta: Optional[timedelta] = None, username: str = "", role: str = "faculty") -> str:
        if expires_delta is None:
            expires_delta = timedelta(minutes=30)
        
        expire = datetime.utcnow() + expires_delta
        payload = {
            "user_id": user_id,
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": expire
        }
        
        token = jwt.encode(
            payload,
            settings.secret_key,
            algorithm="HS256"
        )
        return token
    
    def verify_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=["HS256"]
            )
            user_id = payload.get("user_id")
            return user_id
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
