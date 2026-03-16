"""
Production-grade database connection management with async support,
connection pooling, health checks, and transaction handling
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from app.core.config.settings import get_settings
from app.core.database.models import Base
from app.core.logging.system_logger import SystemLogger
import logging

logger = SystemLogger("database")


class DatabaseManager:
    """
    Production-grade database manager with async support, connection pooling,
    health checks, and comprehensive transaction handling.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database engine with optimized connection pool"""
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Convert postgresql:// to postgresql+asyncpg://
            database_url = self.settings.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            # Create async engine with optimized settings
            self.engine = create_async_engine(
                database_url,
                echo=self.settings.database_echo,
                pool_size=self.settings.database_pool_size,
                max_overflow=self.settings.database_max_overflow,
                poolclass=QueuePool,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,   # Recycle connections after 1 hour
                connect_args={
                    "timeout": 30,
                    "command_timeout": 30,
                    "server_settings": {
                        "application_name": self.settings.app_name,
                        "jit": "off",
                    }
                }
            )
            
            # Create session factory
            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            self._initialized = True
            logger.info("Database engine initialized successfully", 
                       pool_size=self.settings.database_pool_size)
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
            raise
    
    async def create_tables(self):
        """Create all database tables from SQLAlchemy models"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                # Backward-compatible schema fix: PO/PSO code uniqueness should be scoped by program.
                await conn.execute(text("ALTER TABLE program_outcomes DROP CONSTRAINT IF EXISTS program_outcomes_code_key"))
                await conn.execute(text("ALTER TABLE program_specific_outcomes DROP CONSTRAINT IF EXISTS program_specific_outcomes_code_key"))
                await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_program_outcome_program_code ON program_outcomes (program, code)"))
                await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_program_specific_outcome_program_code ON program_specific_outcomes (program, code)"))
                # Backward-compatible schema fix: course detail fields used in workflow screens.
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS course_type VARCHAR(20) DEFAULT 'core'"))
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS enrolled_students INTEGER DEFAULT 0"))
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS fa_method VARCHAR(50) DEFAULT 'best_n_of_m'"))
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS fa_best_n INTEGER DEFAULT 3"))
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS fa_total_components INTEGER DEFAULT 5"))
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS fa_weight DOUBLE PRECISION DEFAULT 0.40"))
                await conn.execute(text("ALTER TABLE courses ADD COLUMN IF NOT EXISTS sa_weight DOUBLE PRECISION DEFAULT 0.60"))
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {str(e)}", exc_info=True)
            raise
    
    async def drop_tables(self):
        """Drop all database tables (development only, use with caution)"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        if self.settings.is_production:
            logger.error("Cannot drop tables in production environment")
            raise RuntimeError("Cannot drop tables in production")
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("All database tables dropped")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables: {str(e)}", exc_info=True)
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.async_session_factory()
    
    async def close(self):
        """Close database engine and dispose all connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        if not self._initialized:
            return False
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.warning(f"Database health check failed: {str(e)}")
            return False
    
    async def execute_raw_sql(self, sql: str):
        """Execute raw SQL query (use cautiously)"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text(sql))
            logger.info(f"Raw SQL executed successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to execute raw SQL: {str(e)}", exc_info=True)
            raise


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session with automatic cleanup and
    error handling. Used in FastAPI routes.
    """
    session = await db_manager.get_session()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error in database session: {str(e)}", exc_info=True)
        raise
    finally:
        await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Backward-compatible session dependency used by API routes."""
    async for session in get_db_session():
        yield session
