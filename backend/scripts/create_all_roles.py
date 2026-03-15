"""
Create all user roles with real credentials in the database
This script creates users for all available roles in the system
"""
import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config.settings import get_settings
from app.core.database.models import Base, User, Department, Program
from app.core.security.password_hashing import PasswordManager
from app.core.config.constants import UserRole


async def create_all_roles():
    """Create all user roles with real credentials"""
    settings = get_settings()
    
    print("[*] Creating all user roles in database...")
    print(f"[*] Database URL: {settings.database_url}")
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,  # Set to True for SQL debugging
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow
    )
    
    # Create all tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        await create_users_and_departments(session)
    
    await engine.dispose()
    print("[OK] All roles created successfully!")


async def create_users_and_departments(session: AsyncSession):
    """Create departments and users for all roles"""
    password_hasher = PasswordManager()
    
    # Create departments first
    departments_data = [
        {"code": "CSE", "name": "Computer Science and Engineering"},
        {"code": "ECE", "name": "Electronics and Communication Engineering"},
        {"code": "ME", "name": "Mechanical Engineering"},
        {"code": "CE", "name": "Civil Engineering"},
        {"code": "EEE", "name": "Electrical and Electronics Engineering"},
        {"code": "ADMIN", "name": "Administration"}
    ]
    
    print("\n[*] Creating departments...")
    for dept_data in departments_data:
        # Check if department already exists
        result = await session.execute(
            select(Department).where(Department.code == dept_data["code"])
        )
        existing_dept = result.scalar_one_or_none()
        
        if not existing_dept:
            department = Department(
                id=str(uuid4()),
                code=dept_data["code"],
                name=dept_data["name"],
                description=f"Department of {dept_data['name']}"
            )
            session.add(department)
            print(f"  [+] Created department: {dept_data['name']}")
        else:
            print(f"  [=] Department already exists: {dept_data['name']}")
    
    await session.flush()
    
    # Define users for each role with real credentials
    users_data = [
        # ADMIN users
        {
            "username": "admin",
            "email": "admin@university.edu",
            "full_name": "System Administrator",
            "password": "Admin@123456",
            "role": UserRole.ADMIN,
            "department": "Administration"
        },
        {
            "username": "superadmin",
            "email": "superadmin@university.edu", 
            "full_name": "Super Administrator",
            "password": "SuperAdmin@123456",
            "role": UserRole.ADMIN,
            "department": "Administration"
        },
        
        # HOD users
        {
            "username": "hod_cse",
            "email": "hod.cse@university.edu",
            "full_name": "Dr. Rajesh Kumar (HOD CSE)",
            "password": "HodCSE@123456",
            "role": UserRole.HOD,
            "department": "Computer Science and Engineering"
        },
        {
            "username": "hod_ece",
            "email": "hod.ece@university.edu",
            "full_name": "Dr. Priya Sharma (HOD ECE)",
            "password": "HodECE@123456",
            "role": UserRole.HOD,
            "department": "Electronics and Communication Engineering"
        },
        {
            "username": "hod_me",
            "email": "hod.me@university.edu",
            "full_name": "Dr. Amit Singh (HOD ME)",
            "password": "HodME@123456",
            "role": UserRole.HOD,
            "department": "Mechanical Engineering"
        },
        
        # COURSE_LEAD users
        {
            "username": "lead_cs101",
            "email": "lead.cs101@university.edu",
            "full_name": "Dr. Sunita Verma (Course Lead)",
            "password": "LeadCS@123456",
            "role": UserRole.COURSE_LEAD,
            "department": "Computer Science and Engineering"
        },
        {
            "username": "lead_cs201",
            "email": "lead.cs201@university.edu",
            "full_name": "Dr. Vikram Patel (Course Lead)",
            "password": "LeadCS201@123456",
            "role": UserRole.COURSE_LEAD,
            "department": "Computer Science and Engineering"
        },
        {
            "username": "lead_ece101",
            "email": "lead.ece101@university.edu",
            "full_name": "Dr. Meera Joshi (Course Lead)",
            "password": "LeadECE@123456",
            "role": UserRole.COURSE_LEAD,
            "department": "Electronics and Communication Engineering"
        },
        
        # FACULTY users
        {
            "username": "faculty1",
            "email": "faculty1@university.edu",
            "full_name": "Dr. John Smith",
            "password": "Faculty@123456",
            "role": UserRole.FACULTY,
            "department": "Computer Science and Engineering"
        },
        {
            "username": "faculty2",
            "email": "faculty2@university.edu",
            "full_name": "Dr. Jane Doe",
            "password": "Faculty2@123456",
            "role": UserRole.FACULTY,
            "department": "Computer Science and Engineering"
        },
        {
            "username": "faculty3",
            "email": "faculty3@university.edu",
            "full_name": "Dr. Michael Johnson",
            "password": "Faculty3@123456",
            "role": UserRole.FACULTY,
            "department": "Electronics and Communication Engineering"
        },
        {
            "username": "faculty4",
            "email": "faculty4@university.edu",
            "full_name": "Dr. Sarah Wilson",
            "password": "Faculty4@123456",
            "role": UserRole.FACULTY,
            "department": "Mechanical Engineering"
        },
        {
            "username": "faculty5",
            "email": "faculty5@university.edu",
            "full_name": "Dr. David Brown",
            "password": "Faculty5@123456",
            "role": UserRole.FACULTY,
            "department": "Civil Engineering"
        },
        
        # ACCREDITATION_OFFICER users
        {
            "username": "accreditation1",
            "email": "accreditation@university.edu",
            "full_name": "Dr. Kavita Reddy (Accreditation Officer)",
            "password": "Accred@123456",
            "role": UserRole.ACCREDITATION_OFFICER,
            "department": "Administration"
        },
        {
            "username": "accreditation2",
            "email": "accreditation2@university.edu",
            "full_name": "Dr. Ravi Gupta (Accreditation Officer)",
            "password": "Accred2@123456",
            "role": UserRole.ACCREDITATION_OFFICER,
            "department": "Administration"
        },
        
        # VIEWER users
        {
            "username": "viewer1",
            "email": "viewer1@university.edu",
            "full_name": "Student Representative",
            "password": "Viewer@123456",
            "role": UserRole.VIEWER,
            "department": "Computer Science and Engineering"
        },
        {
            "username": "viewer2",
            "email": "viewer2@university.edu",
            "full_name": "External Examiner",
            "password": "Viewer2@123456",
            "role": UserRole.VIEWER,
            "department": "Administration"
        },
        {
            "username": "guest",
            "email": "guest@university.edu",
            "full_name": "Guest User",
            "password": "Guest@123456",
            "role": UserRole.VIEWER,
            "department": "Administration"
        }
    ]
    
    print("\n[*] Creating users for all roles...")
    created_count = 0
    existing_count = 0
    
    for user_data in users_data:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.username == user_data["username"])
        )
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            user = User(
                id=str(uuid4()),
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=password_hasher.hash_password(user_data["password"]),
                role=user_data["role"],
                department=user_data["department"],
                is_active=True,
                is_verified=True
            )
            session.add(user)
            created_count += 1
            print(f"  [+] Created {user_data['role'].value}: {user_data['username']} ({user_data['full_name']})")
        else:
            existing_count += 1
            print(f"  [=] User already exists: {user_data['username']}")
    
    # Commit all changes
    await session.commit()
    
    print(f"\n[OK] User creation summary:")
    print(f"  - Created: {created_count} users")
    print(f"  - Already existed: {existing_count} users")
    print(f"  - Total users processed: {len(users_data)}")
    
    # Print login credentials
    print("\n" + "="*80)
    print("LOGIN CREDENTIALS FOR ALL ROLES")
    print("="*80)
    
    role_groups = {}
    for user_data in users_data:
        role = user_data["role"].value.upper()
        if role not in role_groups:
            role_groups[role] = []
        role_groups[role].append(user_data)
    
    for role, users in role_groups.items():
        print(f"\n{role} USERS:")
        print("-" * 40)
        for user in users:
            print(f"  Username: {user['username']}")
            print(f"  Email:    {user['email']}")
            print(f"  Password: {user['password']}")
            print(f"  Name:     {user['full_name']}")
            print(f"  Dept:     {user['department']}")
            print()
    
    print("="*80)
    print("IMPORTANT NOTES:")
    print("- All passwords follow the pattern: Role@123456")
    print("- All users are active and verified")
    print("- Change default passwords after first login")
    print("- Use these credentials to test all role-based features")
    print("="*80)


async def main():
    """Main function"""
    try:
        await create_all_roles()
        print("\n[OK] All roles setup completed successfully!")
        return 0
    except Exception as e:
        print(f"\n[X] Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    exit_code = asyncio.run(main())
    sys.exit(exit_code)