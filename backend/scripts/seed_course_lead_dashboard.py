"""
Course Lead Dashboard Data Seeding Script
=========================================

This script populates the Course Lead Dashboard tables with realistic
sample data for testing and demonstration purposes.

Data Created:
- Approval queue entries with various statuses and wait times
- Remedial actions for Level 1 COs
- PO/PSO targets with current vs target tracking
- Audit log entries for system changes
- Sample reports and historical data

Usage:
    python scripts/seed_course_lead_dashboard.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config.settings import get_settings
from app.core.database.models import (
    ApprovalQueue, RemedialAction, POTarget, PSOTarget, AuditLog, Report,
    Course, User, CourseOutcome, ProgramOutcome, ProgramSpecificOutcome
)

settings = get_settings()

class CourseLeadDataSeeder:
    def __init__(self):
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
    
    async def seed_all_data(self):
        """Seed all Course Lead Dashboard data"""
        async with self.async_session() as session:
            # Get existing data for references
            courses = await self._get_existing_courses(session)
            users = await self._get_existing_users(session)
            cos = await self._get_existing_cos(session)
            pos = await self._get_existing_pos(session)
            psos = await self._get_existing_psos(session)
            
            if not courses or not users:
                print("⚠️  No courses or users found. Please run the main seed script first.")
                return
            
            # Seed approval queue
            await self._seed_approval_queue(session, courses, users)
            
            # Seed remedial actions
            await self._seed_remedial_actions(session, courses, users, cos)
            
            # Seed PO targets
            await self._seed_po_targets(session, pos)
            
            # Seed PSO targets
            await self._seed_pso_targets(session, psos)
            
            # Seed audit logs
            await self._seed_audit_logs(session, users)
            
            # Seed sample reports
            await self._seed_sample_reports(session, courses, users)
            
            await session.commit()
            print("✅ Course Lead Dashboard data seeded successfully!")
    
    async def _get_existing_courses(self, session: AsyncSession):
        """Get existing courses"""
        result = await session.execute(select(Course).limit(10))
        return list(result.scalars().all())
    
    async def _get_existing_users(self, session: AsyncSession):
        """Get existing users"""
        result = await session.execute(select(User).limit(10))
        return list(result.scalars().all())
    
    async def _get_existing_cos(self, session: AsyncSession):
        """Get existing course outcomes"""
        result = await session.execute(select(CourseOutcome).limit(20))
        return list(result.scalars().all())
    
    async def _get_existing_pos(self, session: AsyncSession):
        """Get existing program outcomes"""
        result = await session.execute(select(ProgramOutcome).limit(10))
        return list(result.scalars().all())
    
    async def _get_existing_psos(self, session: AsyncSession):
        """Get existing program specific outcomes"""
        result = await session.execute(select(ProgramSpecificOutcome).limit(5))
        return list(result.scalars().all())
    
    async def _seed_approval_queue(self, session: AsyncSession, courses, users):
        """Seed approval queue with various submission types and statuses"""
        print("📝 Seeding approval queue...")
        
        approval_entries = []
        
        # Create entries with different wait times and urgencies
        base_time = datetime.utcnow()
        
        for i, course in enumerate(courses[:6]):
            faculty = users[i % len(users)]
            
            # Vary submission times to create different wait times
            if i == 0:
                submitted_time = base_time - timedelta(hours=80)  # Critical (>72h)
                priority = "critical"
            elif i == 1:
                submitted_time = base_time - timedelta(hours=30)  # High (>24h)
                priority = "high"
            elif i == 2:
                submitted_time = base_time - timedelta(hours=10)  # Normal (<24h)
                priority = "normal"
            else:
                submitted_time = base_time - timedelta(hours=5 + i)
                priority = "normal"
            
            # Different submission types
            submission_types = ["marks", "co_generation", "exam_config"]
            submission_type = submission_types[i % len(submission_types)]
            
            # Different statuses
            statuses = ["pending", "pending", "pending", "approved", "returned", "pending"]
            status = statuses[i]
            
            approval_entry = ApprovalQueue(
                id=str(uuid.uuid4()),
                course_id=course.id,
                faculty_id=faculty.id,
                submission_type=submission_type,
                status=status,
                priority=priority,
                submitted_at=submitted_time,
                reviewed_at=base_time - timedelta(hours=2) if status in ["approved", "returned"] else None,
                reviewed_by=users[0].id if status in ["approved", "returned"] else None,
                review_comments=f"Sample review comment for {submission_type}" if status in ["approved", "returned"] else None,
                data={
                    "exam_type": "T1" if submission_type == "marks" else None,
                    "total_students": 45 + i * 5,
                    "cos_generated": 5 if submission_type == "co_generation" else None,
                    "syllabus_updated": True if submission_type == "co_generation" else None,
                    "assessment_code": f"T{i+1}" if submission_type == "exam_config" else None
                }
            )
            approval_entries.append(approval_entry)
        
        for entry in approval_entries:
            session.add(entry)
        
        print(f"   Added {len(approval_entries)} approval queue entries")
    
    async def _seed_remedial_actions(self, session: AsyncSession, courses, users, cos):
        """Seed remedial actions for Level 1 COs"""
        print("🔧 Seeding remedial actions...")
        
        if not cos:
            print("   No COs found, skipping remedial actions")
            return
        
        remedial_entries = []
        
        # Create remedial actions for some COs
        for i, co in enumerate(cos[:5]):
            course = next((c for c in courses if c.id == co.course_id), courses[0])
            faculty = users[i % len(users)]
            course_lead = users[0]  # Assume first user is course lead
            
            # Different statuses and due dates
            statuses = ["pending", "in_progress", "completed", "overdue", "pending"]
            status = statuses[i]
            
            due_date = datetime.utcnow() + timedelta(days=7 + i * 3)
            if status == "overdue":
                due_date = datetime.utcnow() - timedelta(days=2)
            
            remedial_entry = RemedialAction(
                id=str(uuid.uuid4()),
                course_id=course.id,
                course_outcome_id=co.id,
                attainment_percentage=35.0 + i * 5,  # Level 1 percentages
                action_plan=f"Remedial action plan for {co.code}: Conduct additional tutorials, provide extra practice materials, and schedule one-on-one sessions for struggling students.",
                target_percentage=65.0,
                due_date=due_date,
                status=status,
                assigned_to=faculty.id,
                created_by=course_lead.id,
                completed_at=datetime.utcnow() - timedelta(days=1) if status == "completed" else None
            )
            remedial_entries.append(remedial_entry)
        
        for entry in remedial_entries:
            session.add(entry)
        
        print(f"   Added {len(remedial_entries)} remedial actions")
    
    async def _seed_po_targets(self, session: AsyncSession, pos):
        """Seed PO targets with current vs target tracking"""
        print("🎯 Seeding PO targets...")
        
        if not pos:
            print("   No POs found, skipping PO targets")
            return
        
        po_targets = []
        departments = ["CSE", "ECE", "MECH"]
        academic_year = "2024-25"
        
        for i, po in enumerate(pos):
            department = departments[i % len(departments)]
            
            # Vary current percentages to show different statuses
            target_pct = 70.0
            current_percentages = [72.5, 68.3, 65.8, 71.2, 58.9, 69.1, 73.4, 62.7, 70.8, 66.5]
            current_pct = current_percentages[i % len(current_percentages)]
            
            # Determine status
            if current_pct >= target_pct:
                status = "met"
            elif current_pct >= target_pct * 0.8:  # 80% of target
                status = "partial"
            else:
                status = "not_met"
            
            po_target = POTarget(
                id=str(uuid.uuid4()),
                program_outcome_id=po.id,
                department=department,
                academic_year=academic_year,
                target_percentage=target_pct,
                current_percentage=current_pct,
                status=status,
                courses_mapped=5 + i,
                last_calculated=datetime.utcnow() - timedelta(days=i)
            )
            po_targets.append(po_target)
        
        for target in po_targets:
            session.add(target)
        
        print(f"   Added {len(po_targets)} PO targets")
    
    async def _seed_pso_targets(self, session: AsyncSession, psos):
        """Seed PSO targets"""
        print("🎯 Seeding PSO targets...")
        
        if not psos:
            print("   No PSOs found, skipping PSO targets")
            return
        
        pso_targets = []
        departments = ["CSE", "ECE"]
        academic_year = "2024-25"
        
        for i, pso in enumerate(psos):
            department = departments[i % len(departments)]
            
            # PSO targets
            target_pct = 70.0
            current_percentages = [68.4, 72.1, 65.3, 71.8, 63.2]
            current_pct = current_percentages[i % len(current_percentages)]
            
            if current_pct >= target_pct:
                status = "met"
            elif current_pct >= target_pct * 0.8:
                status = "partial"
            else:
                status = "not_met"
            
            pso_target = PSOTarget(
                id=str(uuid.uuid4()),
                pso_id=pso.id,
                department=department,
                academic_year=academic_year,
                target_percentage=target_pct,
                current_percentage=current_pct,
                status=status,
                courses_mapped=3 + i,
                last_calculated=datetime.utcnow() - timedelta(days=i)
            )
            pso_targets.append(pso_target)
        
        for target in pso_targets:
            session.add(target)
        
        print(f"   Added {len(pso_targets)} PSO targets")
    
    async def _seed_audit_logs(self, session: AsyncSession, users):
        """Seed audit logs for system changes"""
        print("📋 Seeding audit logs...")
        
        audit_entries = []
        
        # Different types of actions
        actions = [
            ("marks_approval", "Approved T1 marks for CS301"),
            ("co_attainment_override", "Overridden CO1 attainment level"),
            ("marks_return", "Returned T2 marks for revision"),
            ("remedial_action_created", "Created remedial action for CO3"),
            ("po_target_updated", "Updated PO1 target percentage"),
            ("report_generated", "Generated CO attainment report"),
            ("marks_override", "HOD override for exam marks"),
            ("co_generation", "Generated 5 COs using AI"),
            ("exam_configuration", "Configured T3 exam structure"),
            ("student_marks_upload", "Uploaded marks for 45 students")
        ]
        
        for i, (action, description) in enumerate(actions):
            user = users[i % len(users)]
            
            audit_entry = AuditLog(
                id=str(uuid.uuid4()),
                user_id=user.id,
                action=action,
                entity_type="exam" if "marks" in action else "course_outcome" if "co" in action else "system",
                entity_id=str(uuid.uuid4()),  # Sample entity ID
                changes={
                    "description": description,
                    "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                    "details": f"Sample audit log entry for {action}",
                    "user_role": "course_lead" if i % 3 == 0 else "faculty"
                },
                ip_address=f"192.168.1.{100 + i}",
                user_agent="Mozilla/5.0 (Course Lead Dashboard)",
                timestamp=datetime.utcnow() - timedelta(hours=i)
            )
            audit_entries.append(audit_entry)
        
        for entry in audit_entries:
            session.add(entry)
        
        print(f"   Added {len(audit_entries)} audit log entries")
    
    async def _seed_sample_reports(self, session: AsyncSession, courses, users):
        """Seed sample reports for report history"""
        print("📊 Seeding sample reports...")
        
        report_entries = []
        report_types = ["co_attainment", "po_attainment", "student_performance", "nba_format"]
        
        for i in range(8):
            course = courses[i % len(courses)]
            user = users[i % len(users)]
            report_type = report_types[i % len(report_types)]
            
            report = Report(
                id=str(uuid.uuid4()),
                report_type=report_type,
                title=f"{report_type.replace('_', ' ').title()} Report - CSE | AY 2024-25",
                description=f"Generated report for {report_type} analysis",
                course_id=course.id,
                generated_by=user.id,
                generated_at=datetime.utcnow() - timedelta(days=i),
                file_format="pdf",
                data={
                    "department": "CSE",
                    "academic_year": "2024-25",
                    "report_type": report_type,
                    "generated_at": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "file_size": f"{2.5 + i * 0.3:.1f} MB"
                },
                is_archived=i > 5  # Archive older reports
            )
            report_entries.append(report)
        
        for report in report_entries:
            session.add(report)
        
        print(f"   Added {len(report_entries)} sample reports")
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

async def main():
    """Run the seeding process"""
    print("🌱 Starting Course Lead Dashboard Data Seeding...")
    
    seeder = CourseLeadDataSeeder()
    
    try:
        await seeder.seed_all_data()
        print("✅ Course Lead Dashboard data seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")
        raise
    
    finally:
        await seeder.close()

if __name__ == "__main__":
    asyncio.run(main())