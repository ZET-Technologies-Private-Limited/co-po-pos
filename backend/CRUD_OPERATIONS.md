# Enhanced CRUD Operations - CO-PO-PSO System

This document outlines the comprehensive CRUD (Create, Read, Update, Delete) operations available in the enhanced services using the existing base repository pattern.

## Overview

All services have been enhanced with full CRUD operations while maintaining the existing architecture and patterns. The services use the `BaseRepository` class for consistent database operations.

## Enhanced Services

### 1. CourseService (`app/modules/courses/services/course_service.py`)

#### Course Operations
- **Create**: `create_course(course_code, course_name, credits, semester, description, faculty_id, **kwargs)`
- **Read**: `get_course(course_id)`
- **Update**: `update_course(course_id, **data)`
- **Delete**: `delete_course(course_id)`
- **List**: `list_courses(semester=None, skip=0, limit=100, **filters)`
- **Search**: `search_courses(query, limit=10)`
- **Count**: `count_courses(**filters)`

#### Exam Operations
- **Create**: `create_exam(course_id, exam_name, exam_type, total_marks, **kwargs)`
- **Read**: `get_exam(exam_id)`
- **Update**: `update_exam(exam_id, **data)`
- **Delete**: `delete_exam(exam_id)`
- **List**: `list_exams(course_id)`

#### Question Operations
- **Create**: `add_question(exam_id, question_text, marks, question_number, **kwargs)`
- **Read**: `get_question(question_id)`
- **Update**: `update_question(question_id, **data)`
- **Delete**: `delete_question(question_id)`
- **List**: `list_questions(exam_id)`

#### Course Outcome Operations
- **Create**: `create_course_outcome(course_id, code, statement, bloom_level, **kwargs)`
- **Read**: `get_course_outcome(co_id)`
- **Update**: `update_course_outcome(co_id, **data)`
- **Delete**: `delete_course_outcome(co_id)`
- **List**: `list_course_outcomes(course_id)`

#### Additional Operations
- **Enrollment Count**: `get_enrollment_count(course_id)`
- **Course Enrollments**: `get_course_enrollments(course_id)`

### 2. UserService (`app/modules/user/services/user_service.py`)

#### User Operations
- **Create**: `create_user(session, username, email, password, full_name, role, department, **kwargs)`
- **Read**: `get_user_by_id(session, user_id)`
- **Read by Email**: `get_user_by_email(session, email)`
- **Read by Username**: `get_user_by_username(session, username)`
- **Update**: `update_user(session, user_id, **kwargs)`
- **Delete**: `delete_user(session, user_id)`
- **List**: `list_users(session, skip=0, limit=100, **filters)`
- **Search**: `search_users(session, query, limit=10)`
- **Count**: `count_users(session, **filters)`
- **Exists**: `exists_user(session, **filters)`

#### Authentication Operations
- **Authenticate**: `authenticate_user(session, email, password)`
- **Change Password**: `change_password(session, user_id, old_password, new_password)`
- **Deactivate**: `deactivate_user(session, user_id)`
- **Verify**: `verify_user(session, user_id)`

#### Student Operations
- **Create**: `create_student(session, roll_number, first_name, last_name, email, program_id, **kwargs)`
- **Read**: `get_student(session, student_id)`
- **Read by Roll**: `get_student_by_roll(session, roll_number)`
- **Update**: `update_student(session, student_id, **data)`
- **Delete**: `delete_student(session, student_id)`
- **List**: `list_students(session, skip=0, limit=100, **filters)`
- **Search**: `search_students(session, query, limit=10)`

### 3. AttainmentService (`app/modules/attainment_engine/services/attainment_service.py`)

#### CO Attainment Operations
- **Create**: `create_co_attainment(**data)`
- **Read**: `get_co_attainment(attainment_id)`
- **Update**: `update_co_attainment(attainment_id, **data)`
- **Delete**: `delete_co_attainment(attainment_id)`
- **List**: `list_co_attainments(course_id, skip=0, limit=100)`

#### PO Attainment Operations
- **Create**: `create_po_attainment(**data)`
- **Read**: `get_po_attainment(attainment_id)`
- **Update**: `update_po_attainment(attainment_id, **data)`
- **Delete**: `delete_po_attainment(attainment_id)`
- **List**: `list_po_attainments(course_id, skip=0, limit=100)`

#### Report Operations
- **Create**: `generate_report(course_id, report_type, user_id)`
- **Read**: `get_report(report_id)`
- **Update**: `update_report(report_id, **data)`
- **Delete**: `delete_report(report_id)`
- **List**: `list_reports(course_id=None, skip=0, limit=100)`

#### Additional Operations
- **Count Attainments**: `count_attainments(course_id, attainment_type="co")`
- **Latest Attainments**: `get_latest_attainments(course_id, limit=10)`

