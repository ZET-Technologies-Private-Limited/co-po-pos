"""
User management service with comprehensive CRUD operations
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
import uuid

from app.core.database.models import User, Student
from app.modules.repositories.base_repository import BaseRepository
from app.core.security.password_hashing import PasswordManager
from app.core.logging.system_logger import SystemLogger


class UserService:
    """User management and authentication with full CRUD operations"""
    
    def __init__(self):
        self.logger = SystemLogger("user_service")
        self.password_hasher = PasswordManager()
        self.user_repo = BaseRepository(User)
        self.student_repo = BaseRepository(Student)
    
    async def create_user(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: str = "viewer",
        department: Optional[str] = None,
        **kwargs
    ) -> Optional[User]:
        """Create new user with enhanced validation"""
        try:
            # Check if user exists
            existing = await self.get_user_by_email(session, email)
            if existing:
                self.logger.warning(f"User already exists: {email}")
                return None
            
            # Hash password
            hashed_password = self.password_hasher.hash_password(password)
            
            # Create user data
            user_data = {
                'username': username,
                'email': email,
                'full_name': full_name,
                'hashed_password': hashed_password,
                'role': role,
                'department': department,
                'is_active': True,
                'is_verified': False,
                **kwargs
            }
            
            user = await self.user_repo.create(session, **user_data)
            await session.commit()
            
            self.logger.info(f"User created: {email}")
            return user
        
        except Exception as e:
            self.logger.error(f"User creation failed: {str(e)}")
            await session.rollback()
            return None
    
    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Optional[User]:
        """Get user by ID using repository"""
        try:
            return await self.user_repo.get_by_id(session, user_id)
        except Exception as e:
            self.logger.error(f"Get user by ID failed: {str(e)}")
            return None
    
    async def get_user_by_email(
        self,
        session: AsyncSession,
        email: str
    ) -> Optional[User]:
        """Get user by email"""
        try:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Get user by email failed: {str(e)}")
            return None
    
    async def get_user_by_username(
        self,
        session: AsyncSession,
        username: str
    ) -> Optional[User]:
        """Get user by username"""
        try:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Get user by username failed: {str(e)}")
            return None
    
    async def authenticate_user(
        self,
        session: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user"""
        try:
            user = await self.get_user_by_email(session, email)
            
            if not user:
                self.logger.warning(f"Authentication failed: user not found {email}")
                return None
            
            if not self.password_hasher.verify_password(password, user.hashed_password):
                self.logger.warning(f"Authentication failed: invalid password {email}")
                return None
            
            if not user.is_active:
                self.logger.warning(f"Authentication failed: user inactive {email}")
                return None
            
            self.logger.info(f"User authenticated: {email}")
            return user
        
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return None
    
    async def update_user(
        self,
        session: AsyncSession,
        user_id: str,
        **kwargs
    ) -> Optional[User]:
        """Update user using repository"""
        try:
            user = await self.user_repo.update(session, user_id, **kwargs)
            await session.commit()
            
            self.logger.info(f"User updated: {user_id}")
            return user
        
        except Exception as e:
            self.logger.error(f"User update failed: {str(e)}")
            await session.rollback()
            return None
    
    async def deactivate_user(
        self,
        session: AsyncSession,
        user_id: str
    ) -> bool:
        """Deactivate user"""
        try:
            user = await self.update_user(session, user_id, is_active=False)
            return user is not None
        
        except Exception as e:
            self.logger.error(f"User deactivation failed: {str(e)}")
            return False
    
    async def verify_user(
        self,
        session: AsyncSession,
        user_id: str
    ) -> bool:
        """Verify user"""
        try:
            user = await self.update_user(session, user_id, is_verified=True)
            return user is not None
        
        except Exception as e:
            self.logger.error(f"User verification failed: {str(e)}")
            return False
    
    async def change_password(
        self,
        session: AsyncSession,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """Change user password"""
        try:
            user = await self.get_user_by_id(session, user_id)
            
            if not user:
                return False
            
            if not self.password_hasher.verify_password(old_password, user.hashed_password):
                self.logger.warning(f"Password change failed: invalid old password {user_id}")
                return False
            
            hashed_password = self.password_hasher.hash_password(new_password)
            updated_user = await self.update_user(session, user_id, hashed_password=hashed_password)
            
            self.logger.info(f"Password changed: {user_id}")
            return updated_user is not None
        
        except Exception as e:
            self.logger.error(f"Password change failed: {str(e)}")
            return False
    
    # ==================== ENHANCED CRUD OPERATIONS ====================
    
    async def delete_user(self, session: AsyncSession, user_id: str) -> bool:
        """Delete user permanently"""
        try:
            deleted = await self.user_repo.delete(session, user_id)
            await session.commit()
            
            if deleted:
                self.logger.info(f"User deleted: {user_id}")
            return deleted
        
        except Exception as e:
            self.logger.error(f"User deletion failed: {str(e)}")
            await session.rollback()
            return False
    
    async def list_users(self, session: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> List[User]:
        """List users with filters"""
        try:
            stmt = select(User).offset(skip).limit(limit)
            
            if 'role' in filters:
                stmt = stmt.where(User.role == filters['role'])
            if 'department' in filters:
                stmt = stmt.where(User.department == filters['department'])
            if 'is_active' in filters:
                stmt = stmt.where(User.is_active == filters['is_active'])
            if 'is_verified' in filters:
                stmt = stmt.where(User.is_verified == filters['is_verified'])
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
        
        except Exception as e:
            self.logger.error(f"List users failed: {str(e)}")
            return []
    
    async def search_users(self, session: AsyncSession, query: str, limit: int = 10) -> List[User]:
        """Search users by username, email, or full name"""
        try:
            stmt = select(User).where(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.email.ilike(f"%{query}%"),
                    User.full_name.ilike(f"%{query}%")
                )
            ).limit(limit)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
        
        except Exception as e:
            self.logger.error(f"Search users failed: {str(e)}")
            return []
    
    async def count_users(self, session: AsyncSession, **filters) -> int:
        """Count users with filters"""
        try:
            stmt = select(func.count()).select_from(User)
            
            if 'role' in filters:
                stmt = stmt.where(User.role == filters['role'])
            if 'department' in filters:
                stmt = stmt.where(User.department == filters['department'])
            if 'is_active' in filters:
                stmt = stmt.where(User.is_active == filters['is_active'])
            
            result = await session.execute(stmt)
            return result.scalar() or 0
        
        except Exception as e:
            self.logger.error(f"Count users failed: {str(e)}")
            return 0
    
    async def exists_user(self, session: AsyncSession, **filters) -> bool:
        """Check if user exists with given filters"""
        try:
            return await self.user_repo.exists(session, **filters)
        except Exception as e:
            self.logger.error(f"User exists check failed: {str(e)}")
            return False
    
    # ==================== STUDENT OPERATIONS ====================
    
    async def create_student(self, session: AsyncSession, roll_number: str, first_name: str, 
                           last_name: str, email: str, program_id: str, **kwargs) -> Optional[Student]:
        """Create new student"""
        try:
            student_data = {
                'roll_number': roll_number,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'program_id': program_id,
                **kwargs
            }
            
            student = await self.student_repo.create(session, **student_data)
            await session.commit()
            
            self.logger.info(f"Student created: {roll_number}")
            return student
        
        except Exception as e:
            self.logger.error(f"Student creation failed: {str(e)}")
            await session.rollback()
            return None
    
    async def get_student(self, session: AsyncSession, student_id: str) -> Optional[Student]:
        """Get student by ID"""
        return await self.student_repo.get_by_id(session, student_id)
    
    async def get_student_by_roll(self, session: AsyncSession, roll_number: str) -> Optional[Student]:
        """Get student by roll number"""
        try:
            stmt = select(Student).where(Student.roll_number == roll_number)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Get student by roll failed: {str(e)}")
            return None
    
    async def update_student(self, session: AsyncSession, student_id: str, **data) -> Optional[Student]:
        """Update student"""
        try:
            student = await self.student_repo.update(session, student_id, **data)
            await session.commit()
            
            self.logger.info(f"Student updated: {student_id}")
            return student
        
        except Exception as e:
            self.logger.error(f"Student update failed: {str(e)}")
            await session.rollback()
            return None
    
    async def delete_student(self, session: AsyncSession, student_id: str) -> bool:
        """Delete student"""
        try:
            deleted = await self.student_repo.delete(session, student_id)
            await session.commit()
            
            if deleted:
                self.logger.info(f"Student deleted: {student_id}")
            return deleted
        
        except Exception as e:
            self.logger.error(f"Student deletion failed: {str(e)}")
            await session.rollback()
            return False
    
    async def list_students(self, session: AsyncSession, skip: int = 0, limit: int = 100, **filters) -> List[Student]:
        """List students with filters"""
        try:
            stmt = select(Student).offset(skip).limit(limit)
            
            if 'program_id' in filters:
                stmt = stmt.where(Student.program_id == filters['program_id'])
            if 'is_active' in filters:
                stmt = stmt.where(Student.is_active == filters['is_active'])
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
        
        except Exception as e:
            self.logger.error(f"List students failed: {str(e)}")
            return []
    
    async def search_students(self, session: AsyncSession, query: str, limit: int = 10) -> List[Student]:
        """Search students by roll number or name"""
        try:
            stmt = select(Student).where(
                or_(
                    Student.roll_number.ilike(f"%{query}%"),
                    Student.first_name.ilike(f"%{query}%"),
                    Student.last_name.ilike(f"%{query}%")
                )
            ).limit(limit)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
        
        except Exception as e:
            self.logger.error(f"Search students failed: {str(e)}")
            return []
