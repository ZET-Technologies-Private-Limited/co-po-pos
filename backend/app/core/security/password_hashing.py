"""
Password hashing and verification using bcrypt
"""
from passlib.context import CryptContext

# Configure bcrypt context with production-level settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Cost factor for bcrypt
)


class PasswordManager:
    """Password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hashed password"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Alias for hash_password"""
        return PasswordManager.hash_password(password)


def hash_password(password: str) -> str:
    """Compatibility helper for modules importing function-style API."""
    return PasswordManager.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compatibility helper for modules importing function-style API."""
    return PasswordManager.verify_password(plain_password, hashed_password)
