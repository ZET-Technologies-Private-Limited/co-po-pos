"""
Base repository class with common database operations
"""
from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload
from uuid import uuid4

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository with CRUD operations"""
    
    def __init__(self, model: type[T]):
        self.model = model
    
    async def create(self, session: AsyncSession, **kwargs) -> T:
        """Create new entity"""
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        instance = self.model(**kwargs)
        session.add(instance)
        await session.flush()
        return instance
    
    async def get_by_id(self, session: AsyncSession, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        stmt = select(self.model).where(self.model.id == entity_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination"""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def update(self, session: AsyncSession, entity_id: str, **kwargs) -> Optional[T]:
        """Update entity"""
        stmt = update(self.model).where(self.model.id == entity_id).values(**kwargs)
        await session.execute(stmt)
        await session.flush()
        return await self.get_by_id(session, entity_id)
    
    async def delete(self, session: AsyncSession, entity_id: str) -> bool:
        """Delete entity"""
        stmt = delete(self.model).where(self.model.id == entity_id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0
    
    async def count(self, session: AsyncSession) -> int:
        """Count total entities"""
        stmt = select(func.count()).select_from(self.model)
        result = await session.execute(stmt)
        return result.scalar() or 0
    
    async def exists(self, session: AsyncSession, **filters) -> bool:
        """Check if entity exists"""
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
