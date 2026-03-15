"""
Course Lead Dashboard Database Migration
=======================================

This script adds the missing database tables and indexes required for
the Course Lead Dashboard functionality.

Tables Added:
- approval_queue: Tracks marks and CO submissions for approval
- remedial_actions: Manages Level 1 CO remedial action plans
- po_targets: PO attainment targets and tracking
- pso_targets: PSO attainment targets and tracking
- audit_logs: System audit trail for all changes

Run this script after setting up the main database schema.
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config.settings import get_settings
from app.core.database.models import Base, ApprovalQueue, RemedialAction, POTarget, PSOTarget, AuditLog

settings = get_settings()

async def create_course_lead_tables():
    """Create Course Lead Dashboard tables"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Course Lead Dashboard tables created successfully")
        
        # Add indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_approval_queue_status ON approval_queue(status);",
            "CREATE INDEX IF NOT EXISTS idx_approval_queue_submitted ON approval_queue(submitted_at);",
            "CREATE INDEX IF NOT EXISTS idx_approval_queue_course ON approval_queue(course_id);",
            "CREATE INDEX IF NOT EXISTS idx_remedial_actions_status ON remedial_actions(status);",
            "CREATE INDEX IF NOT EXISTS idx_remedial_actions_due ON remedial_actions(due_date);",
            "CREATE INDEX IF NOT EXISTS idx_remedial_actions_course ON remedial_actions(course_id);",
            "CREATE INDEX IF NOT EXISTS idx_po_targets_status ON po_targets(status);",
            "CREATE INDEX IF NOT EXISTS idx_pso_targets_status ON pso_targets(status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);"
        ]
        
        for index_sql in indexes:
            await conn.execute(text(index_sql))
        
        print("✅ Database indexes created successfully")
    
    await engine.dispose()

async def seed_course_lead_data():
    """Seed sample data for Course Lead Dashboard"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Sample approval queue entries
        approval_entries = [
            ApprovalQueue(
                id=str(uuid.uuid4()),
                course_id="course_1",  # Replace with actual course IDs
                faculty_id="faculty_1",  # Replace with actual faculty IDs
                submission_type="marks",
                status="pending",
                priority="high",
                submitted_at=datetime.utcnow(),
                data={"exam_type": "T1", "total_students": 45}
            ),
            ApprovalQueue(
                id=str(uuid.uuid4()),
                course_id="course_2",
                faculty_id="faculty_2",
                submission_type="co_generation",
                status="pending",
                priority="normal",
                submitted_at=datetime.utcnow(),
                data={"cos_generated": 5, "syllabus_updated": True}
            )
        ]
        
        # Sample remedial actions
        remedial_entries = [
            RemedialAction(
                id=str(uuid.uuid4()),
                course_id="course_1",
                course_outcome_id="co_1",
                attainment_percentage=45.0,
                action_plan="Conduct additional tutorials and practice sessions for weak students",
                target_percentage=65.0,
                due_date=datetime.utcnow(),
                status="pending",
                assigned_to="faculty_1",
                created_by="course_lead_1"
            )
        ]
        
        # Sample PO targets
        po_targets = [
            POTarget(
                id=str(uuid.uuid4()),
                program_outcome_id="po_1",
                department="CSE",
                academic_year="2024-25",
                target_percentage=70.0,
                current_percentage=68.5,
                status="partial",
                courses_mapped=8
            ),
            POTarget(
                id=str(uuid.uuid4()),
                program_outcome_id="po_2",
                department="CSE",
                academic_year="2024-25",
                target_percentage=70.0,
                current_percentage=72.3,
                status="met",
                courses_mapped=6
            )
        ]
        
        # Sample PSO targets
        pso_targets = [
            PSOTarget(
                id=str(uuid.uuid4()),
                pso_id="pso_1",
                department="CSE",
                academic_year="2024-25",
                target_percentage=70.0,
                current_percentage=65.8,
                status="not_met",
                courses_mapped=4
            )
        ]
        
        # Add all sample data
        for entry in approval_entries + remedial_entries + po_targets + pso_targets:
            session.add(entry)
        
        await session.commit()
        print("✅ Sample Course Lead Dashboard data seeded successfully")
    
    await engine.dispose()

async def main():
    """Run the complete migration"""
    print("🚀 Starting Course Lead Dashboard Migration...")
    
    try:
        await create_course_lead_tables()
        await seed_course_lead_data()
        print("✅ Course Lead Dashboard migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())