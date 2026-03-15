"""
Seed Course Lead Dashboard Data
==============================

Populates the Course Lead Dashboard tables with realistic sample data:
- Sample approval queue entries
- PO/PSO targets for departments
- Sample remedial actions for Level 1 COs
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.database.models import (
    ApprovalQueue, POTarget, PSOTarget, RemedialAction,
    Course, User, ProgramOutcome, ProgramSpecificOutcome, CourseOutcome
)
from app.core.config.settings import get_settings

async def seed_course_lead_data():
    """Seed Course Lead Dashboard with sample data"""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("🌱 Seeding Course Lead Dashboard data...")
        
        # Get existing data
        courses_result = await session.execute(select(Course))
        courses = list(courses_result.scalars().all())
        
        users_result = await session.execute(select(User))
        users = list(users_result.scalars().all())
        
        pos_result = await session.execute(select(ProgramOutcome))
        pos = list(pos_result.scalars().all())
        
        psos_result = await session.execute(select(ProgramSpecificOutcome))
        psos = list(psos_result.scalars().all())
        
        cos_result = await session.execute(select(CourseOutcome))
        cos = list(cos_result.scalars().all())
        
        if not courses or not users:
            print("❌ No courses or users found. Run seed_database.py first.")
            return
        
        # 1. Create sample approval queue entries
        print("📋 Creating approval queue entries...")
        now = datetime.utcnow()
        
        # Recent submission (normal priority)
        approval1 = ApprovalQueue(
            id=str(uuid.uuid4()),
            course_id=courses[0].id,
            faculty_id=users[1].id if len(users) > 1 else users[0].id,
            submission_type='marks',
            status='pending',
            priority='normal',
            submitted_at=now - timedelta(hours=2),
            data={'exam_type': 'mid_term', 'total_students': 45}
        )
        session.add(approval1)
        
        # Older submission (high priority)
        if len(courses) > 1:
            approval2 = ApprovalQueue(
                id=str(uuid.uuid4()),
                course_id=courses[1].id,
                faculty_id=users[1].id if len(users) > 1 else users[0].id,
                submission_type='co_generation',
                status='pending',
                priority='high',
                submitted_at=now - timedelta(hours=30),
                data={'co_count': 5, 'syllabus_length': 2500}
            )
            session.add(approval2)
        
        # Critical submission (overdue)
        approval3 = ApprovalQueue(
            id=str(uuid.uuid4()),
            course_id=courses[0].id,
            faculty_id=users[0].id,
            submission_type='marks',
            status='pending',
            priority='critical',
            submitted_at=now - timedelta(hours=80),
            data={'exam_type': 'end_term', 'total_students': 42}
        )
        session.add(approval3)
        
        # 2. Create PO targets
        print("🎯 Creating PO targets...")
        department = courses[0].department or "CSE"
        academic_year = "2024-25"
        
        for i, po in enumerate(pos[:5]):  # First 5 POs
            target_pct = 70.0
            current_pct = 65.0 + (i * 3)  # Varying current percentages
            
            po_target = POTarget(
                id=str(uuid.uuid4()),
                program_outcome_id=po.id,
                department=department,
                academic_year=academic_year,
                target_percentage=target_pct,
                current_percentage=current_pct,
                status='met' if current_pct >= target_pct else 'not_met',
                courses_mapped=len(courses),
                last_calculated=now
            )
            session.add(po_target)
        
        # 3. Create PSO targets
        print("🎯 Creating PSO targets...")
        for i, pso in enumerate(psos[:3]):  # First 3 PSOs
            target_pct = 70.0
            current_pct = 68.0 + (i * 2)  # Varying current percentages
            
            pso_target = PSOTarget(
                id=str(uuid.uuid4()),
                pso_id=pso.id,
                department=department,
                academic_year=academic_year,
                target_percentage=target_pct,
                current_percentage=current_pct,
                status='met' if current_pct >= target_pct else 'not_met',
                courses_mapped=len(courses),
                last_calculated=now
            )
            session.add(pso_target)
        
        # 4. Create sample remedial actions
        print("🔧 Creating remedial actions...")
        if cos:
            # Pending remedial action
            remedial1 = RemedialAction(
                id=str(uuid.uuid4()),
                course_id=courses[0].id,
                course_outcome_id=cos[0].id,
                attainment_percentage=45.5,  # Level 1
                action_plan="Conduct additional tutorial sessions and practice problems for weak students",
                target_percentage=65.0,
                due_date=now + timedelta(days=30),
                status='pending',
                assigned_to=users[1].id if len(users) > 1 else users[0].id,
                created_by=users[0].id
            )
            session.add(remedial1)
            
            # Overdue remedial action
            if len(cos) > 1:
                remedial2 = RemedialAction(
                    id=str(uuid.uuid4()),
                    course_id=courses[0].id,
                    course_outcome_id=cos[1].id,
                    attainment_percentage=38.2,  # Level 1
                    action_plan="Redesign assessment strategy and provide supplementary learning materials",
                    target_percentage=60.0,
                    due_date=now - timedelta(days=5),  # Overdue
                    status='overdue',
                    assigned_to=users[1].id if len(users) > 1 else users[0].id,
                    created_by=users[0].id
                )
                session.add(remedial2)
        
        # Commit all changes
        await session.commit()
        
        print("✅ Course Lead Dashboard data seeded successfully!")
        print(f"Created:")
        print(f"  - 3 approval queue entries")
        print(f"  - {min(5, len(pos))} PO targets")
        print(f"  - {min(3, len(psos))} PSO targets")
        print(f"  - {min(2, len(cos))} remedial actions")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_course_lead_data())