#### Existing Complex Operations (Preserved)
- **Calculate CO Attainments**: `calculate_course_outcome_attainments(course_id, exam_id, threshold_pct)`
- **Calculate Weighted CO**: `calculate_weighted_co_attainments(course_id, threshold_pct)`
- **Calculate PO Attainments**: `calculate_program_outcome_attainments(course_id, program_id)`
- **Full Pipeline**: `run_full_attainment_pipeline(course_id, program_id, threshold_pct)`
- **Get Summary**: `get_course_attainment_summary(course_id)`
- **Get Matrix**: `get_co_po_matrix(course_id)`
- **Student Performance**: `get_student_performance(course_id, exam_id)`
- **Visualization Data**: `get_visualization_data(course_id)`

## Usage Examples

### Basic CRUD Operations

```python
from app.modules.courses.services.course_service import CourseService
from app.modules.user.services.user_service import UserService
from app.modules.attainment_engine.services.attainment_service import AttainmentService

# Course CRUD
async def course_operations(session):
    course_service = CourseService(session)
    
    # Create
    course = await course_service.create_course(
        course_code="CS101",
        course_name="Programming",
        credits=4,
        semester=1,
        description="Basic programming",
        faculty_id="faculty-123"
    )
    
    # Read
    course = await course_service.get_course(course.id)
    
    # Update
    course = await course_service.update_course(
        course.id,
        description="Updated description"
    )
    
    # Delete
    deleted = await course_service.delete_course(course.id)
    
    # List with filters
    courses = await course_service.list_courses(
        semester=1,
        department="CS"
    )
    
    # Search
    results = await course_service.search_courses("Programming")
    
    # Count
    count = await course_service.count_courses(semester=1)

# User CRUD
async def user_operations(session):
    user_service = UserService()
    
    # Create
    user = await user_service.create_user(
        session=session,
        username="john_doe",
        email="john@example.com",
        password="secure123",
        full_name="John Doe",
        role="faculty"
    )
    
    # Read
    user = await user_service.get_user_by_email(session, "john@example.com")
    
    # Update
    user = await user_service.update_user(
        session,
        user.id,
        department="Computer Science"
    )
    
    # List
    users = await user_service.list_users(
        session,
        role="faculty",
        is_active=True
    )

# Attainment CRUD
async def attainment_operations(session):
    attainment_service = AttainmentService(session)
    
    # Create CO Attainment
    co_attainment = await attainment_service.create_co_attainment(
        course_outcome_id="co-123",
        exam_id="exam-123",
        attainment_percentage=75.0,
        attainment_level="Level 3"
    )
    
    # Read
    attainment = await attainment_service.get_co_attainment(co_attainment.id)
    
    # Update
    attainment = await attainment_service.update_co_attainment(
        co_attainment.id,
        attainment_percentage=80.0
    )
    
    # List
    attainments = await attainment_service.list_co_attainments("course-123")
```

### Advanced Operations

```python
# Complex filtering and searching
courses = await course_service.list_courses(
    semester=1,
    department="Computer Science",
    skip=0,
    limit=50
)

# Search across multiple fields
users = await user_service.search_users(session, "john doe")
students = await user_service.search_students(session, "CS2024")

# Count with filters
faculty_count = await user_service.count_users(
    session,
    role="faculty",
    department="CS",
    is_active=True
)

# Latest attainments
latest = await attainment_service.get_latest_attainments("course-123", limit=5)
```

## Key Features

1. **Consistent API**: All services follow the same CRUD pattern
2. **Repository Pattern**: Uses existing `BaseRepository` for database operations
3. **Transaction Management**: Proper commit/rollback handling
4. **Error Handling**: Comprehensive exception handling with logging
5. **Filtering**: Advanced filtering capabilities for list operations
6. **Search**: Full-text search across relevant fields
7. **Pagination**: Built-in pagination support
8. **Validation**: Input validation and existence checks
9. **Logging**: Comprehensive logging for all operations
10. **Backwards Compatibility**: All existing functionality preserved

## Benefits

- **Reduced Code Duplication**: Common operations handled by base repository
- **Consistent Behavior**: Same patterns across all services
- **Easy Maintenance**: Centralized database logic
- **Better Testing**: Standardized operations are easier to test
- **Enhanced Functionality**: Rich set of operations beyond basic CRUD
- **Performance**: Optimized queries with proper indexing
- **Scalability**: Pagination and filtering for large datasets

## Integration with Existing API

All enhanced CRUD operations are fully compatible with the existing API routes in `app/api/v1/routes.py`. The existing endpoints continue to work while new functionality is available for future enhancements.

The services maintain all existing business logic while adding comprehensive CRUD capabilities, making the system more robust and feature-complete.