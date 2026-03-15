"""
Role-based access control and permission management
"""
from typing import List, Set
from app.core.config.constants import UserRole


class PermissionManager:
    """Manage role-based permissions and access control"""
    
    # Role permission mapping
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            "users:create", "users:read", "users:update", "users:delete",
            "courses:create", "courses:read", "courses:update", "courses:delete",
            "outcomes:create", "outcomes:read", "outcomes:update", "outcomes:delete",
            "exams:create", "exams:read", "exams:update", "exams:delete",
            "marks:upload", "marks:read", "marks:update",
            "reports:generate", "reports:read",
            "system:manage", "system:logs",
        },
        UserRole.HOD: {
            "courses:read", "courses:update",
            "outcomes:create", "outcomes:read", "outcomes:update",
            "exams:create", "exams:read", "exams:update",
            "marks:read",
            "reports:generate", "reports:read",
        },
        UserRole.FACULTY: {
            "courses:read",
            "outcomes:read",
            "exams:create", "exams:read", "exams:update",
            "marks:upload", "marks:read",
            "reports:read",
        },
        UserRole.ACCREDITATION_OFFICER: {
            "courses:read",
            "outcomes:read",
            "exams:read",
            "marks:read",
            "reports:generate", "reports:read",
        },
        UserRole.VIEWER: {
            "courses:read",
            "outcomes:read",
            "reports:read",
        },
    }
    
    @classmethod
    def get_user_permissions(cls, role: UserRole) -> Set[str]:
        """Get all permissions for a role"""
        return cls.ROLE_PERMISSIONS.get(role, set())
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: str) -> bool:
        """Check if role has specific permission"""
        permissions = cls.get_user_permissions(role)
        return permission in permissions
    
    @classmethod
    def has_any_permission(cls, role: UserRole, permissions: List[str]) -> bool:
        """Check if role has any of the specified permissions"""
        user_permissions = cls.get_user_permissions(role)
        return any(perm in user_permissions for perm in permissions)
    
    @classmethod
    def has_all_permissions(cls, role: UserRole, permissions: List[str]) -> bool:
        """Check if role has all specified permissions"""
        user_permissions = cls.get_user_permissions(role)
        return all(perm in user_permissions for perm in permissions)
