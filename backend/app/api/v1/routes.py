"""
OBE System – Complete API Routes
All routes implement real OBE algorithms with no mocks.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import hashlib
import secrets
import uuid
from celery.result import AsyncResult

from app.core.database.connection_manager import get_session
from app.core.infrastructure.celery_app import celery_app
from app.core.security.jwt_auth import get_current_user
from app.core.database.models import (
    User, Course, CourseOutcome, Exam, Program, ProgramOutcome, ProgramSpecificOutcome,
    ExamQuestion, COAttainment, POAttainment, StudentEnrollment, AuditLog,
    co_po_mapping_table, co_pso_mapping_table,
)
from app.api.schemas import (
    UserLogin, UserRegister, TokenResponse,
    CourseCreate, CourseResponse,
    COCreate, COResponse,
    ExamCreate, ExamResponse,
    MarksUpload, AttainmentResponse, ReportResponse,
    COGenerateRequest, COGenerateResponse,
    SyllabusUpdate, QuestionsAddRequest, BulkMarksRequest,
    ChatMessage, ChatResponse,
    QuestionSearchRequest, PresignRequest,
    NotificationMarkReadRequest, AcademicYearConfig,
    ForgotPasswordRequest, ResendOtpRequest, VerifyOtpRequest, ResetPasswordRequest,
    ChangePasswordRequest, COMappingsUpdate,
)
from app.modules.auth.services.auth_service import AuthService
from app.modules.user.services.user_service import UserService
from app.modules.courses.services.course_service import CourseService
from app.modules.attainment_engine.services.attainment_service import AttainmentService
from app.modules.question_analysis.services.question_analysis_service import QuestionAnalysisService
from app.modules.co_generation.services.co_generation_service import CoGenerationService
from app.core.logging.system_logger import SystemLogger
from app.modules.attainment_engine.tasks.attainment_tasks import run_full_pipeline_task
from app.core.infrastructure.redis_client import get_json, set_json, delete_key
from app.core.infrastructure.multi_tier_cache import invalidate_course_report_cache, invalidate_exam_preview_cache
from app.services.course_lead_service import CourseLeadService
from app.services.three_message_flow_service import (
    ThreeMessageFlowService,
    validate_course_matrix_before_save,
    validate_matrix,
)
from app.core.config.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["api"])
logger = SystemLogger("api_routes")


# All routes use persisted services (DB/Redis) for runtime state.


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _password_policy(password: str) -> Dict[str, Any]:
    checks = {
        "min_length": len(password) >= 8,
        "uppercase": any(ch.isupper() for ch in password),
        "lowercase": any(ch.islower() for ch in password),
        "digit": any(ch.isdigit() for ch in password),
        "special": any(not ch.isalnum() for ch in password),
    }
    score = sum(1 for ok in checks.values() if ok)
    if score <= 2:
        strength = "weak"
    elif score <= 4:
        strength = "medium"
    else:
        strength = "strong"
    return {
        "checks": checks,
        "score": score,
        "strength": strength,
        "valid": all(checks.values()),
    }


def _otp_hash(raw_otp: str) -> str:
    return hashlib.sha256(raw_otp.encode("utf-8")).hexdigest()


def _new_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


async def _verify_reset_identity(session: AsyncSession, employee_id: str, email: str) -> User:
    emp_lower = employee_id.strip().lower()
    email_lower = email.strip().lower()
    result = await session.execute(
        select(User).where(
            func.lower(User.email) == email_lower,
            or_(
                func.lower(User.username) == emp_lower,
                func.lower(User.email) == emp_lower,
            ),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Identity not found")
    return user


async def _issue_reset_otp(email: str) -> Dict[str, Any]:
    otp = _new_otp()
    now = datetime.utcnow()
    payload = {
        "otp_hash": _otp_hash(otp),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "resend_after": (now + timedelta(seconds=60)).isoformat(),
        "attempts": 0,
        "verified": False,
    }
    await set_json(f"auth:otp:{email.lower()}", payload, ttl_seconds=600)

    from app.core.infrastructure.celery_tasks import send_email_notification

    subject = "Password Reset OTP"
    html = (
        "<p>Your password reset OTP is: "
        f"<strong>{otp}</strong></p>"
        "<p>This OTP expires in 10 minutes.</p>"
        "<p>If you did not request this, please ignore this email.</p>"
    )
    send_email_notification.delay(
        to_email=email,
        subject=subject,
        body=html,
        notification_type="password_reset_otp",
    )

    return {"otp": otp, **payload}


def _seconds_remaining(iso_time: str) -> int:
    target = datetime.fromisoformat(iso_time)
    delta = int((target - datetime.utcnow()).total_seconds())
    return max(0, delta)


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _format_time_ago(value: datetime, now: Optional[datetime] = None) -> str:
    now = now or datetime.utcnow()
    delta = now - value
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _greeting_for_hour(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _level_short(level: Optional[str]) -> str:
    value = (level or "").strip().lower()
    if value == "level 3":
        return "L3"
    if value == "level 2":
        return "L2"
    if value == "level 1":
        return "L1"
    return "--"


def _marks_status_to_label(status: str) -> Tuple[str, str, int]:
    value = (status or "").strip().lower()
    if value == "approved":
        return ("Approved", "green", 0)
    if value == "submitted":
        return ("Pending Approval", "amber", 2)
    if value == "not_configured":
        return ("Not Configured", "red", 4)
    return ("Pending Upload", "red", 3)


def _co_status_text(total_cos: int, target_cos: int = 5) -> Tuple[str, str, int]:
    if total_cos <= 0:
        return ("Pending - 0 COs", "red", target_cos)
    if total_cos >= target_cos:
        return (f"Generated ({target_cos}/{target_cos})", "green", 0)
    return (f"Generated ({total_cos}/{target_cos})", "amber", target_cos - total_cos)


def _sort_key_for_course(item: Dict[str, Any], sort_by: str) -> Any:
    if sort_by == "course_code":
        return (item.get("course_code") or "").upper()
    if sort_by == "course_name":
        return (item.get("course_name") or "").upper()
    if sort_by == "semester":
        return int(item.get("semester") or 0)
    if sort_by == "enrolled_students":
        return int(item.get("enrolled_students") or 0)
    if sort_by == "co_status":
        return int(item.get("co_pending_count") or 0)
    if sort_by == "marks_status":
        return int(item.get("marks_urgency") or 0)
    return int(item.get("urgency_score") or 0)


async def _safe_get_json(key: str) -> Optional[Dict[str, Any]]:
    try:
        return await get_json(key)
    except Exception:
        return None


async def _safe_set_json(key: str, payload: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
    try:
        await set_json(key, payload, ttl_seconds=ttl_seconds)
    except Exception:
        return


def _default_ay_configs() -> List[Dict[str, Any]]:
    return [
        {"code": "2025-26", "is_active": True, "is_locked": False, "read_only": False, "lock_date": None},
        {"code": "2024-25", "is_active": False, "is_locked": True, "read_only": True, "lock_date": "2025-06-30T00:00:00Z"},
        {"code": "2023-24", "is_active": False, "is_locked": True, "read_only": True, "lock_date": "2024-06-30T00:00:00Z"},
        {"code": "2022-23", "is_active": False, "is_locked": True, "read_only": True, "lock_date": "2023-06-30T00:00:00Z"},
    ]


async def _get_ay_configs() -> List[Dict[str, Any]]:
    cached = await _safe_get_json("faculty:ay_configs")
    items = cached.get("items") if isinstance(cached, dict) else None
    if isinstance(items, list):
        normalized = [item for item in items if isinstance(item, dict) and item.get("code")]
        if normalized:
            return normalized

    defaults = _default_ay_configs()
    await _safe_set_json("faculty:ay_configs", {"items": defaults}, ttl_seconds=86400 * 30)
    return defaults


async def _get_current_ay() -> Optional[str]:
    configs = await _get_ay_configs()
    for ay in configs:
        if ay.get("is_active"):
            return ay.get("code")
    return configs[0].get("code") if configs else None


async def _add_notification(user_id: str, title: str, message: str, notification_type: str, action_link: Optional[str] = None) -> Dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "type": notification_type,
        "action_link": action_link,
        "is_read": False,
        "created_at": _now_iso(),
    }
    key = f"faculty:notifications:{user_id}"
    payload = await _safe_get_json(key)
    items = list(payload.get("items", [])) if payload else []
    items.insert(0, item)
    items = items[:200]
    await _safe_set_json(key, {"items": items}, ttl_seconds=86400 * 14)
    return item


async def _get_notifications(user_id: str) -> List[Dict[str, Any]]:
    key = f"faculty:notifications:{user_id}"
    payload = await _safe_get_json(key)
    if payload and isinstance(payload.get("items"), list):
        return payload["items"]
    return []


async def _set_co_lock(course_id: str, locked: bool, by: str, reason: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "course_id": course_id,
        "locked": bool(locked),
        "locked_by": by,
        "reason": reason,
        "updated_at": _now_iso(),
    }
    await _safe_set_json(f"faculty:co_lock:{course_id}", payload, ttl_seconds=86400 * 30)
    return payload


async def _get_co_lock(course_id: str) -> Dict[str, Any]:
    payload = await _safe_get_json(f"faculty:co_lock:{course_id}")
    if payload:
        return payload
    return {"course_id": course_id, "locked": False, "locked_by": None, "reason": None, "updated_at": _now_iso()}


def _co_lock_blocks_for_user(lock: Dict[str, Any], user: User) -> bool:
    """Return True only when CO lock should block current user."""
    if not lock.get("locked"):
        return False

    role = _role_value(user)
    if role in {"admin", "hod", "accreditation_officer"}:
        return False

    return str(lock.get("locked_by") or "") != str(user.id)


def _co_defaults_key(course_code: str, regulation: str) -> str:
    return f"co_defaults:{course_code.strip().upper()}:{regulation.strip()}"


async def _set_exam_meta(exam_id: str, meta: Dict[str, Any]) -> None:
    await _safe_set_json(f"exam_meta:{exam_id}", meta, ttl_seconds=86400 * 30)


async def _get_exam_meta(exam_id: str) -> Dict[str, Any]:
    payload = await _safe_get_json(f"exam_meta:{exam_id}")
    if payload:
        return payload
    return {}


async def _set_question_meta(exam_id: str, questions: List[Dict[str, Any]]) -> None:
    payload = {"exam_id": exam_id, "questions": questions, "updated_at": _now_iso()}
    await _safe_set_json(f"exam_question_meta:{exam_id}", payload, ttl_seconds=86400 * 30)


def _role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role).lower()


async def _assert_faculty_owns_course(session: AsyncSession, user: User, course_id: str) -> Course:
    result = await session.execute(
        select(Course).where((Course.id == course_id) | (Course.course_code == course_id))
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if _role_value(user) != "faculty":
        return course

    if str(course.created_by) != str(user.id):
        raise HTTPException(status_code=403, detail="Faculty can access only own courses")
    return course


def _dept_program_key(department: Optional[str]) -> str:
    dept = (department or "").strip().upper()
    return f"DEPT:{dept}" if dept else "DEPT:GENERAL"


async def _count_pos_for_program(session: AsyncSession, program_key: str) -> int:
    result = await session.execute(
        select(func.count(ProgramOutcome.id)).where(ProgramOutcome.program == program_key)
    )
    return int(result.scalar() or 0)


async def _count_psos_for_program(session: AsyncSession, program_key: str) -> int:
    result = await session.execute(
        select(func.count(ProgramSpecificOutcome.id)).where(ProgramSpecificOutcome.program == program_key)
    )
    return int(result.scalar() or 0)


async def _ensure_nba_pos_seeded(session: AsyncSession, program_key: str) -> None:
    existing_result = await session.execute(
        select(ProgramOutcome.code).where(ProgramOutcome.program == program_key)
    )
    existing_codes = {str(code).strip().upper() for code in existing_result.scalars().all() if code}

    to_create: List[ProgramOutcome] = []
    for item in _NBA_POS:
        code = str(item.get("code") or "").strip().upper()
        if not code or code in existing_codes:
            continue
        statement = str(item.get("statement") or item.get("name") or code).strip() or code
        to_create.append(
            ProgramOutcome(
                id=str(uuid.uuid4()),
                code=code,
                statement=statement,
                description=statement,
                program=program_key,
            )
        )

    if to_create:
        session.add_all(to_create)
        await session.commit()


async def _resolve_program_key_for_course(
    session: AsyncSession,
    course_id: str,
    requested_program_id: Optional[str],
    *,
    require: str = "po",
) -> str:
    course_result = await session.execute(
        select(Course).where((Course.id == course_id) | (Course.course_code == course_id))
    )
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    requested = (requested_program_id or "").strip()
    candidates: List[str] = []

    def add_candidate(value: Optional[str]) -> None:
        key = (value or "").strip()
        if key and key not in candidates:
            candidates.append(key)

    add_candidate(requested)

    if requested:
        program_result = await session.execute(
            select(Program).where((Program.id == requested) | (Program.code == requested))
        )
        program_row = program_result.scalar_one_or_none()
        if program_row:
            add_candidate(program_row.code)

    add_candidate(_dept_program_key(getattr(course, "department", None)))

    mapped_po_keys = await session.execute(
        select(ProgramOutcome.program)
        .join(co_po_mapping_table, co_po_mapping_table.c.program_outcome_id == ProgramOutcome.id)
        .join(CourseOutcome, CourseOutcome.id == co_po_mapping_table.c.course_outcome_id)
        .where(CourseOutcome.course_id == course.id)
        .distinct()
    )
    for key in mapped_po_keys.scalars().all():
        add_candidate(key)

    mapped_pso_keys = await session.execute(
        select(ProgramSpecificOutcome.program)
        .join(co_pso_mapping_table, co_pso_mapping_table.c.program_specific_outcome_id == ProgramSpecificOutcome.id)
        .join(CourseOutcome, CourseOutcome.id == co_pso_mapping_table.c.course_outcome_id)
        .where(CourseOutcome.course_id == course.id)
        .distinct()
    )
    for key in mapped_pso_keys.scalars().all():
        add_candidate(key)

    if not candidates:
        raise HTTPException(status_code=400, detail="Unable to resolve a program key for this course")

    best_key = candidates[0]
    best_score = -1
    best_po_count = 0
    best_pso_count = 0

    for key in candidates:
        po_count = await _count_pos_for_program(session, key)
        pso_count = await _count_psos_for_program(session, key)
        if require == "pso":
            score = (2 if pso_count > 0 else 0) + (1 if po_count > 0 else 0)
        elif require == "both":
            score = (2 if po_count > 0 else 0) + (2 if pso_count > 0 else 0)
        else:
            score = (2 if po_count > 0 else 0) + (1 if pso_count > 0 else 0)
        if requested and key == requested:
            score += 1
        if score > best_score:
            best_score = score
            best_key = key
            best_po_count = po_count
            best_pso_count = pso_count

    if require in {"po", "both"} and best_po_count <= 0:
        await _ensure_nba_pos_seeded(session, best_key)
        best_po_count = await _count_pos_for_program(session, best_key)

    if require == "po" and best_po_count <= 0:
        raise HTTPException(status_code=400, detail="No Program Outcomes found for this course context")
    if require == "pso" and best_pso_count <= 0:
        raise HTTPException(status_code=400, detail="No Program Specific Outcomes found for this course context")

    return best_key


async def _assert_faculty_owns_exam(session: AsyncSession, user: User, exam_id: str) -> Exam:
    ex_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = ex_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    await _assert_faculty_owns_course(session, user, exam.course_id)
    return exam


class CourseUpdateRequest(BaseModel):
    course_name: Optional[str] = None
    credits: Optional[int] = None
    semester: Optional[int] = None
    description: Optional[str] = None
    course_type: Optional[str] = None
    enrolled_students: Optional[int] = None
    fa_method: Optional[str] = None
    fa_best_n: Optional[int] = None
    fa_total_components: Optional[int] = None
    fa_weight: Optional[float] = None
    sa_weight: Optional[float] = None
    department: Optional[str] = None
    created_by: Optional[str] = None


class OutcomeUpdateRequest(BaseModel):
    code: Optional[str] = None
    statement: Optional[str] = None
    bloom_level: Optional[str] = None
    description: Optional[str] = None


class ExamUpdateRequest(BaseModel):
    assessment_code: Optional[str] = None
    exam_name: Optional[str] = None
    exam_type: Optional[str] = None
    total_marks: Optional[int] = None
    duration_minutes: Optional[int] = None
    weightage_pct: Optional[float] = None
    exam_date: Optional[datetime] = None
    units_covered: Optional[List[str]] = None
    number_of_questions: Optional[int] = None


class QuestionUpdateRequest(BaseModel):
    question_number: Optional[int] = None
    question_text: Optional[str] = None
    marks: Optional[float] = None
    question_type: Optional[str] = None
    bloom_level: Optional[str] = None
    override_reason: Optional[str] = None


class ProgramOutcomePayload(BaseModel):
    code: str
    statement: str
    description: Optional[str] = None


class CODefaultsPayload(BaseModel):
    templates: List[Dict[str, Any]]


class ChatbotValidateMatrixRequest(BaseModel):
    session_id: str
    mapping: Dict[str, Any]
    course_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/auth/register", response_model=TokenResponse, summary="Register a new user")
async def register(payload: UserRegister, session: AsyncSession = Depends(get_session)):
    from sqlalchemy.exc import IntegrityError
    svc = AuthService(session)
    try:
        user = await svc.register_user(
            username=payload.username, email=payload.email, password=payload.password,
            full_name=payload.full_name, role=payload.role or "faculty",
            department=getattr(payload, "department", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A user with this email or username already exists.")
    except Exception as exc:
        await session.rollback()
        logger.error(f"Registration error: {exc}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(exc)}")
    token = svc.create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "role": user.role}


@router.post("/auth/login", response_model=TokenResponse, summary="Login and get JWT token")
async def login(payload: UserLogin, session: AsyncSession = Depends(get_session)):
    svc = AuthService(session)

    if not payload.email and not payload.employee_id:
        raise HTTPException(status_code=400, detail="Either email or employee_id is required")

    user = None
    if payload.email:
        user = await svc.authenticate_user(str(payload.email), payload.password)
    elif payload.employee_id:
        result = await session.execute(select(User).where(User.username == payload.employee_id))
        found = result.scalar_one_or_none()
        if found:
            user = await svc.authenticate_user(found.email, payload.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_department = str(getattr(user, "department", "") or "").strip().lower()
    if payload.department and stored_department and stored_department != payload.department.strip().lower():
        raise HTTPException(status_code=403, detail="Department mismatch")

    if payload.academic_year:
        ay_configs = await _get_ay_configs()
        ay = next((x for x in ay_configs if x.get("code") == payload.academic_year), None)
        if not ay:
            raise HTTPException(status_code=400, detail="Academic year not found")
        if not ay.get("is_active"):
            raise HTTPException(status_code=403, detail="Selected academic year is not active")

    token = svc.create_access_token(user.id, expires_delta=timedelta(days=7) if payload.remember_me else None)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "role": user.role}


@router.get("/auth/role-options", summary="Get role options for authenticated user")
async def auth_role_options(current_user: User = Depends(get_current_user)):
    role = _role_value(current_user)
    secondary = []
    payload = await _safe_get_json(f"auth:secondary_roles:{current_user.id}")
    if payload and isinstance(payload.get("roles"), list):
        secondary = payload["roles"]
    all_roles = [role] + [r for r in secondary if r != role]
    return {"primary_role": role, "available_roles": all_roles}


@router.post("/auth/forgot-password", summary="Generate OTP for password reset")
async def auth_forgot_password(payload: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)):
    await _verify_reset_identity(session, payload.employee_id, str(payload.email))
    issued = await _issue_reset_otp(str(payload.email))
    from app.core.config.settings import get_settings
    settings = get_settings()
    resp: Dict[str, Any] = {
        "status": "otp_sent",
        "email": str(payload.email),
        "expires_in_seconds": _seconds_remaining(issued["expires_at"]),
        "resend_in_seconds": _seconds_remaining(issued["resend_after"]),
    }
    # In development/debug mode return the OTP directly since no SMTP is configured
    if settings.debug or settings.environment != "production":
        resp["dev_otp"] = issued["otp"]
    return resp


@router.post("/auth/resend-otp", summary="Resend OTP for password reset")
async def auth_resend_otp(payload: ResendOtpRequest, session: AsyncSession = Depends(get_session)):
    await _verify_reset_identity(session, payload.employee_id, str(payload.email))
    key = f"auth:otp:{str(payload.email).lower()}"
    existing = await get_json(key)
    if existing:
        remaining = _seconds_remaining(existing.get("resend_after", _now_iso()))
        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Resend available in {remaining} seconds",
            )

    issued = await _issue_reset_otp(str(payload.email))
    return {
        "status": "otp_resent",
        "email": str(payload.email),
        "expires_in_seconds": _seconds_remaining(issued["expires_at"]),
        "resend_in_seconds": _seconds_remaining(issued["resend_after"]),
    }


@router.post("/auth/verify-otp", summary="Verify OTP for password reset")
async def auth_verify_otp(payload: VerifyOtpRequest, session: AsyncSession = Depends(get_session)):
    await _verify_reset_identity(session, payload.employee_id, str(payload.email))
    key = f"auth:otp:{str(payload.email).lower()}"
    if not payload.otp.isdigit() or len(payload.otp) != 6:
        raise HTTPException(status_code=400, detail="OTP must be exactly 6 digits")

    otp_state = await get_json(key)
    if not otp_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    if _seconds_remaining(otp_state.get("expires_at", _now_iso())) <= 0:
        await delete_key(key)
        raise HTTPException(status_code=400, detail="OTP expired")

    attempts = int(otp_state.get("attempts", 0))
    if attempts >= 5:
        await delete_key(key)
        raise HTTPException(status_code=429, detail="Too many OTP attempts. Request a new OTP")

    if _otp_hash(payload.otp) != str(otp_state.get("otp_hash", "")):
        otp_state["attempts"] = attempts + 1
        await set_json(key, otp_state, ttl_seconds=600)
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_state["verified"] = True
    otp_state["verified_at"] = _now_iso()
    await set_json(key, otp_state, ttl_seconds=600)
    return {"status": "otp_verified", "email": str(payload.email)}


class _PasswordStrengthRequest(BaseModel):
    password: str


@router.post("/auth/password-strength", summary="Check password strength and requirements")
async def auth_password_strength(payload: _PasswordStrengthRequest):
    policy = _password_policy(payload.password)
    return {
        "strength": policy["strength"],
        "score": policy["score"],
        "requirements": policy["checks"],
        "valid": policy["valid"],
    }


@router.post("/auth/reset-password", summary="Reset password using OTP")
async def auth_reset_password(payload: ResetPasswordRequest, session: AsyncSession = Depends(get_session)):
    user = await _verify_reset_identity(session, payload.employee_id, str(payload.email))
    key = f"auth:otp:{str(payload.email).lower()}"
    if not payload.otp.isdigit() or len(payload.otp) != 6:
        raise HTTPException(status_code=400, detail="OTP must be exactly 6 digits")

    otp_state = await get_json(key)
    if not otp_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    if _seconds_remaining(otp_state.get("expires_at", _now_iso())) <= 0:
        await delete_key(key)
        raise HTTPException(status_code=400, detail="OTP expired")

    if _otp_hash(payload.otp) != str(otp_state.get("otp_hash", "")):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm password do not match")

    policy = _password_policy(payload.new_password)
    if not policy["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Password does not meet policy requirements",
                "requirements": policy["checks"],
                "strength": policy["strength"],
            },
        )

    from app.core.security.password_hashing import hash_password

    user.hashed_password = hash_password(payload.new_password)
    await session.commit()
    await delete_key(key)
    return {
        "status": "password_reset_success",
        "message": "Password updated successfully. You will be redirected to login in 3 seconds.",
        "redirect_in_seconds": 3,
    }


@router.post("/auth/change-password", summary="Change password (authenticated user, e.g. first-login)")
async def auth_change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match")
    policy = _password_policy(payload.new_password)
    if not policy["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Password does not meet policy requirements",
                "requirements": policy["checks"],
                "strength": policy["strength"],
            },
        )
    user_svc = UserService()
    success = await user_svc.change_password(
        session, str(current_user.id), payload.old_password, payload.new_password
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid current password")
    await session.commit()
    return {"status": "success", "message": "Password changed successfully"}


@router.get("/academic-years", summary="List academic years")
async def list_academic_years(current_user: User = Depends(get_current_user)):
    items = await _get_ay_configs()
    return {"items": items}


@router.get("/academic-years/current", summary="Get current active academic year")
async def current_academic_year(current_user: User = Depends(get_current_user)):
    code = await _get_current_ay()
    return {"code": code}


@router.post("/academic-years", summary="Create or update academic year config")
async def upsert_academic_year(
    payload: AcademicYearConfig,
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in {"admin", "hod"}:
        raise HTTPException(status_code=403, detail="Only HOD/Admin can configure academic years")

    items = await _get_ay_configs()
    exists = next((x for x in items if x.get("code") == payload.code), None)
    if exists:
        exists.update(payload.model_dump())
    else:
        items.append(payload.model_dump())

    if payload.is_active:
        for ay in items:
            if ay.get("code") != payload.code:
                ay["is_active"] = False
    await _safe_set_json("faculty:ay_configs", {"items": items}, ttl_seconds=86400)
    return {"status": "saved", "item": payload.model_dump()}


@router.post("/academic-years/{ay_code}/lock", summary="Lock an academic year")
async def lock_academic_year(
    ay_code: str,
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in {"admin", "hod"}:
        raise HTTPException(status_code=403, detail="Only HOD/Admin can lock academic years")

    items = await _get_ay_configs()
    ay = next((x for x in items if x.get("code") == ay_code), None)
    if not ay:
        raise HTTPException(status_code=404, detail="Academic year not found")

    ay["is_locked"] = True
    ay["read_only"] = True
    await _safe_set_json("faculty:ay_configs", {"items": items}, ttl_seconds=86400)
    return {"status": "locked", "code": ay_code}


@router.get("/users", summary="List all users (admin only)")
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) != "admin":
        raise HTTPException(status_code=403, detail="Only admin can list users")
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name or "",
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "department": u.department or "",
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.put("/users/{user_id}", summary="Update user (admin only)")
async def update_user(
    user_id: str,
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update users")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "role" in payload:
        from app.core.config.constants import UserRole
        raw = (payload["role"] or "faculty").lower().strip()
        role_map = {"department_head": "hod", "subject_lead": "course_lead"}
        raw = role_map.get(raw, raw)
        try:
            user.role = UserRole(raw)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {[r.value for r in UserRole]}")
    if "department" in payload:
        user.department = str(payload["department"]) if payload["department"] is not None else None
    if "full_name" in payload:
        user.full_name = str(payload["full_name"]) if payload["full_name"] is not None else None
    if "is_active" in payload:
        user.is_active = bool(payload["is_active"])
    await session.commit()
    return {"id": str(user.id), "username": user.username, "email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role), "department": user.department or "", "is_active": user.is_active}


@router.get("/programs", summary="List all programs")
async def list_programs(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Program).order_by(Program.code))
    programs = result.scalars().all()
    return [{"id": str(p.id), "code": p.code, "name": p.name, "description": p.description or ""} for p in programs]


@router.get("/audit-log", summary="List audit log entries (admin/HOD)")
async def list_audit_log(
    limit: int = Query(200, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in {"admin", "hod"}:
        raise HTTPException(status_code=403, detail="Audit log is available only for admin or HOD")
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "timestamp": r.timestamp.isoformat() if r.timestamp else "",
            "type": r.entity_type or "system",
            "userId": r.user_id or "",
            "action": r.action or "",
            "ip": r.ip_address or "",
        }
        for r in rows
    ]


@router.get("/settings/thresholds", summary="Get attainment level thresholds")
async def get_thresholds(current_user: User = Depends(get_current_user)):
    s = get_settings()
    l2_default = getattr(s, "attainment_level_2_threshold", 0.50)
    l3_default = getattr(s, "attainment_level_3_threshold", 0.60)
    cached = await get_json("obe:thresholds")
    if cached:
        return {
            "level2": cached.get("level2", l2_default),
            "level3": cached.get("level3", l3_default),
            "pass_threshold": cached.get("pass_threshold", getattr(s, "co_attainment_threshold", 0.40)),
        }
    return {
        "level2": l2_default,
        "level3": l3_default,
        "pass_threshold": getattr(s, "co_attainment_threshold", 0.40),
    }


@router.put("/settings/thresholds", summary="Update attainment level thresholds (admin/HOD)")
async def update_thresholds(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in {"admin", "hod"}:
        raise HTTPException(status_code=403, detail="Only admin or HOD can update thresholds")
    level2 = payload.get("level2")
    level3 = payload.get("level3")
    pass_threshold = payload.get("pass_threshold")
    if level2 is not None and not (0 < level2 < 1):
        raise HTTPException(status_code=400, detail="level2 must be between 0 and 1")
    if level3 is not None and not (0 < level3 < 1):
        raise HTTPException(status_code=400, detail="level3 must be between 0 and 1")
    if pass_threshold is not None and not (0 < pass_threshold < 1):
        raise HTTPException(status_code=400, detail="pass_threshold must be between 0 and 1")
    if level2 is not None and level3 is not None and level2 >= level3:
        raise HTTPException(status_code=400, detail="level2 must be less than level3")
    current = await get_json("obe:thresholds") or {}
    if level2 is not None:
        current["level2"] = float(level2)
    if level3 is not None:
        current["level3"] = float(level3)
    if pass_threshold is not None:
        current["pass_threshold"] = float(pass_threshold)
    await set_json("obe:thresholds", current)
    return {"status": "saved", "thresholds": current}


@router.get("/faculty/notifications", summary="Faculty notification center")
async def faculty_notifications(current_user: User = Depends(get_current_user)):
    items = await _get_notifications(str(current_user.id))
    unread = sum(1 for i in items if not i.get("is_read"))
    return {"count": len(items), "unread": unread, "items": items}


@router.post("/faculty/notifications/mark-read", summary="Mark notifications as read")
async def faculty_notifications_mark_read(
    payload: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)
    items = await _get_notifications(user_id)
    mark_set = {str(x) for x in payload.notification_ids}
    changed = 0
    for item in items:
        if item.get("id") in mark_set and not item.get("is_read"):
            item["is_read"] = True
            changed += 1
    await _safe_set_json(f"faculty:notifications:{user_id}", {"items": items}, ttl_seconds=86400 * 14)
    return {"status": "ok", "updated": changed}


@router.get("/faculty/dashboard", summary="Faculty dashboard aggregate")
async def faculty_dashboard(
    ay_code: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Filter courses by course code or course name"),
    sort_by: str = Query("urgency", description="urgency|course_code|course_name|semester|enrolled_students|co_status|marks_status"),
    sort_dir: str = Query("desc", description="asc|desc"),
    show_completed: bool = Query(False, description="Include completed actions older than 24h"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    role = _role_value(current_user)
    if role not in {"faculty", "course_lead", "subject_lead"}:
        raise HTTPException(status_code=403, detail="Faculty dashboard is available for faculty, course lead, and subject lead roles")

    now_utc = datetime.utcnow()
    now_local = datetime.now()

    ay_configs = await _get_ay_configs()
    active_cfg = None
    if ay_code:
        active_cfg = next((x for x in ay_configs if x.get("code") == ay_code), None)
    if not active_cfg:
        active_cfg = next((x for x in ay_configs if x.get("is_active")), ay_configs[0] if ay_configs else {"code": ay_code or "N/A", "is_active": True, "is_locked": False, "read_only": False})

    active_ay = active_cfg.get("code")
    ay_lock_date = _parse_iso_datetime(active_cfg.get("lock_date"))
    near_lock = bool(ay_lock_date and timedelta(0) <= (ay_lock_date - now_utc) <= timedelta(days=14))

    course_result = await session.execute(select(Course).where(Course.created_by == current_user.id).order_by(Course.created_at.desc()))
    courses = list(course_result.scalars().all())
    if search:
        term = search.strip().lower()
        courses = [
            c for c in courses
            if term in (c.course_code or "").lower() or term in (c.course_name or "").lower()
        ]

    course_ids = [c.id for c in courses]
    notifications = await _get_notifications(str(current_user.id))

    pending_actions_raw: List[Dict[str, Any]] = []
    completed_actions: List[Dict[str, Any]] = []
    course_rows: List[Dict[str, Any]] = []
    marks_upload_status: List[Dict[str, Any]] = []
    co_status: List[Dict[str, Any]] = []
    attainment_quick_view: List[Dict[str, Any]] = []
    attainment_rows: List[Dict[str, Any]] = []

    nearest_pending_deadline_days: Optional[int] = None
    total_level1_alerts = 0

    for course in courses:
        co_r = await session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course.id).order_by(CourseOutcome.code))
        cos = list(co_r.scalars().all())

        co_text, co_color, co_pending = _co_status_text(len(cos), target_cos=5)
        co_status.append({
            "course_id": course.id,
            "course_code": course.course_code,
            "total_cos": len(cos),
            "generated": len(cos),
            "pending": co_pending,
        })

        enrolled_query = select(func.count(StudentEnrollment.id)).where(StudentEnrollment.course_id == course.id)
        if active_ay:
            enrolled_query = enrolled_query.where(StudentEnrollment.academic_year == active_ay)
        enrolled_query = enrolled_query.where(StudentEnrollment.status == "active")
        enrolled_students = int((await session.execute(enrolled_query)).scalar() or 0)

        exam_r = await session.execute(select(Exam).where(Exam.course_id == course.id).order_by(Exam.created_at))
        exams = list(exam_r.scalars().all())

        marks_details: List[Dict[str, Any]] = []
        configured_assessments: set[str] = set()
        marks_urgency = 0
        marks_approved_exists = False
        has_overdue = False

        for ex in exams:
            meta = await _get_exam_meta(ex.id)
            assessment = (meta.get("assessment_code") or ex.exam_name or "").strip() or "Exam"
            configured_assessments.add(assessment.upper())

            lock = await _safe_get_json(f"marks_lock:{ex.id}")
            raw_status = (lock or {}).get("status") or "not_started"
            label, status_color, urgency = _marks_status_to_label(raw_status)

            due_dt = _parse_iso_datetime(meta.get("exam_date")) or ex.exam_date
            due_days = None
            due_iso = None
            overdue = False
            if due_dt:
                due_iso = due_dt.isoformat()
                due_days = int((due_dt - now_utc).total_seconds() // 86400)
                overdue = due_days < 0 and raw_status != "approved"
                if raw_status != "approved":
                    nearest_pending_deadline_days = due_days if nearest_pending_deadline_days is None else min(nearest_pending_deadline_days, due_days)

            if raw_status == "approved":
                marks_approved_exists = True

            if overdue:
                has_overdue = True

            marks_urgency = max(marks_urgency, urgency + (1 if overdue else 0))
            marks_details.append({
                "exam_id": ex.id,
                "assessment": assessment,
                "exam_name": ex.exam_name,
                "status": raw_status,
                "label": label,
                "color": "red" if overdue else status_color,
                "due_date": due_iso,
                "due_in_days": due_days,
                "overdue": overdue,
                "action_link": f"/faculty/course/{course.id}/marks/{ex.id}",
            })

            marks_upload_status.append({
                "course_id": course.id,
                "course_code": course.course_code,
                "exam_id": ex.id,
                "assessment": assessment,
                "status": raw_status,
            })

            if raw_status in {"not_started", "submitted"}:
                due_note = "No due date"
                if due_dt:
                    due_note = due_dt.strftime("%Y-%m-%d")
                pending_actions_raw.append({
                    "kind": "marks",
                    "priority_weight": 100 if overdue else (80 if raw_status == "submitted" else 70),
                    "description": f"{label} for {assessment}",
                    "course_id": course.id,
                    "course_name": course.course_name,
                    "course_code": course.course_code,
                    "due_date": due_iso,
                    "due_date_label": due_note,
                    "overdue": overdue,
                    "action_link": f"/faculty/course/{course.id}/marks/{ex.id}",
                    "status": "pending",
                })

        for expected in ("T1", "T2", "T3"):
            if expected not in configured_assessments:
                marks_details.append({
                    "exam_id": None,
                    "assessment": expected,
                    "exam_name": None,
                    "status": "not_configured",
                    "label": "Not Configured",
                    "color": "red",
                    "due_date": None,
                    "due_in_days": None,
                    "overdue": False,
                    "action_link": f"/faculty/course/{course.id}/exam-setup",
                })
                marks_urgency = max(marks_urgency, 4)
                pending_actions_raw.append({
                    "kind": "exam_setup",
                    "priority_weight": 65,
                    "description": f"Configure {expected}",
                    "course_id": course.id,
                    "course_name": course.course_name,
                    "course_code": course.course_code,
                    "due_date": None,
                    "due_date_label": "No due date",
                    "overdue": False,
                    "action_link": f"/faculty/course/{course.id}/exam-setup",
                    "status": "pending",
                })

        if co_pending > 0:
            pending_actions_raw.append({
                "kind": "co_generation",
                "priority_weight": 90,
                "description": f"Generate {co_pending} pending CO(s)",
                "course_id": course.id,
                "course_name": course.course_name,
                "course_code": course.course_code,
                "due_date": None,
                "due_date_label": "No due date",
                "overdue": False,
                "action_link": f"/faculty/course/{course.id}/co-generation",
                "status": "pending",
            })

        att_r = await session.execute(
            select(
                CourseOutcome.code,
                COAttainment.attainment_percentage,
                COAttainment.attainment_level,
                COAttainment.calculated_at,
            )
            .join(CourseOutcome, COAttainment.course_outcome_id == CourseOutcome.id)
            .where(CourseOutcome.course_id == course.id)
            .order_by(COAttainment.calculated_at.desc())
        )
        att_rows = list(att_r.all())
        latest_by_code: Dict[str, Dict[str, Any]] = {}
        for code, pct, level, calc_at in att_rows:
            if code not in latest_by_code:
                latest_by_code[code] = {
                    "code": code,
                    "percentage": float(pct or 0.0),
                    "level": str(level or "Level 1"),
                    "calculated_at": calc_at,
                }

        level1_count = sum(1 for v in latest_by_code.values() if str(v.get("level", "")).lower() == "level 1")
        total_level1_alerts += level1_count

        attainment_quick_view.append({
            "course_id": course.id,
            "course_code": course.course_code,
            "co_count": len(latest_by_code),
            "level1_count": level1_count,
            "avg_attainment": round(
                sum(float(v.get("percentage", 0.0)) for v in latest_by_code.values()) / max(len(latest_by_code), 1),
                2,
            ) if latest_by_code else 0.0,
        })

        co_cells = []
        cell_percentages: List[float] = []
        for co_code in ["CO1", "CO2", "CO3", "CO4", "CO5"]:
            value = latest_by_code.get(co_code)
            if value and marks_approved_exists:
                pct = round(float(value["percentage"]), 2)
                lvl = str(value["level"])
                short = _level_short(lvl)
                color = "green" if short == "L3" else ("amber" if short == "L2" else "red")
                co_cells.append({
                    "co_code": co_code,
                    "percentage": pct,
                    "level": short,
                    "text": f"{pct}% ({short})",
                    "color": color,
                    "emphasis": "bold" if short == "L1" else "normal",
                    "drilldown_link": f"/faculty/course/{course.id}/co-attainment",
                })
                cell_percentages.append(pct)
            else:
                co_cells.append({
                    "co_code": co_code,
                    "percentage": None,
                    "level": "--",
                    "text": "--",
                    "color": "muted",
                    "emphasis": "italic",
                    "note": "Pending marks approval",
                    "drilldown_link": f"/faculty/course/{course.id}/co-attainment",
                })

        overall_pct = round(sum(cell_percentages) / len(cell_percentages), 2) if cell_percentages else None
        overall_level = _level_short("Level 1" if overall_pct is None else ("Level 3" if overall_pct >= 70 else ("Level 2" if overall_pct >= 60 else "Level 1")))
        overall_color = "muted" if overall_pct is None else ("green" if overall_level == "L3" else ("amber" if overall_level == "L2" else "red"))

        attainment_rows.append({
            "course_id": course.id,
            "course": f"{course.course_code} - {course.course_name}",
            "pending_marks_approval": not marks_approved_exists,
            "pending_note": "Pending marks approval" if not marks_approved_exists else None,
            "co_cells": co_cells,
            "overall": {
                "percentage": overall_pct,
                "level": "--" if overall_pct is None else overall_level,
                "text": "--" if overall_pct is None else f"{overall_pct}% ({overall_level})",
                "color": overall_color,
                "emphasis": "bold" if overall_level == "L1" else "normal",
            },
        })

        marks_details.sort(key=lambda x: (x.get("assessment") or "", x.get("label") or ""))
        marks_inline = " | ".join(f"{x['assessment']}: {x['label']}" for x in marks_details)
        urgency_score = co_pending * 5 + marks_urgency * 3 + level1_count * 2 + (3 if has_overdue else 0)

        row_actions = [
            {"label": "Open Course", "link": f"/faculty/course/{course.id}", "urgency": 1},
            {"label": "Upload Marks", "link": f"/faculty/course/{course.id}/marks", "urgency": 10 if marks_urgency >= 3 else 2},
            {"label": "Generate COs", "link": f"/faculty/course/{course.id}/co-generation", "urgency": 9 if co_pending > 0 else 0},
        ]
        row_actions = [x for x in row_actions if x["urgency"] > 0]
        row_actions.sort(key=lambda x: x["urgency"], reverse=True)

        course_rows.append({
            "course_id": course.id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "semester": course.semester,
            "enrolled_students": enrolled_students,
            "co_status": co_text,
            "co_status_color": co_color,
            "co_pending_count": co_pending,
            "marks_status": marks_inline,
            "marks_status_details": marks_details,
            "marks_urgency": marks_urgency,
            "actions": [{"label": x["label"], "link": x["link"]} for x in row_actions],
            "primary_action": row_actions[0]["label"] if row_actions else "Open Course",
            "accordion": {
                "expanded_exam_statuses": marks_details,
            },
            "urgency_score": urgency_score,
            "row_click_expandable": True,
        })

    reverse_sort = (sort_dir or "desc").lower() != "asc"
    requested_sort = (sort_by or "urgency").strip().lower()
    valid_sorts = {"urgency", "course_code", "course_name", "semester", "enrolled_students", "co_status", "marks_status"}
    if requested_sort not in valid_sorts:
        requested_sort = "urgency"

    course_rows.sort(key=lambda x: _sort_key_for_course(x, requested_sort), reverse=reverse_sort)

    pending_actions_raw.sort(
        key=lambda x: (
            -int(x.get("priority_weight", 0)),
            x.get("due_date") or "9999-12-31T00:00:00",
            x.get("course_code") or "",
        )
    )
    pending_actions = []
    for idx, item in enumerate(pending_actions_raw, start=1):
        pending_actions.append({
            "priority": idx,
            "description": item.get("description"),
            "course_name": item.get("course_name"),
            "course_code": item.get("course_code"),
            "due_date": item.get("due_date"),
            "due_date_label": item.get("due_date_label"),
            "overdue": bool(item.get("overdue")),
            "action_link": item.get("action_link"),
            "go_link": item.get("action_link"),
            "status": "pending",
        })

    completed_hidden_count = 0
    completion_types = {"marks_approved", "co_generated", "marks_returned"}
    for item in notifications:
        n_type = str(item.get("type") or "")
        if n_type not in completion_types:
            continue
        created_dt = _parse_iso_datetime(item.get("created_at"))
        older_than_day = bool(created_dt and (now_utc - created_dt) > timedelta(hours=24))
        if older_than_day and not show_completed:
            completed_hidden_count += 1
            continue
        completed_actions.append({
            "priority": 0,
            "description": item.get("message") or item.get("title") or "Completed action",
            "course_name": None,
            "course_code": None,
            "due_date": created_dt.isoformat() if created_dt else None,
            "due_date_label": _format_time_ago(created_dt, now_utc) if created_dt else "recently",
            "overdue": False,
            "action_link": item.get("action_link"),
            "go_link": item.get("action_link"),
            "status": "completed",
        })

    for idx, item in enumerate(completed_actions, start=len(pending_actions) + 1):
        item["priority"] = idx

    courses_count = len(course_rows)
    total_co_pending = sum(int(c.get("co_pending_count") or 0) for c in course_rows)
    if nearest_pending_deadline_days is None:
        marks_deadline_phrase = "0 marks deadline"
    elif nearest_pending_deadline_days < 0:
        marks_deadline_phrase = f"1 marks deadline overdue by {abs(nearest_pending_deadline_days)} days"
    elif nearest_pending_deadline_days == 0:
        marks_deadline_phrase = "1 marks deadline today"
    else:
        marks_deadline_phrase = f"1 marks deadline in {nearest_pending_deadline_days} days"

    semester_label = "Odd"
    semester_values = [int(c.semester) for c in courses if c.semester is not None]
    if semester_values:
        odd = sum(1 for x in semester_values if x % 2 == 1)
        even = len(semester_values) - odd
        semester_label = "Odd" if odd >= even else "Even"

    ay_state = "Locked" if bool(active_cfg.get("is_locked")) else "Active"
    ay_context = f"Viewing: Academic Year {active_ay} | {semester_label} Semester | {ay_state}"
    ay_context_color = "amber" if near_lock else ("red" if ay_state == "Locked" else "green")

    welcome_name = current_user.full_name or current_user.username or "Faculty"
    welcome_line = f"{_greeting_for_hour(now_local.hour)}, {welcome_name}"
    today_full = now_local.strftime("%A, %d %B %Y")

    summary_line = (
        f"You have {courses_count} courses | {total_co_pending} COs pending | "
        f"{marks_deadline_phrase} | {total_level1_alerts} Level 1 alerts"
    )

    level1_alert_line = (
        f"{total_level1_alerts} Course Outcomes require remedial action"
        if total_level1_alerts > 0 else None
    )

    activity_rows: List[Dict[str, Any]] = []
    course_name_by_id = {c.id: c.course_code for c in courses}

    for c in courses:
        if c.created_at:
            activity_rows.append({
                "ts": c.created_at,
                "action": "Created course",
                "course": c.course_code,
            })

    if course_ids:
        exam_activity = await session.execute(
            select(Exam.course_id, Exam.exam_name, Exam.created_at)
            .where(Exam.course_id.in_(course_ids))
        )
        for row in exam_activity.all():
            if row[2]:
                activity_rows.append({
                    "ts": row[2],
                    "action": f"Created exam {row[1]}",
                    "course": course_name_by_id.get(row[0], "Course"),
                })

        co_activity = await session.execute(
            select(CourseOutcome.course_id, CourseOutcome.code, CourseOutcome.created_at)
            .where(CourseOutcome.course_id.in_(course_ids))
        )
        for row in co_activity.all():
            if row[2]:
                activity_rows.append({
                    "ts": row[2],
                    "action": f"Added {row[1]}",
                    "course": course_name_by_id.get(row[0], "Course"),
                })

    for n in notifications:
        created = _parse_iso_datetime(n.get("created_at"))
        if created:
            activity_rows.append({
                "ts": created,
                "action": n.get("title") or "Notification",
                "course": "System",
            })

    activity_rows.sort(key=lambda x: x["ts"], reverse=True)
    recent_activity = []
    for idx, item in enumerate(activity_rows[:10], start=1):
        ago = _format_time_ago(item["ts"], now_utc)
        recent_activity.append({
            "index": idx,
            "action": item["action"],
            "course": item["course"],
            "time_ago": ago,
            "text": f"[{item['action']}] for [{item['course']}] - {ago}",
        })

    response_payload = {
        "header": {
            "welcome_line": welcome_line,
            "today_full_date": today_full,
            "status_summary_line": summary_line,
            "ay_context_line": ay_context,
            "ay_context_color": ay_context_color,
            "ay_near_lock": near_lock,
        },
        "courses_table": {
            "columns": [
                "course_code",
                "course_name",
                "semester",
                "enrolled_students",
                "co_status",
                "marks_status",
                "action",
            ],
            "sort": {
                "by": requested_sort,
                "direction": "desc" if reverse_sort else "asc",
                "default": "urgency desc",
            },
            "search": {
                "query": search or "",
                "matches": len(course_rows),
            },
            "rows": course_rows,
        },
        "pending_actions": {
            "items": pending_actions,
            "completed_items": completed_actions,
            "show_completed": show_completed,
            "completed_hidden_count": completed_hidden_count,
            "empty_state": "No pending actions. All tasks are complete." if not pending_actions else None,
        },
        "co_attainment_summary": {
            "columns": ["course", "CO1", "CO2", "CO3", "CO4", "CO5", "overall"],
            "level_color_legend": {"L3": "green", "L2": "amber", "L1": "red_bold"},
            "level1_alert_line": level1_alert_line,
            "rows": attainment_rows,
        },
        "recent_activity": {
            "items": recent_activity,
            "view_all_link": "/faculty/activity-log",
        },
        "academic_year": active_ay,
        "my_courses": [
            {
                "id": c.id,
                "course_code": c.course_code,
                "course_name": c.course_name,
                "semester": c.semester,
            }
            for c in courses
        ],
        "co_status": co_status,
        "marks_upload_status": marks_upload_status,
        "attainment_quick_view": attainment_quick_view,
        "notification_unread": sum(1 for i in notifications if not i.get("is_read")),
        "available_years": ay_configs[:3],
        "status_summary_line": summary_line,
        "ay_context_line": ay_context,
    }

    return response_payload


@router.get("/faculty/activity-log", summary="Faculty full activity log")
async def faculty_activity_log(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    role = _role_value(current_user)
    if role != "faculty":
        raise HTTPException(status_code=403, detail="Faculty activity log is available only for faculty role")

    now_utc = datetime.utcnow()
    course_result = await session.execute(select(Course).where(Course.created_by == current_user.id))
    courses = list(course_result.scalars().all())
    course_ids = [c.id for c in courses]
    course_name_by_id = {c.id: c.course_code for c in courses}

    activities: List[Dict[str, Any]] = []
    for c in courses:
        if c.created_at:
            activities.append({"ts": c.created_at, "action": "Created course", "course": c.course_code})

    if course_ids:
        exam_activity = await session.execute(
            select(Exam.course_id, Exam.exam_name, Exam.created_at)
            .where(Exam.course_id.in_(course_ids))
        )
        for row in exam_activity.all():
            if row[2]:
                activities.append({
                    "ts": row[2],
                    "action": f"Created exam {row[1]}",
                    "course": course_name_by_id.get(row[0], "Course"),
                })

        co_activity = await session.execute(
            select(CourseOutcome.course_id, CourseOutcome.code, CourseOutcome.created_at)
            .where(CourseOutcome.course_id.in_(course_ids))
        )
        for row in co_activity.all():
            if row[2]:
                activities.append({
                    "ts": row[2],
                    "action": f"Added {row[1]}",
                    "course": course_name_by_id.get(row[0], "Course"),
                })

    notifications = await _get_notifications(str(current_user.id))
    for item in notifications:
        created = _parse_iso_datetime(item.get("created_at"))
        if created:
            activities.append({
                "ts": created,
                "action": item.get("title") or "Notification",
                "course": "System",
            })

    activities.sort(key=lambda x: x["ts"], reverse=True)
    out = []
    for idx, item in enumerate(activities[:limit], start=1):
        ago = _format_time_ago(item["ts"], now_utc)
        out.append({
            "index": idx,
            "action": item["action"],
            "course": item["course"],
            "time_ago": ago,
            "timestamp": item["ts"].isoformat(),
            "text": f"[{item['action']}] for [{item['course']}] - {ago}",
        })

    return {"count": len(out), "items": out}


# ══════════════════════════════════════════════════════════════════════════════
# COURSE LEAD DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lead/dashboard", summary="Course Lead Dashboard with approval queue and CO health")
async def course_lead_dashboard(
    department: str = Query(..., description="Department code (e.g., CSE, ECE)"),
    academic_year: str = Query(..., description="Academic year (e.g., 2024-25)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Course Lead Dashboard - L1 Main Page
    
    Features implemented:
    - L1-01: Header with department and academic year
    - L1-02: Status summary with counts
    - L1-03: Approval queue table with wait times
    - L1-04: Wait time indicators (Green/Amber/Red)
    - L1-05: Review action links
    - L1-06: CO health table with L1/L2/L3 levels
    - L1-07: Level 1 CO alert summary
    - L1-08: PO summary table with attainment
    - L1-09: PSO summary lines
    - L1-10: Recent actions list
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Course Lead Dashboard requires course_lead, hod, or admin role")
    
    # Verify user has access to this department
    if role == "course_lead" and current_user.department != department:
        raise HTTPException(status_code=403, detail="Course Lead can only access their own department")
    
    svc = CourseLeadService(session)
    dashboard_data = await svc.get_dashboard_data(department, academic_year)
    
    logger.info(f"Course Lead Dashboard accessed by {current_user.username} for {department}")
    return dashboard_data


@router.post("/lead/approve/{approval_id}", summary="Approve submission in approval queue")
async def approve_submission(
    approval_id: str,
    comments: Optional[str] = Query(None, description="Review comments"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Approve a submission from the approval queue.
    Implements real approval workflow with status updates.
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Approval requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    try:
        result = await svc.approve_submission(approval_id, str(current_user.id), comments)
        logger.info(f"Approval {approval_id} processed by {current_user.username}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/lead/co-health/{department}", summary="Detailed CO health analysis for department")
async def get_co_health_analysis(
    department: str,
    academic_year: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Detailed CO health analysis with remedial action recommendations.
    Shows Level 1 COs requiring immediate attention.
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="CO health analysis requires course_lead, hod, or admin role")
    
    # Get department courses
    courses_result = await session.execute(
        select(Course).where(Course.department == department)
    )
    courses = list(courses_result.scalars().all())
    course_ids = [c.id for c in courses]
    
    if not course_ids:
        return {"courses": [], "level1_cos": [], "remedial_recommendations": []}
    
    # Get Level 1 COs requiring remedial action
    level1_result = await session.execute(
        select(
            Course.course_code,
            Course.course_name,
            CourseOutcome.code,
            CourseOutcome.statement,
            COAttainment.attainment_percentage,
            COAttainment.calculated_at
        )
        .join(CourseOutcome, Course.id == CourseOutcome.course_id)
        .join(COAttainment, CourseOutcome.id == COAttainment.course_outcome_id)
        .where(
            and_(
                Course.id.in_(course_ids),
                COAttainment.attainment_percentage < 60
            )
        )
        .order_by(COAttainment.attainment_percentage.asc())
    )
    
    level1_cos = []
    for row in level1_result.all():
        level1_cos.append({
            "course_code": row.course_code,
            "course_name": row.course_name,
            "co_code": row.code,
            "co_statement": row.statement,
            "attainment_percentage": float(row.attainment_percentage),
            "calculated_at": row.calculated_at.isoformat(),
            "urgency": "Critical" if row.attainment_percentage < 40 else "High",
            "recommended_action": "Immediate remedial action required" if row.attainment_percentage < 40 else "Remedial action recommended"
        })
    
    return {
        "department": department,
        "academic_year": academic_year,
        "total_courses": len(courses),
        "level1_cos": level1_cos,
        "level1_count": len(level1_cos),
        "critical_count": len([co for co in level1_cos if co["urgency"] == "Critical"])
    }


@router.get("/lead/po-targets/{department}", summary="PO target tracking and status")
async def get_po_targets(
    department: str,
    academic_year: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get PO target tracking with current vs target percentages.
    Shows which POs are meeting targets and which need attention.
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="PO targets requires course_lead, hod, or admin role")
    
    # Get department courses
    courses_result = await session.execute(
        select(Course.id).where(Course.department == department)
    )
    course_ids = [row[0] for row in courses_result.all()]
    
    if not course_ids:
        return {"po_targets": [], "summary": {"total": 0, "met": 0, "not_met": 0}}
    
    # Get PO attainments for department
    po_result = await session.execute(
        select(
            ProgramOutcome.code,
            ProgramOutcome.statement,
            func.avg(POAttainment.attainment_percentage).label('current_percentage'),
            func.count(POAttainment.id).label('course_count')
        )
        .join(POAttainment, ProgramOutcome.id == POAttainment.program_outcome_id)
        .where(POAttainment.course_id.in_(course_ids))
        .group_by(ProgramOutcome.id, ProgramOutcome.code, ProgramOutcome.statement)
        .order_by(ProgramOutcome.code)
    )
    
    po_targets = []
    met_count = 0
    target_percentage = 70.0  # Standard target
    
    for row in po_result.all():
        current_pct = float(row.current_percentage or 0)
        is_met = current_pct >= target_percentage
        if is_met:
            met_count += 1
        
        po_targets.append({
            "code": row.code,
            "statement": row.statement,
            "current_percentage": round(current_pct, 1),
            "target_percentage": target_percentage,
            "gap": round(target_percentage - current_pct, 1),
            "status": "Met" if is_met else "Not Met",
            "level": "Level 3" if current_pct >= 70 else "Level 2" if current_pct >= 60 else "Level 1",
            "course_count": row.course_count,
            "color": "green" if is_met else "red"
        })
    
    return {
        "department": department,
        "academic_year": academic_year,
        "po_targets": po_targets,
        "summary": {
            "total": len(po_targets),
            "met": met_count,
            "not_met": len(po_targets) - met_count,
            "percentage_met": round((met_count / len(po_targets)) * 100, 1) if po_targets else 0
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# L2 - MARKS APPROVAL PAGE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lead/marks-approval/{submission_id}", summary="L2 - Marks approval page with anomaly detection")
async def get_marks_approval_page(
    submission_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L2 - Marks Approval Page
    Features: L2-01 through L2-12
    - Submission header, read-only marks table, anomaly detection
    - CO preview, previous exam comparison, approval workflow
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Marks approval requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    approval_data = await svc.get_marks_approval_data(submission_id, str(current_user.id))
    
    logger.info(f"Marks approval page accessed for {submission_id} by {current_user.username}")
    return approval_data


@router.post("/lead/marks-approval/{submission_id}/approve", summary="L2-08 - Approve marks submission")
async def approve_marks_submission(
    submission_id: str,
    comments: Optional[str] = Query(None, description="L2-07 - Lead comments"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L2-08: Approve button with confirmation
    Triggers CO attainment calculation
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Marks approval requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    result = await svc.approve_marks_submission(submission_id, str(current_user.id), comments)
    
    logger.info(f"Marks approved for {submission_id} by {current_user.username}")
    return result


@router.post("/lead/marks-approval/{submission_id}/return", summary="L2-09 - Return marks submission")
async def return_marks_submission(
    submission_id: str,
    reason: str = Query(..., description="L2-09 - Required reason for return"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L2-09: Return button with required reason
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Marks approval requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    result = await svc.return_marks_submission(submission_id, str(current_user.id), reason)
    
    logger.info(f"Marks returned for {submission_id} by {current_user.username}")
    return result


@router.post("/lead/marks-approval/{submission_id}/override", summary="L2-10/L2-11 - HOD override mode")
async def override_marks_submission(
    submission_id: str,
    marks_data: Dict[str, Any],
    override_reason: str = Query(..., description="L2-11 - Required override reason"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L2-10: HOD-authorized edit mode
    L2-11: Override reason field (required)
    All changes logged in audit trail
    """
    role = _role_value(current_user)
    if role not in {"hod", "admin"}:
        raise HTTPException(status_code=403, detail="Override mode requires HOD or admin role")
    
    svc = CourseLeadService(session)
    result = await svc.override_marks_submission(submission_id, str(current_user.id), marks_data, override_reason)
    
    logger.info(f"Marks overridden for {submission_id} by {current_user.username}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# L3 - CO ATTAINMENT PAGE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lead/co-attainment", summary="L3 - CO Attainment for all assigned courses")
async def get_co_attainment_page(
    department: str = Query(...),
    academic_year: str = Query(...),
    course_filter: Optional[str] = Query(None, description="L3-01 - Course dropdown filter"),
    semester_filter: Optional[int] = Query(None, description="L3-01 - Semester filter"),
    status_filter: str = Query("all", description="L3-01 - Status filter: all|level1|pending"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L3 - CO Attainment Page
    Features: L3-01 through L3-10
    - Filter bar, expandable course list, CO sub-tables
    - Override controls, comparison mode, export functionality
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="CO attainment requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    attainment_data = await svc.get_co_attainment_data(
        department, academic_year, course_filter, semester_filter, status_filter
    )
    
    logger.info(f"CO attainment page accessed for {department} by {current_user.username}")
    return attainment_data


@router.post("/lead/co-attainment/override", summary="L3-05 - Override CO attainment")
async def override_co_attainment(
    co_id: str,
    new_level: str,
    justification: str = Query(..., description="L3-05 - Override justification"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L3-05: Override control with inline justification
    Saves override and notifies HOD
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="CO override requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    result = await svc.override_co_attainment(co_id, new_level, justification, str(current_user.id))
    
    logger.info(f"CO attainment overridden for {co_id} by {current_user.username}")
    return result


@router.get("/lead/co-attainment/compare", summary="L3-08 - Side comparison mode")
async def compare_courses_co_attainment(
    course1_id: str = Query(..., description="L3-08 - First course for comparison"),
    course2_id: str = Query(..., description="L3-08 - Second course for comparison"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L3-08: Side comparison mode
    Split view with two course dropdowns and CO tables side by side
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="CO comparison requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    comparison_data = await svc.compare_courses_co_attainment(course1_id, course2_id)
    
    logger.info(f"CO comparison accessed for {course1_id} vs {course2_id} by {current_user.username}")
    return comparison_data


@router.get("/lead/co-attainment/export", summary="L3-10 - Export all courses to Excel")
async def export_co_attainment(
    department: str = Query(...),
    academic_year: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L3-10: Export all courses to Excel
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="CO export requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    excel_content = await svc.export_co_attainment_excel(department, academic_year)
    
    filename = f"CO_Attainment_{department}_{academic_year}.xlsx"
    return Response(
        content=excel_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# L4 - PO & PSO ATTAINMENT PAGE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lead/po-attainment", summary="L4 - PO & PSO Attainment with gap analysis")
async def get_po_pso_attainment_page(
    department: str = Query(...),
    academic_year: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L4 - PO & PSO Attainment Page
    Features: L4-01 through L4-07
    - PO table with gap analysis, expandable CO contributions
    - PO bar chart, PSO section, formula reference, export options
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="PO attainment requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    po_pso_data = await svc.get_po_pso_attainment_data(department, academic_year)
    
    logger.info(f"PO/PSO attainment page accessed for {department} by {current_user.username}")
    return po_pso_data


@router.get("/lead/po-attainment/export", summary="L4-07 - Export PO tables (PDF/Excel/NBA)")
async def export_po_attainment(
    department: str = Query(...),
    academic_year: str = Query(...),
    format: str = Query("pdf", description="L4-07 - pdf|excel|nba"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L4-07: Export buttons - PDF, Excel, NBA format
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="PO export requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    
    if format.lower() == "pdf":
        content = await svc.export_po_attainment_pdf(department, academic_year)
        media_type = "application/pdf"
        filename = f"PO_Attainment_{department}_{academic_year}.pdf"
    elif format.lower() == "excel":
        content = await svc.export_po_attainment_excel(department, academic_year)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"PO_Attainment_{department}_{academic_year}.xlsx"
    elif format.lower() == "nba":
        content = await svc.export_po_attainment_nba(department, academic_year)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"NBA_PO_Attainment_{department}_{academic_year}.xlsx"
    else:
        raise HTTPException(status_code=400, detail="Format must be pdf, excel, or nba")
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# L5 - ACADEMIC YEAR COMPARISON PAGE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lead/ay-comparison", summary="L5 - Academic Year Comparison with trend analysis")
async def get_ay_comparison_page(
    course_id: str = Query(..., description="L5-01 - Course selector"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L5 - Academic Year Comparison Page
    Features: L5-01 through L5-06
    - Course selector, comparison table, trend analysis
    - Persistent low highlights, trend chart, export functionality
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="AY comparison requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    comparison_data = await svc.get_ay_comparison_data(course_id)
    
    logger.info(f"AY comparison page accessed for {course_id} by {current_user.username}")
    return comparison_data


@router.get("/lead/ay-comparison/export", summary="L5-06 - Export comparison table to Excel")
async def export_ay_comparison(
    course_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L5-06: Export comparison table to Excel
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="AY comparison export requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    excel_content = await svc.export_ay_comparison_excel(course_id)
    
    # Get course code for filename
    course_result = await session.execute(select(Course.course_code).where(Course.id == course_id))
    course_code = course_result.scalar() or "Course"
    
    filename = f"AY_Comparison_{course_code}.xlsx"
    return Response(
        content=excel_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# L6 - LEAD REPORTS PAGE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/lead/reports", summary="L6 - Lead Reports with NBA format support")
async def get_lead_reports_page(
    department: str = Query(...),
    academic_year: str = Query(...),
    report_type: str = Query("co_attainment", description="L6-01 - Report type selector"),
    course_filter: Optional[str] = Query(None, description="L6-02 - Course filter"),
    exam_filter: Optional[str] = Query(None, description="L6-02 - Exam filter"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L6 - Lead Reports Page
    Features: L6-01 through L6-06
    - Report type selector, filter controls, generate & preview
    - Download options, NBA export, report history
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Lead reports requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    reports_data = await svc.get_lead_reports_data(
        department, academic_year, report_type, course_filter, exam_filter
    )
    
    logger.info(f"Lead reports page accessed for {department} by {current_user.username}")
    return reports_data


@router.post("/lead/reports/generate", summary="L6-03 - Generate & preview report")
async def generate_lead_report(
    department: str = Query(...),
    academic_year: str = Query(...),
    report_type: str = Query(..., description="L6-01 - co_attainment|po_attainment|student_performance|nba"),
    course_filter: Optional[str] = Query(None),
    exam_filter: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L6-03: Generate & preview - Inline PDF preview after generation
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Report generation requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    report_result = await svc.generate_lead_report(
        department, academic_year, report_type, course_filter, exam_filter, str(current_user.id)
    )
    
    logger.info(f"Lead report generated: {report_type} for {department} by {current_user.username}")
    return report_result


@router.get("/lead/reports/download", summary="L6-04/L6-05 - Download PDF/Excel/NBA buttons")
async def download_lead_report(
    report_id: str = Query(...),
    format: str = Query("pdf", description="L6-04/L6-05 - pdf|excel|nba"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L6-04: Download PDF / Excel buttons
    L6-05: NBA export button
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Report download requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    content, media_type, filename = await svc.download_lead_report(report_id, format)
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/lead/reports/history", summary="L6-06 - Report history list")
async def get_lead_reports_history(
    department: str = Query(...),
    limit: int = Query(10, description="L6-06 - Last 10 generated reports"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    L6-06: Report history list
    Table of last 10 generated reports with date and download link
    """
    role = _role_value(current_user)
    if role not in {"course_lead", "hod", "admin"}:
        raise HTTPException(status_code=403, detail="Report history requires course_lead, hod, or admin role")
    
    svc = CourseLeadService(session)
    history_data = await svc.get_lead_reports_history(department, limit)
    
    return history_data


# ══════════════════════════════════════════════════════════════════════════════
# FACULTY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/courses", response_model=CourseResponse, summary="Create a course")
async def create_course(
    payload: CourseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.exc import IntegrityError as SAIntegrityError

    role = _role_value(current_user)
    if role not in {"admin", "faculty", "course_lead", "subject_lead"}:
        raise HTTPException(status_code=403, detail="Only faculty/admin roles can create courses")

    svc = CourseService(session)
    try:
        course = await svc.create_course(
            course_code=payload.course_code, course_name=payload.course_name,
            credits=payload.credits, semester=payload.semester,
            description=payload.description, faculty_id=current_user.id,
            course_type=payload.course_type,
            enrolled_students=payload.enrolled_students,
            fa_method=payload.fa_method,
            fa_best_n=payload.fa_best_n,
            fa_total_components=payload.fa_total_components,
            fa_weight=payload.fa_weight,
            sa_weight=payload.sa_weight,
            department=payload.department or getattr(current_user, 'department', None),
        )
        logger.info(f"Course created: {course.id}")
        return course
    except SAIntegrityError as e:
        await session.rollback()
        if 'course_code' in str(e) or 'UNIQUE' in str(e).upper():
            raise HTTPException(status_code=409, detail=f"A course with code '{payload.course_code}' already exists.")
        raise HTTPException(status_code=409, detail="A course with these details already exists.")
    except Exception as e:
        await session.rollback()
        logger.error(f"Course creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create course: {str(e)}")


@router.get("/courses", response_model=List[CourseResponse], summary="List all courses")
async def list_courses(
    semester: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    svc = CourseService(session)
    courses = await svc.list_courses(semester=semester)
    if _role_value(current_user) == "faculty":
        return [c for c in courses if str(getattr(c, "created_by", "")) == str(current_user.id)]
    return courses


@router.get("/courses/{course_id}", response_model=CourseResponse, summary="Get a course")
async def get_course(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Course).where((Course.id == course_id) | (Course.course_code == course_id))
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if _role_value(current_user) == "faculty" and str(getattr(course, "created_by", "")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Faculty can access only own courses")
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse, summary="Update a course")
async def update_course(
    course_id: str,
    payload: CourseUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    updates = payload.model_dump(exclude_unset=True)
    if "created_by" in updates and _role_value(current_user) != "admin":
        del updates["created_by"]
    for key, value in updates.items():
        setattr(course, key, value)

    await session.commit()
    await session.refresh(course)
    return course


@router.delete("/courses/{course_id}", summary="Delete a course and related data")
async def delete_course(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await session.delete(course)
    await session.commit()
    return {"status": "deleted", "course_id": course_id}


@router.post("/courses/{course_id}/syllabus", summary="Update course syllabus")
async def update_syllabus(
    course_id: str,
    payload: SyllabusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.syllabus = payload.syllabus
    await session.commit()
    return {"course_id": course_id, "syllabus_length": len(payload.syllabus), "status": "updated"}


# ══════════════════════════════════════════════════════════════════════════════
# COURSE OUTCOMES
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/courses/{course_id}/outcomes", response_model=COResponse, summary="Manually add a CO")
async def add_course_outcome(
    course_id: str,
    payload: COCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")

    svc = CoGenerationService(session)
    co = await svc.create_course_outcome(
        course_id=course_id, co_code=payload.co_code,
        co_statement=payload.co_statement, bloom_level=payload.bloom_level,
        description=payload.description,
    )
    logger.info(f"CO created: {co.id}")
    return co


@router.get("/courses/{course_id}/outcomes", summary="List all COs for a course")
async def list_course_outcomes(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id)
        .order_by(CourseOutcome.code)
    )
    cos = result.scalars().all()
    return [
        {
            "id": co.id,
            "course_id": co.course_id,
            "code": co.code,
            "statement": co.statement,
            "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
            "description": co.description,
        }
        for co in cos
    ]


@router.put("/courses/{course_id}/outcomes/{co_id}", summary="Update a course outcome")
async def update_course_outcome(
    course_id: str,
    co_id: str,
    payload: OutcomeUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")

    result = await session.execute(
        select(CourseOutcome).where(
            CourseOutcome.id == co_id,
            CourseOutcome.course_id == course_id,
        )
    )
    co = result.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="Course outcome not found")

    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates:
        co.code = updates["code"]
    if "statement" in updates:
        co.statement = updates["statement"]
    if "bloom_level" in updates:
        co.bloom_level = updates["bloom_level"]
    if "description" in updates:
        co.description = updates["description"]

    await session.commit()
    await invalidate_course_report_cache(course_id)
    return {
        "id": co.id,
        "course_id": co.course_id,
        "code": co.code,
        "statement": co.statement,
        "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
        "description": co.description,
    }


@router.delete("/courses/{course_id}/outcomes/{co_id}", summary="Delete a course outcome")
async def delete_course_outcome(
    course_id: str,
    co_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")

    result = await session.execute(
        select(CourseOutcome).where(
            CourseOutcome.id == co_id,
            CourseOutcome.course_id == course_id,
        )
    )
    co = result.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="Course outcome not found")

    await session.delete(co)
    await session.commit()
    await invalidate_course_report_cache(course_id)
    return {"status": "deleted", "co_id": co_id, "course_id": course_id}


# ── F3-08: Syllabus file upload ────────────────────────────────────────────────

@router.post("/courses/{course_id}/syllabus/upload", summary="Upload syllabus file (PDF/DOCX/TXT) and extract text")
async def upload_syllabus_file(
    course_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Accept .pdf, .docx, or .txt syllabus files; extract text and save to Course.syllabus."""
    await _assert_faculty_owns_course(session, current_user, course_id)
    
    # Fetch the course
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    filename = (file.filename or "").lower()
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    # Extract text based on file type
    if filename.endswith(".txt"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")
    elif filename.endswith(".pdf"):
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            logger.error(f"PDF extraction failed: {exc}")
            raise HTTPException(status_code=422, detail=f"PDF text extraction failed: {exc}")
    elif filename.endswith(".docx"):
        try:
            import io
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error(f"DOCX extraction failed: {exc}")
            raise HTTPException(status_code=422, detail=f"DOCX text extraction failed: {exc}")
    else:
        raise HTTPException(status_code=415, detail="Unsupported file type. Accepted: .pdf, .docx, .txt")

    # Truncate and save
    text = text[:5000] if text else ""
    course.syllabus = text
    
    # Explicitly flush and commit to ensure data persists
    await session.flush()
    await session.commit()
    
    logger.info(f"Syllabus uploaded for course {course_id}: {len(text)} chars")
    
    return {
        "course_id": course_id,
        "filename": file.filename,
        "syllabus_length": len(text),
        "status": "updated",
    }


# ── F3-17 enhanced: CO list with PO/PSO mappings, BT verbs, status ────────────

_BT_LEVEL_LABEL: Dict[str, str] = {
    "remember":   "L1 — Remember",
    "understand": "L2 — Understand",
    "apply":      "L3 — Apply",
    "analyze":    "L4 — Analyze",
    "evaluate":   "L5 — Evaluate",
    "create":     "L6 — Create",
}
_BT_PRIMARY_VERB: Dict[str, str] = {
    "remember":   "Recall",
    "understand": "Explain",
    "apply":      "Apply",
    "analyze":    "Analyse",
    "evaluate":   "Evaluate",
    "create":     "Design",
}
_BT_ALL_VERBS: Dict[str, List[str]] = {
    "remember":   ["Define", "List", "Recall", "Name", "State", "Identify", "Memorise"],
    "understand": ["Explain", "Describe", "Summarise", "Interpret", "Classify", "Compare"],
    "apply":      ["Apply", "Use", "Implement", "Solve", "Demonstrate", "Execute", "Calculate"],
    "analyze":    ["Analyse", "Compare", "Differentiate", "Examine", "Break down", "Deconstruct"],
    "evaluate":   ["Evaluate", "Justify", "Critique", "Assess", "Judge", "Appraise"],
    "create":     ["Design", "Develop", "Construct", "Formulate", "Compose", "Build"],
}


def _bloom_raw(co_bloom_level) -> str:
    return str(co_bloom_level.value if hasattr(co_bloom_level, "value") else co_bloom_level).lower()


@router.get("/courses/{course_id}/outcomes/detail", summary="List COs with PO/PSO mappings, BT verbs and status (F3-17 to F3-23)")
async def list_course_outcomes_detail(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    co_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
    )
    cos = co_result.scalars().all()
    if not cos:
        return []

    co_ids = [co.id for co in cos]

    # Load PO mappings
    po_rows = (await session.execute(
        select(
            co_po_mapping_table.c.course_outcome_id,
            ProgramOutcome.code,
            co_po_mapping_table.c.similarity_score,
        )
        .join(ProgramOutcome, co_po_mapping_table.c.program_outcome_id == ProgramOutcome.id)
        .where(co_po_mapping_table.c.course_outcome_id.in_(co_ids))
    )).fetchall()

    # Load PSO mappings
    pso_rows = (await session.execute(
        select(
            co_pso_mapping_table.c.course_outcome_id,
            ProgramSpecificOutcome.code,
            co_pso_mapping_table.c.similarity_score,
        )
        .join(ProgramSpecificOutcome, co_pso_mapping_table.c.program_specific_outcome_id == ProgramSpecificOutcome.id)
        .where(co_pso_mapping_table.c.course_outcome_id.in_(co_ids))
    )).fetchall()

    po_by_co: Dict[str, List[Dict]] = {}
    for r in po_rows:
        po_by_co.setdefault(r[0], []).append({"code": r[1], "level": round(r[2] * 3) if r[2] else 0})

    pso_by_co: Dict[str, List[Dict]] = {}
    for r in pso_rows:
        pso_by_co.setdefault(r[0], []).append({"code": r[1], "level": round(r[2] * 3) if r[2] else 0})

    out = []
    for co in cos:
        bl = _bloom_raw(co.bloom_level)
        out.append({
            "id": co.id,
            "course_id": co.course_id,
            "code": co.code,
            "statement": co.statement,
            "bloom_level": bl,
            "bloom_label": _BT_LEVEL_LABEL.get(bl, bl.capitalize()),
            "bt_verb": _BT_PRIMARY_VERB.get(bl, ""),
            "bt_all_verbs": _BT_ALL_VERBS.get(bl, []),
            "po_mappings": po_by_co.get(co.id, []),
            "pso_mappings": pso_by_co.get(co.id, []),
            "status": "Saved" if co.is_active else "Inactive",
            "description": co.description,
        })
    return out


# ── F3-21/22: Update CO PO/PSO mappings inline ────────────────────────────────

@router.put("/courses/{course_id}/outcomes/{co_id}/mappings", summary="Update PO and PSO code mappings for a CO (F3-21, F3-22)")
async def update_co_mappings(
    course_id: str,
    co_id: str,
    payload: COMappingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)

    co_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.id == co_id, CourseOutcome.course_id == course_id)
    )
    co = co_result.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="Course outcome not found")

    # Delete existing mappings for this CO
    await session.execute(
        co_po_mapping_table.delete().where(co_po_mapping_table.c.course_outcome_id == co_id)
    )
    await session.execute(
        co_pso_mapping_table.delete().where(co_pso_mapping_table.c.course_outcome_id == co_id)
    )

    po_inserted = []
    pso_inserted = []

    # Re-insert PO mappings by code lookup (deduplicated — one mapping per code)
    if payload.po_codes:
        # Resolve program key: explicit > dept key; auto-seed NBA POs if needed
        _co_course_result = await session.execute(select(Course).where(Course.id == course_id))
        _co_course = _co_course_result.scalar_one_or_none()
        _dept_key = _dept_program_key(getattr(_co_course, "department", None)) if _co_course else "DEPT:GENERAL"
        _resolved_prog = payload.program_id or _dept_key
        await _ensure_nba_pos_seeded(session, _resolved_prog)
        po_filter = (ProgramOutcome.code.in_(payload.po_codes)) & (ProgramOutcome.program == _resolved_prog)
        po_objs = (await session.execute(select(ProgramOutcome).where(po_filter))).scalars().all()
        if not po_objs:
            # fallback: any program
            po_objs = (await session.execute(select(ProgramOutcome).where(ProgramOutcome.code.in_(payload.po_codes)))).scalars().all()
        seen_po: set = set()
        for po_obj in po_objs:
            if po_obj.code in seen_po:
                continue
            seen_po.add(po_obj.code)
            await session.execute(
                co_po_mapping_table.insert().values(
                    course_outcome_id=co_id,
                    program_outcome_id=po_obj.id,
                    similarity_score=round(max(1, min(3, payload.po_levels.get(po_obj.code, 1))) / 3.0, 6),
                )
            )
            po_inserted.append(po_obj.code)

    # Re-insert PSO mappings by code lookup (deduplicated — one mapping per code)
    if payload.pso_codes:
        pso_filter = ProgramSpecificOutcome.code.in_(payload.pso_codes)
        if payload.program_id:
            pso_filter = (ProgramSpecificOutcome.code.in_(payload.pso_codes)) & (ProgramSpecificOutcome.program == payload.program_id)
        pso_objs = (await session.execute(select(ProgramSpecificOutcome).where(pso_filter))).scalars().all()
        seen_pso: set = set()
        for pso_obj in pso_objs:
            if pso_obj.code in seen_pso:
                continue
            seen_pso.add(pso_obj.code)
            await session.execute(
                co_pso_mapping_table.insert().values(
                    course_outcome_id=co_id,
                    program_specific_outcome_id=pso_obj.id,
                    similarity_score=round(max(1, min(3, payload.pso_levels.get(pso_obj.code, 1))) / 3.0, 6),
                )
            )
            pso_inserted.append(pso_obj.code)

    await session.commit()
    await invalidate_course_report_cache(course_id)

    validation = await validate_course_matrix_before_save(session, course_id)
    return {
        "co_id": co_id,
        "po_mappings": po_inserted,
        "pso_mappings": pso_inserted,
        "status": "updated",
        "warnings": validation.get("warnings", []),
        "validation_errors": validation.get("errors", []),
        "can_save": validation.get("can_save", True),
        "matrix_density": validation.get("matrix_density"),
    }


# ── F3-19/20: BT level & verb reference ───────────────────────────────────────

@router.get("/outcomes/bt-verbs", summary="Bloom's Taxonomy verbs and examples for each level (F3-19, F3-20)")
async def get_bt_verbs(
    level: Optional[str] = Query(None, description="Filter by level: remember|understand|apply|analyze|evaluate|create or L1-L6"),
    current_user: User = Depends(get_current_user),
):
    _ALIAS: Dict[str, str] = {"l1": "remember", "l2": "understand", "l3": "apply", "l4": "analyze", "l5": "evaluate", "l6": "create"}
    levels = {
        "remember":   {"label": "L1 — Remember",   "primary_verb": "Recall",    "verbs": _BT_ALL_VERBS["remember"],   "example": "Recall the definition of CO attainment."},
        "understand": {"label": "L2 — Understand",  "primary_verb": "Explain",   "verbs": _BT_ALL_VERBS["understand"], "example": "Explain how Bloom's Taxonomy is structured."},
        "apply":      {"label": "L3 — Apply",       "primary_verb": "Apply",     "verbs": _BT_ALL_VERBS["apply"],      "example": "Apply OBE principles to design course outcomes."},
        "analyze":    {"label": "L4 — Analyze",     "primary_verb": "Analyse",   "verbs": _BT_ALL_VERBS["analyze"],    "example": "Analyse student performance data to identify gaps."},
        "evaluate":   {"label": "L5 — Evaluate",    "primary_verb": "Evaluate",  "verbs": _BT_ALL_VERBS["evaluate"],   "example": "Evaluate the effectiveness of teaching methods."},
        "create":     {"label": "L6 — Create",      "primary_verb": "Design",    "verbs": _BT_ALL_VERBS["create"],     "example": "Design a comprehensive OBE curriculum framework."},
    }
    if level:
        key = _ALIAS.get(level.lower(), level.lower())
        if key not in levels:
            raise HTTPException(status_code=400, detail=f"Unknown level '{level}'. Use: remember|understand|apply|analyze|evaluate|create or L1-L6")
        return {key: levels[key]}
    return levels


# ── F3-27: Bloom distribution of COs ──────────────────────────────────────────

@router.get("/courses/{course_id}/outcomes/bloom-distribution", summary="BT level distribution of all COs (F3-27)")
async def co_bloom_distribution(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id)
    )
    cos = result.scalars().all()

    dist: Dict[str, int] = {k: 0 for k in ("remember", "understand", "apply", "analyze", "evaluate", "create")}
    for co in cos:
        bl = _bloom_raw(co.bloom_level)
        if bl in dist:
            dist[bl] += 1

    label_dist = {_BT_LEVEL_LABEL.get(k, k): v for k, v in dist.items()}
    low_order = dist["remember"] + dist["understand"]
    total = len(cos)
    warning = None
    if total > 0 and low_order == total:
        warning = "All COs are at L1-L2 (lower-order thinking). Consider adding higher-order COs (L3-L6)."
    elif total > 0 and low_order / total > 0.6:
        warning = "Most COs are at L1-L2. A balanced distribution across L1-L6 is recommended."

    return {
        "course_id": course_id,
        "total_cos": total,
        "distribution": label_dist,
        "raw_distribution": dist,
        "warning": warning,
    }


# ── F3-15: Single CO regeneration ─────────────────────────────────────────────

@router.post("/courses/{course_id}/outcomes/{co_id}/regenerate", summary="Regenerate a single CO via AI, others untouched (F3-15)")
async def regenerate_single_course_outcome(
    course_id: str,
    co_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")

    svc = CoGenerationService(session)
    try:
        updated_co = await svc.regenerate_single_co(course_id=course_id, co_id=co_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await invalidate_course_report_cache(course_id)
    bl = _bloom_raw(updated_co.bloom_level)
    return {
        "id": updated_co.id,
        "course_id": updated_co.course_id,
        "code": updated_co.code,
        "statement": updated_co.statement,
        "bloom_level": bl,
        "bloom_label": _BT_LEVEL_LABEL.get(bl, bl.capitalize()),
        "status": "AI Generated",
    }


# ── F3-26: CO coverage analysis ───────────────────────────────────────────────

@router.get("/courses/{course_id}/co-coverage", summary="Analyse which syllabus topics are covered by at least one CO (F3-26)")
async def co_coverage_analysis(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)

    course_result = await session.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    syllabus = (course.syllabus or "").strip()
    if not syllabus:
        return {"course_id": course_id, "has_syllabus": False, "units": [], "coverage_pct": 0}

    co_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id)
    )
    cos = list(co_result.scalars().all())

    svc = CoGenerationService(session)
    units = svc._parse_syllabus_units(syllabus)
    coverage_result = svc._validate_unit_coverage(units, cos)

    coverage_items = [
        {
            "unit": item.get("unit", ""),
            "is_covered": bool(item.get("covered")),
            "covered_by": item.get("covered_by", []),
            "color": "green" if item.get("covered") else "amber",
        }
        for item in coverage_result.get("unit_details", [])
    ]

    total = int(coverage_result.get("total_units", len(coverage_items)) or 0)
    covered_count = int(coverage_result.get("covered_count", 0) or 0)
    uncovered_count = int(coverage_result.get("uncovered_count", max(total - covered_count, 0)) or 0)
    return {
        "course_id": course_id,
        "has_syllabus": True,
        "total_units": total,
        "covered_units": covered_count,
        "covered_count": covered_count,
        "uncovered_units": uncovered_count,
        "uncovered_count": uncovered_count,
        "coverage_pct": round(float(coverage_result.get("coverage_pct", (covered_count / total * 100) if total else 0)), 1),
        "covered_unit_names": coverage_result.get("covered_units", []),
        "uncovered_unit_names": coverage_result.get("uncovered_units", []),
        "unit_details": coverage_result.get("unit_details", []),
        "units": coverage_items,
    }


# ── F3-29: Export CO list (PDF / CSV) ─────────────────────────────────────────

# ── Inline CO statement edit (F3-11/12) ──────────────────────────────────────

class COStatementUpdateRequest(BaseModel):
    statement: str
    bloom_level: Optional[str] = None


@router.put("/courses/{course_id}/outcomes/{co_id}/statement", summary="Inline edit CO statement with NBA quality validation")
async def update_co_statement(
    course_id: str,
    co_id: str,
    payload: COStatementUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")
    svc = CoGenerationService(session)
    try:
        result = await svc.update_co_statement(
            course_id=course_id,
            co_id=co_id,
            new_statement=payload.statement,
            new_bloom_level=payload.bloom_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await invalidate_course_report_cache(course_id)
    return result


# ── CO generation history (F3-15 history) ─────────────────────────────────────

@router.get("/courses/{course_id}/co-history", summary="Get CO version history snapshots from Redis")
async def get_co_history(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = CoGenerationService(session)
    versions = await svc.get_co_history(course_id)
    return {"course_id": course_id, "versions": versions, "count": len(versions)}


# ── CO generation session memory (F3-14) ──────────────────────────────────────

@router.get("/courses/{course_id}/co-session", summary="Get last CO generation session context from Redis")
async def get_co_session(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = CoGenerationService(session)
    sess = await svc.get_co_session(course_id)
    return sess or {"course_id": course_id, "last_generated_at": None}


# ── Per-CO item history + rollback (Part 2 Step 9) ────────────────────────────

@router.get(
    "/courses/{course_id}/outcomes/{co_id}/history",
    summary="Get per-CO version history (latest first)",
)
async def get_co_item_history(
    course_id: str,
    co_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    co_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.id == co_id, CourseOutcome.course_id == course_id)
    )
    co = co_result.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="CO not found")
    svc = CoGenerationService(session)
    versions = await svc.get_co_item_history(course_id=course_id, co_code=co.code)
    return {"course_id": course_id, "co_id": co_id, "co_code": co.code, "versions": versions, "count": len(versions)}


class CORollbackRequest(BaseModel):
    version_index: int = 0


@router.post(
    "/courses/{course_id}/outcomes/{co_id}/rollback",
    summary="Rollback a CO to a previous version index",
)
async def rollback_course_outcome(
    course_id: str,
    co_id: str,
    payload: CORollbackRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")
    svc = CoGenerationService(session)
    try:
        co = await svc.rollback_co_to_version(course_id=course_id, co_id=co_id, version_index=int(payload.version_index))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await invalidate_course_report_cache(course_id)
    return {
        "id": co.id,
        "course_id": co.course_id,
        "code": co.code,
        "statement": co.statement,
        "bloom_level": _bloom_raw(co.bloom_level),
        "status": "Rolled Back",
    }


# ── NBA SAR export (F3-16) ────────────────────────────────────────────────────

@router.get("/courses/{course_id}/outcomes/export/nba-sar", summary="Export NBA SAR table as CSV (CO No, Statement, BT Level, PO levels, Attainment)")
async def export_nba_sar(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    course_result = await session.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    svc = CoGenerationService(session)
    csv_bytes = await svc.export_nba_sar(course_id)
    filename = f"NBA_SAR_{course.course_code}_{course.course_name[:20].replace(' ', '_')}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/courses/{course_id}/outcomes/export", summary="Export CO list as PDF or CSV draft (F3-29)")
async def export_course_outcomes(
    course_id: str,
    format: str = Query("pdf", description="pdf or csv"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)

    course_result = await session.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    co_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
    )
    cos = co_result.scalars().all()

    if format.lower() == "csv":
        import io, csv
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["CO No", "Statement", "Bloom Level", "Description"])
        for co in cos:
            bl = _bloom_raw(co.bloom_level)
            writer.writerow([co.code, co.statement, _BT_LEVEL_LABEL.get(bl, bl), co.description or ""])
        csv_bytes = buf.getvalue().encode("utf-8")
        filename = f"CO_List_{course.course_code}.csv"
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # PDF via reportlab
    try:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle("Title", parent=styles["Heading1"], spaceAfter=6, fontSize=14)
        story.append(Paragraph(f"Course Outcomes — {course.course_name} ({course.course_code})", title_style))
        story.append(Paragraph(f"Semester {course.semester or '—'}  |  Generated: {datetime.utcnow().strftime('%d %b %Y')}", styles["Normal"]))
        story.append(Spacer(1, 0.4*cm))

        if not cos:
            story.append(Paragraph("No Course Outcomes defined yet.", styles["Normal"]))
        else:
            table_data = [["CO No", "Statement", "BT Level"]]
            for co in cos:
                bl = _bloom_raw(co.bloom_level)
                table_data.append([
                    Paragraph(co.code, styles["Normal"]),
                    Paragraph(co.statement, styles["Normal"]),
                    Paragraph(_BT_LEVEL_LABEL.get(bl, bl), styles["Normal"]),
                ])
            col_widths = [2*cm, 12*cm, 3.5*cm]
            tbl = Table(table_data, colWidths=col_widths)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, 0), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
                ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING",  (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(tbl)
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("DRAFT — For review only. Save to system to make COs official.", styles["Italic"]))
        doc.build(story)
        pdf_bytes = buf.getvalue()
        filename = f"CO_List_{course.course_code}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")


@router.post("/courses/{course_id}/generate-co", summary="AI-generate COs from syllabus with PO/PSO alignment")
async def generate_course_outcomes(
    course_id: str,
    payload: COGenerateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    """
    Generates 4-6 COs from the syllabus using Gemini AI.
    Each CO follows Bloom's Taxonomy progression.
    Optionally maps COs to provided POs and PSOs (strength 1/2/3).
    """
    lock = await _get_co_lock(course_id)
    if _co_lock_blocks_for_user(lock, current_user):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")

    try:
        svc = CoGenerationService(session)
        result = await svc.generate_cos_from_syllabus(
            course_id=course_id,
            syllabus=payload.syllabus,
            program_outcomes=[po.model_dump() for po in payload.program_outcomes],
            program_specific_outcomes=[pso.model_dump() for pso in payload.program_specific_outcomes],
            num_cos=payload.num_cos,
        )
        cos_out = [
            {
                "id": co.id,
                "code": co.code,
                "statement": co.statement,
                "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
            }
            for co in result["course_outcomes"]
        ]
        logger.info(f"Generated {len(cos_out)} COs for course {course_id}")
        await _set_co_lock(course_id=course_id, locked=True, by=str(current_user.id), reason="COs saved from AI generation")
        await invalidate_course_report_cache(course_id)

        # Run matrix validation immediately after generation (non-fatal)
        try:
            validation = await validate_course_matrix_before_save(session, course_id)
        except Exception as val_exc:
            logger.warning(f"Matrix validation skipped after CO generation: {val_exc}")
            validation = {"can_save": True, "errors": [], "warnings": [], "matrix_density": 0.0, "nonzero_cells": 0, "total_cells": 0}

        return {
            "total_cos": len(cos_out),
            "course_outcomes": cos_out,
            "co_po_mappings": result["co_po_mappings"],
            "co_pso_mappings": result["co_pso_mappings"],
            "domain": result.get("domain"),
            "quality_warnings": result.get("quality_warnings", []),
            "units": result.get("units", []),
            "coverage": result.get("coverage", {}),
            "mapping_justifications": result.get("mapping_justifications", {}),
            "validation": {
                "can_save": validation["can_save"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "matrix_density": validation["matrix_density"],
                "nonzero_cells": validation.get("nonzero_cells", 0),
                "total_cells": validation.get("total_cells", 0),
            },
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"CO generation failed for course {course_id}: {str(e)}")
        # If it's a known error like a validation error, return appropriate status
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=f"CO Generation failed: {str(e)}")


@router.get("/courses/{course_id}/co-lock-state", summary="Get CO lock state for a course")
async def get_co_lock_state(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    return await _get_co_lock(course_id)


@router.post("/courses/{course_id}/co-lock", summary="Lock CO generation/editing for a course")
async def lock_course_co(
    course_id: str,
    reason: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    payload = await _set_co_lock(course_id=course_id, locked=True, by=str(current_user.id), reason=reason)
    return {"status": "locked", **payload}


@router.post("/courses/{course_id}/co-unlock", summary="Unlock CO generation/editing for a course")
async def unlock_course_co(
    course_id: str,
    reason: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in {"admin", "hod", "accreditation_officer"}:
        raise HTTPException(status_code=403, detail="Only lead/hod/admin can unlock COs")
    payload = await _set_co_lock(course_id=course_id, locked=False, by=str(current_user.id), reason=reason)
    return {"status": "unlocked", **payload}


@router.post("/courses/{course_id}/co-defaults", summary="Upsert default CO templates for a course code and regulation")
async def upsert_co_defaults(
    course_id: str,
    regulation: str = Query(...),
    payload: CODefaultsPayload = ...,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) not in {"admin", "hod"}:
        raise HTTPException(status_code=403, detail="Only HOD/Admin can maintain default CO library")

    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    key = _co_defaults_key(course.course_code, regulation)
    await _safe_set_json(f"faculty:{key}", {"items": payload.templates}, ttl_seconds=86400 * 30)
    return {"status": "saved", "course_code": course.course_code, "regulation": regulation, "count": len(payload.templates)}


@router.get("/courses/{course_id}/co-defaults", summary="Get default CO templates for this course code")
async def get_co_defaults(
    course_id: str,
    regulation: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    key = _co_defaults_key(course.course_code, regulation)
    payload = await _safe_get_json(f"faculty:{key}")
    items = payload.get("items", []) if payload else []
    return {"course_code": course.course_code, "regulation": regulation, "count": len(items), "templates": items}


# ══════════════════════════════════════════════════════════════════════════════
# EXAMS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/courses/{course_id}/exams", response_model=ExamResponse, summary="Create an exam")
async def create_exam(
    course_id: str,
    payload: ExamCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = CourseService(session)

    assessment_code = (payload.assessment_code or "").strip().upper() if payload.assessment_code else None
    if assessment_code and assessment_code not in {"T1", "T2", "T3", "T4", "T5", "SEE"}:
        raise HTTPException(status_code=400, detail="assessment_code must be one of T1/T2/T3/T4/T5/SEE")

    exam = await svc.create_exam(
        course_id=course_id, exam_name=payload.exam_name,
        exam_type=payload.exam_type, total_marks=payload.total_marks,
        duration_minutes=payload.duration_minutes,
        exam_date=payload.exam_date,
        question_count=payload.number_of_questions,
    )
    await _set_exam_meta(
        exam.id,
        {
            "assessment_code": assessment_code,
            "weightage_pct": payload.weightage_pct,
            "units_covered": payload.units_covered or [],
            "number_of_questions": payload.number_of_questions,
            "exam_date": payload.exam_date.isoformat() if payload.exam_date else None,
        },
    )
    logger.info(f"Exam created: {exam.id}")
    await invalidate_course_report_cache(course_id)
    return {
        "id": exam.id,
        "course_id": exam.course_id,
        "exam_name": exam.exam_name,
        "exam_type": str(exam.exam_type.value if hasattr(exam.exam_type, "value") else exam.exam_type),
        "total_marks": exam.total_marks,
        "duration_minutes": exam.duration_minutes,
    }


@router.get("/courses/{course_id}/exams", summary="List all exams for a course")
async def list_exams(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(
        select(Exam).where(Exam.course_id == course_id).order_by(Exam.created_at)
    )
    exams = result.scalars().all()
    out = []
    for e in exams:
        meta = await _get_exam_meta(e.id)
        out.append({
            "id": e.id,
            "course_id": e.course_id,
            "exam_name": e.exam_name,
            "exam_type": str(e.exam_type.value if hasattr(e.exam_type, "value") else e.exam_type),
            "total_marks": e.total_marks,
            "duration_minutes": e.duration_minutes,
            "question_count": e.question_count,
            "assessment_code": meta.get("assessment_code"),
            "weightage_pct": meta.get("weightage_pct"),
            "units_covered": meta.get("units_covered", []),
            "number_of_questions": meta.get("number_of_questions"),
        })
    return out


@router.put("/courses/{course_id}/exams/{exam_id}", summary="Update an exam")
async def update_exam(
    course_id: str,
    exam_id: str,
    payload: ExamUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(
        select(Exam).where(Exam.id == exam_id, Exam.course_id == course_id)
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key in {"assessment_code", "weightage_pct", "units_covered", "number_of_questions"}:
            continue
        setattr(exam, key, value)

    if payload.number_of_questions is not None:
        exam.question_count = payload.number_of_questions

    await session.commit()
    meta = await _get_exam_meta(exam_id)
    if payload.assessment_code is not None:
        assessment_code = payload.assessment_code.strip().upper()
        if assessment_code not in {"T1", "T2", "T3", "T4", "T5", "SEE"}:
            raise HTTPException(status_code=400, detail="assessment_code must be one of T1/T2/T3/T4/T5/SEE")
        meta["assessment_code"] = assessment_code
    if payload.weightage_pct is not None:
        meta["weightage_pct"] = payload.weightage_pct
    if payload.units_covered is not None:
        meta["units_covered"] = payload.units_covered
    if payload.number_of_questions is not None:
        meta["number_of_questions"] = payload.number_of_questions
    if payload.exam_date is not None:
        meta["exam_date"] = payload.exam_date.isoformat()
    await _set_exam_meta(exam_id, meta)

    return {
        "id": exam.id,
        "course_id": exam.course_id,
        "exam_name": exam.exam_name,
        "exam_type": str(exam.exam_type.value if hasattr(exam.exam_type, "value") else exam.exam_type),
        "total_marks": exam.total_marks,
        "duration_minutes": exam.duration_minutes,
        "question_count": exam.question_count,
        "assessment_code": meta.get("assessment_code"),
        "weightage_pct": meta.get("weightage_pct"),
        "units_covered": meta.get("units_covered", []),
        "number_of_questions": meta.get("number_of_questions"),
    }


@router.delete("/courses/{course_id}/exams/{exam_id}", summary="Delete an exam")
async def delete_exam(
    course_id: str,
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    result = await session.execute(
        select(Exam).where(Exam.id == exam_id, Exam.course_id == course_id)
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    await session.delete(exam)
    await session.commit()
    await invalidate_course_report_cache(course_id)
    await invalidate_exam_preview_cache(exam_id)
    return {"status": "deleted", "exam_id": exam_id, "course_id": course_id}


# ══════════════════════════════════════════════════════════════════════════════
# QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/exams/{exam_id}/questions", summary="Add questions with AI Bloom detection and auto CO-mapping")
async def add_exam_questions(
    exam_id: str,
    payload: QuestionsAddRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    """
    Add questions to an exam.
    Uses Gemini AI to:
    1. Detect Bloom's Taxonomy level for each question
    2. Auto-map each question to the most appropriate CO
    """
    prepared_questions = [q.model_dump() for q in payload.questions]
    for q in prepared_questions:
        has_override = bool(
            q.get("bloom_level")
            or q.get("co_mapped")
            or q.get("co_ids")
            or q.get("co_code")
            or q.get("co_codes")
        )
        if has_override and not (q.get("override_reason") or "").strip():
            raise HTTPException(status_code=400, detail="override_reason is required when overriding BT level or CO mapping")

    svc = QuestionAnalysisService(session)
    created = await svc.add_questions(
        exam_id, prepared_questions, detect_bloom_with_llm=True
    )

    question_meta = []
    for source_q, created_q in zip(prepared_questions, created):
        requested_cos = source_q.get("co_mapped") or source_q.get("co_ids") or source_q.get("co_codes") or []
        if not requested_cos and source_q.get("co_code"):
            requested_cos = [source_q.get("co_code")]
        question_meta.append(
            {
                "question_id": created_q.id,
                "question_number": source_q.get("question_number"),
                "part_label": source_q.get("part_label"),
                "either_or_pair": source_q.get("either_or_pair"),
                "co_mapped": requested_cos,
                "override_reason": source_q.get("override_reason"),
                "co_suggestion": {
                    "confidence": float(created_q.bloom_confidence or 0.0),
                    "reason": "AI inferred mapping using question topic and bloom level",
                },
            }
        )
    await _set_question_meta(exam_id, question_meta)

    from app.core.infrastructure.search_client import is_configured as es_is_configured, index_question
    indexed = 0
    if es_is_configured():
        for q in created:
            doc = {
                "exam_id": exam_id,
                "question_number": q.question_number,
                "question_text": q.question_text,
                "marks": q.marks,
                "bloom_level": str(q.bloom_level.value if hasattr(q.bloom_level, "value") else q.bloom_level),
            }
            index_question(q.id, doc)
            indexed += 1

    logger.info(f"Added {len(created)} questions to exam {exam_id}")
    return {
        "exam_id": exam_id,
        "questions_added": len(created),
        "search_indexed": indexed,
        "questions": [
            {
                "id": q.id,
                "question_number": q.question_number,
                "question_text": (q.question_text or "")[:100],
                "marks": q.marks,
                "bloom_level": str(q.bloom_level.value if hasattr(q.bloom_level, "value") else q.bloom_level),
                "bloom_confidence": q.bloom_confidence,
                "co_suggestion": {
                    "confidence": float(q.bloom_confidence or 0.0),
                    "reason": "Suggested from semantic similarity and bloom classification",
                },
            }
            for q in created
        ],
    }


@router.post("/exams/{exam_id}/questions/upload-bulk", summary="Bulk upload questions from CSV/Excel/Document/ODF file")
async def upload_questions_file(
    exam_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload questions in bulk from CSV, Excel, DOC/DOCX, ODT/ODF, TXT, or ODS file.
    
    CSV Format:
        question_text, marks, bloom_level, co_code
        "What is...", 5, "understand", "CO1"
        "Explain...", 10, "apply", "CO2"
    
    Excel/ODS Format: Same columns, can have multiple sheets

    DOC/DOCX/ODT/ODF/TXT Format:
        One question per paragraph/line.
        Optional marks hints are supported, e.g. "What is X? (5 marks)"
    
    Returns: Count of questions added, extracted data preview, and any warnings
    """
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    
    # Import file processing utilities
    from app.core.utils.file_processor import (
        parse_file_by_type, extract_question_data, validate_question_collection
    )
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    
    try:
        # Parse file
        rows, file_format, metadata = await parse_file_by_type(
            content,
            file.filename or "",
            allowed_extensions=("csv", "xlsx", "xls", "ods", "doc", "docx", "odt", "odf", "txt"),
            content_type=file.content_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"File parsing failed: {str(e)}")
    
    # Extract question data from each row
    extracted_questions = []
    extraction_errors = []
    
    for idx, row in enumerate(rows, 1):
        try:
            q_data = extract_question_data(row)
            if q_data:
                extracted_questions.append(q_data)
            else:
                extraction_errors.append(f"Row {idx}: Row ignored (missing required fields)")
        except Exception as e:
            extraction_errors.append(f"Row {idx}: {str(e)}")
    
    # Validate extracted questions
    is_valid, validation_msg, validated_qs = await validate_question_collection(extracted_questions)
    
    if not validated_qs:
        raise HTTPException(
            status_code=422,
            detail=f"No valid questions extracted. {validation_msg}\nErrors: " + 
                   "; ".join(extraction_errors[:3])
        )
    
    # Add questions via service
    svc = QuestionAnalysisService(session)
    created_questions = await svc.add_questions(
        exam_id, 
        validated_qs,
        detect_bloom_with_llm=True
    )

    question_meta = []
    for source_q, created_q in zip(validated_qs, created_questions):
        requested_cos = source_q.get("co_mapped") or source_q.get("co_ids") or source_q.get("co_codes") or []
        if not requested_cos and source_q.get("co_code"):
            requested_cos = [source_q.get("co_code")]
        question_meta.append(
            {
                "question_id": created_q.id,
                "question_number": source_q.get("question_number"),
                "part_label": source_q.get("part_label"),
                "either_or_pair": source_q.get("either_or_pair"),
                "co_mapped": requested_cos,
                "override_reason": source_q.get("override_reason"),
                "co_suggestion": {
                    "confidence": float(created_q.bloom_confidence or 0.0),
                    "reason": "Suggested from semantic similarity and bloom classification",
                },
            }
        )
    await _set_question_meta(exam_id, question_meta)
    
    # Update exam report caches
    exam_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_result.scalar_one_or_none()
    if exam:
        await invalidate_course_report_cache(exam.course_id)
        await invalidate_exam_preview_cache(exam_id)
    
    logger.info(f"Bulk uploaded {len(created_questions)} questions to exam {exam_id}")
    
    return {
        "exam_id": exam_id,
        "status": "success",
        "file_format": file_format,
        "file_metadata": metadata,
        "questions_added": len(created_questions),
        "questions_extracted": len(extracted_questions),
        "questions_validated": len(validated_qs),
        "validation_message": validation_msg,
        "extraction_warnings": extraction_errors[:10],
        "extraction_warnings_total": len(extraction_errors),
        "sample_questions": [
            {
                "id": q.id,
                "question_text": (q.question_text or "")[:80] + ("..." if len(q.question_text or "") > 80 else ""),
                "marks": q.marks,
                "bloom_level": str(q.bloom_level.value if hasattr(q.bloom_level, "value") else q.bloom_level),
            }
            for q in created_questions[:3]
        ]
    }


@router.get("/exams/{exam_id}/questions", summary="List all questions for an exam")
async def list_exam_questions(
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    from app.core.database.models import ExamQuestion, question_co_mapping_table
    result = await session.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.question_number)
    )
    questions = result.unique().scalars().all()
    meta_payload = await _safe_get_json(f"exam_question_meta:{exam_id}") or {}
    meta_by_id = {str(x.get("question_id")): x for x in meta_payload.get("questions", [])}
    out = []
    for q in questions:
        co_r = await session.execute(
            select(
                question_co_mapping_table.c.course_outcome_id,
                CourseOutcome.code,
            )
            .join(CourseOutcome, CourseOutcome.id == question_co_mapping_table.c.course_outcome_id)
            .where(question_co_mapping_table.c.question_id == q.id)
        )
        mapped_cos = [{"co_id": r[0], "co_code": r[1]} for r in co_r.all()]
        out.append({
            "id": q.id,
            "question_number": q.question_number,
            "question_text":  q.question_text,
            "marks":          q.marks,
            "question_type":  str(q.question_type.value if hasattr(q.question_type, "value") else q.question_type),
            "bloom_level":    str(q.bloom_level.value if hasattr(q.bloom_level, "value") else q.bloom_level),
            "bloom_confidence": q.bloom_confidence,
            "mapped_cos":     mapped_cos,
            "part_label": meta_by_id.get(str(q.id), {}).get("part_label"),
            "either_or_pair": meta_by_id.get(str(q.id), {}).get("either_or_pair"),
            "override_reason": meta_by_id.get(str(q.id), {}).get("override_reason"),
            "co_suggestion": meta_by_id.get(str(q.id), {}).get("co_suggestion", {}),
        })
    return {"exam_id": exam_id, "questions": out, "total": len(out)}


@router.put("/exams/{exam_id}/questions/{question_id}", summary="Update an exam question")
async def update_exam_question(
    exam_id: str,
    question_id: str,
    payload: QuestionUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    from app.core.database.models import ExamQuestion

    result = await session.execute(
        select(ExamQuestion).where(ExamQuestion.id == question_id, ExamQuestion.exam_id == exam_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    updates = payload.model_dump(exclude_unset=True)
    if "bloom_level" in updates and not (updates.get("override_reason") or "").strip():
        raise HTTPException(status_code=400, detail="override_reason is required when overriding BT level")

    for key, value in updates.items():
        if key == "override_reason":
            continue
        setattr(question, key, value)

    await session.commit()

    meta_payload = await _safe_get_json(f"exam_question_meta:{exam_id}") or {"exam_id": exam_id, "questions": []}
    q_meta_list = list(meta_payload.get("questions", []))
    updated = False
    for q_meta in q_meta_list:
        if str(q_meta.get("question_id")) == str(question_id):
            if "override_reason" in updates:
                q_meta["override_reason"] = updates.get("override_reason")
            updated = True
            break
    if not updated and "override_reason" in updates:
        q_meta_list.append({"question_id": question_id, "override_reason": updates.get("override_reason")})
    await _set_question_meta(exam_id, q_meta_list)

    return {
        "id": question.id,
        "exam_id": question.exam_id,
        "question_number": question.question_number,
        "question_text": question.question_text,
        "marks": question.marks,
        "question_type": str(question.question_type.value if hasattr(question.question_type, "value") else question.question_type),
        "bloom_level": str(question.bloom_level.value if hasattr(question.bloom_level, "value") else question.bloom_level),
        "override_reason": updates.get("override_reason"),
    }


@router.delete("/exams/{exam_id}/questions/{question_id}", summary="Delete an exam question")
async def delete_exam_question(
    exam_id: str,
    question_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    from app.core.database.models import ExamQuestion, StudentMarks, question_co_mapping_table

    result = await session.execute(
        select(ExamQuestion).where(ExamQuestion.id == question_id, ExamQuestion.exam_id == exam_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await session.execute(
        delete(question_co_mapping_table).where(question_co_mapping_table.c.question_id == question_id)
    )
    await session.execute(delete(StudentMarks).where(StudentMarks.question_id == question_id))
    await session.delete(question)
    await session.commit()
    return {"status": "deleted", "exam_id": exam_id, "question_id": question_id}


@router.post("/exams/{exam_id}/questions/{question_id}/map-co", summary="Manually map a question to COs")
async def map_question_to_co(
    exam_id: str,
    question_id: str,
    co_ids: List[str],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    svc = QuestionAnalysisService(session)
    result = await svc.map_question_to_cos(question_id, co_ids)
    return result


@router.post("/exams/{exam_id}/analyze-questions", summary="Analyze question statistics and Bloom distribution")
async def analyze_questions(
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    svc = QuestionAnalysisService(session)
    return await svc.analyze_exam_questions(exam_id)


@router.post("/exams/{exam_id}/detect-bloom-levels", summary="Re-detect Bloom levels for all questions via AI")
async def detect_bloom_levels(
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    svc = QuestionAnalysisService(session)
    result = await svc.detect_all_bloom_levels(exam_id)
    logger.info(f"Bloom detected for exam {exam_id}: {result['detected']}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT MARKS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/exams/{exam_id}/marks", summary="Submit student marks (JSON spreadsheet-style)")
async def submit_marks_json(
    exam_id: str,
    payload: BulkMarksRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    """
    Submit marks in spreadsheet-style JSON:
    {
      "rows": [
        {"student_id": "S1", "marks": {"1": 8, "2": 7, "3": 12}},
        {"student_id": "S2", "marks": {"1": 6, "2": 5, "3": 10}}
      ]
    }
    Question keys are question_number strings.
    """
    svc = QuestionAnalysisService(session)
    rows = [{"student_id": r.student_id, "marks": r.marks} for r in payload.rows]
    result = await svc.process_marks_json(exam_id, rows)
    ex_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = ex_result.scalar_one_or_none()
    if exam:
        await invalidate_course_report_cache(exam.course_id)
        await invalidate_exam_preview_cache(exam_id)
    logger.info(f"Marks saved for exam {exam_id}: {result['rows_saved']}")
    return {"exam_id": exam_id, **result}


@router.post("/exams/{exam_id}/upload-marks", summary="Upload marks from CSV or Excel file")
async def upload_marks_file(
    exam_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    """
    Upload student marks as CSV or Excel (.xlsx).

    Spreadsheet format (recommended):
       student_id | Q1 | Q2 | Q3 | Q4
       S1         |  8 |  7 | 12 | 10
       S2         |  6 |  5 | 10 | 12

    Column headers Q1, Q2,... or 1, 2,... match question_number.
    
    Returns: Number of rows processed, students updated, and extraction metadata.
    """
    content = await file.read()
    
    # Get file processing metadata
    from app.core.utils.file_processor import parse_file_by_type
    try:
        rows, file_format, metadata = await parse_file_by_type(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"File parsing failed: {str(e)}")
    
    # Process marks
    svc = QuestionAnalysisService(session)
    result = await svc.process_marks_file(exam_id, content, filename=file.filename or "")
    
    # Invalidate caches
    ex_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = ex_result.scalar_one_or_none()
    if exam:
        await invalidate_course_report_cache(exam.course_id)
        await invalidate_exam_preview_cache(exam_id)
    
    logger.info(f"Marks file uploaded for exam {exam_id}: {result.get('rows_processed',0)} rows")
    
    return {
        "exam_id": exam_id,
        "status": "success",
        "file_format": file_format,
        "file_metadata": metadata,
        "rows_processed": result.get('rows_processed', result.get('rows_saved', 0)),
        "rows_saved": result.get('rows_saved', result.get('rows_processed', 0)),
        "students_updated": result.get('students_count', result.get('rows_processed', 0)),
        "processing_result": result,
    }



@router.get("/exams/{exam_id}/marks", summary="Get all student marks for an exam")
async def get_exam_marks(
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    from app.core.database.models import StudentMarks, ExamQuestion
    marks_result = await session.execute(
        select(StudentMarks.student_id, ExamQuestion.question_number,
               StudentMarks.marks_obtained, ExamQuestion.marks)
        .join(ExamQuestion, StudentMarks.question_id == ExamQuestion.id)
        .where(StudentMarks.exam_id == exam_id)
        .order_by(StudentMarks.student_id, ExamQuestion.question_number)
    )
    marks_rows = marks_result.all()

    # Pivot to spreadsheet form
    table: Dict[str, Dict[int, float]] = {}
    max_marks: Dict[int, float] = {}
    for sid, q_num, obtained, q_max in marks_rows:
        table.setdefault(sid, {})[q_num] = float(obtained)
        max_marks[q_num] = float(q_max)

    q_nums = sorted(max_marks.keys())
    rows_out = [
        {"student_id": sid, **{f"Q{qn}": table[sid].get(qn, 0) for qn in q_nums},
         "total": round(sum(table[sid].get(qn, 0) for qn in q_nums), 2)}
        for sid in sorted(table.keys())
    ]
    return {
        "exam_id": exam_id,
        "question_max_marks": {f"Q{qn}": max_marks[qn] for qn in q_nums},
        "total_students": len(table),
        "rows": rows_out,
    }


@router.post("/courses/{course_id}/co-attainment/upload-data", summary="Upload CO attainment data from CSV or Excel file")
async def upload_attainment_data(
    course_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload CO attainment data from CSV or Excel file.
    
    CSV Format:
        co_code, attainment_percentage, attainment_level
        CO1, 75.5, Level 3
        CO2, 65.0, Level 2
        CO3, 45.0, Level 1
    
    Returns: Count of attainment records created/updated and file metadata
    """
    await _assert_faculty_owns_course(session, current_user, course_id)
    
    # Import utilities
    from app.core.utils.file_processor import (
        parse_file_by_type, extract_attainment_data
    )
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    
    try:
        # Parse file
        rows, file_format, metadata = await parse_file_by_type(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"File parsing failed: {str(e)}")
    
    # Extract attainment data from each row
    extracted_data = []
    extraction_errors = []
    co_map = {}  # Map CO codes to their IDs
    
    for idx, row in enumerate(rows, 1):
        try:
            att_data = extract_attainment_data(row)
            if att_data:
                extracted_data.append(att_data)
            else:
                extraction_errors.append(f"Row {idx}: Row ignored (missing required fields)")
        except Exception as e:
            extraction_errors.append(f"Row {idx}: {str(e)}")
    
    if not extracted_data:
        raise HTTPException(
            status_code=422,
            detail=f"No valid attainment records extracted. Errors: " + 
                   "; ".join(extraction_errors[:3])
        )
    
    # Get all COs for this course
    co_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id)
    )
    cos = co_result.scalars().all()
    co_map = {co.code: co.id for co in cos}
    
    # Process each attainment record
    created_count = 0
    updated_count = 0
    skipped = []
    
    for att_rec in extracted_data:
        co_code = att_rec.get('co_code')
        
        # Find CO
        if co_code not in co_map:
            skipped.append(f"CO {co_code} not found in course")
            continue
        
        co_id = co_map[co_code]
        
        # Check if attainment record exists
        from app.core.database.models import COAttainment
        existing = await session.execute(
            select(COAttainment).where(COAttainment.course_outcome_id == co_id)
        )
        co_att = existing.scalar_one_or_none()
        
        if co_att:
            # Update existing
            co_att.attainment_percentage = att_rec['attainment_percentage']
            co_att.attainment_level = att_rec['attainment_level']
            updated_count += 1
        else:
            # Create new
            co_att = COAttainment(
                id=str(uuid.uuid4()),
                course_outcome_id=co_id,
                attainment_percentage=att_rec['attainment_percentage'],
                attainment_level=att_rec['attainment_level'],
                calculated_at=datetime.utcnow()
            )
            session.add(co_att)
            created_count += 1
    
    if created_count + updated_count > 0:
        await session.commit()
        await invalidate_course_report_cache(course_id)
    
    logger.info(f"Attainment data uploaded for course {course_id}: {created_count} created, {updated_count} updated")
    
    return {
        "course_id": course_id,
        "status": "success",
        "file_format": file_format,
        "file_metadata": metadata,
        "records_processed": len(extracted_data),
        "records_created": created_count,
        "records_updated": updated_count,
        "records_skipped": len(skipped),
        "extraction_warnings": extraction_errors[:10],
        "extraction_warnings_total": len(extraction_errors),
        "skipped_details": skipped[:5],
        "summary": f"Created {created_count}, updated {updated_count}, skipped {len(skipped)} CO attainment records"
    }


@router.get("/marks/{exam_id}/preview", summary="Live CO attainment preview from Redis cache")
async def marks_preview(
    exam_id: str,
    threshold_pct: float = Query(0.40),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    exam = await _assert_faculty_owns_exam(session, current_user, exam_id)
    from app.core.infrastructure.multi_tier_cache import get_or_compute

    async def _compute_preview() -> Dict[str, Any]:
        svc = AttainmentService(session)
        rows = await svc.calculate_course_outcome_attainments(exam.course_id, exam_id, threshold_pct)
        return {
            "course_id": exam.course_id,
            "threshold_pct": threshold_pct,
            "preview": rows,
            "attainments": rows,
            "count": len(rows),
        }

    cache_key = f"co_preview:{exam_id}:{threshold_pct:.2f}"
    payload, source = await get_or_compute(
        cache_key,
        _compute_preview,
        fresh_ttl=300,
        stale_ttl=900,
    )
    return {"exam_id": exam_id, "source": source, **payload}


@router.post("/marks/{exam_id}/submit", summary="Submit marks and lock editing")
async def marks_submit(
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.core.infrastructure.redis_client import set_json

    await _assert_faculty_owns_exam(session, current_user, exam_id)

    lock_key = f"marks_lock:{exam_id}"
    await set_json(lock_key, {"locked": True, "by": current_user.id, "status": "submitted"}, ttl_seconds=86400)
    await _add_notification(
        user_id=str(current_user.id),
        title="Marks Submitted",
        message=f"Marks submitted for exam {exam_id}. Awaiting approval.",
        notification_type="marks_submitted",
        action_link=f"/faculty/marks/{exam_id}",
    )
    return {"exam_id": exam_id, "status": "submitted", "locked": True}


@router.post("/marks/{exam_id}/approve", summary="Approve marks and trigger async attainment")
async def marks_approve(
    exam_id: str,
    program_id: str = Query(...),
    threshold_pct: float = Query(0.40),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_exam(session, current_user, exam_id)
    from app.core.infrastructure.redis_client import set_json
    from app.communication.events.event_bus import event_bus, EventType, SystemEvent

    ex_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = ex_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    faculty_result = await session.execute(select(Course).where(Course.id == exam.course_id))
    faculty_course = faculty_result.scalar_one_or_none()

    task = run_full_pipeline_task.delay(exam.course_id, program_id, threshold_pct)

    await set_json(
        f"marks_lock:{exam_id}",
        {"locked": True, "by": current_user.id, "status": "approved", "task_id": task.id},
        ttl_seconds=86400,
    )

    await event_bus.publish(SystemEvent(
        event_type=EventType.MARKS_PROCESSED,
        timestamp=datetime.utcnow(),
        source_module="api_routes",
        data={"exam_id": exam_id, "course_id": exam.course_id, "task_id": task.id},
    ))

    if faculty_course and faculty_course.created_by:
        await _add_notification(
            user_id=str(faculty_course.created_by),
            title="Marks Approved",
            message=f"Course lead approved marks for exam {exam_id}.",
            notification_type="marks_approved",
            action_link=f"/faculty/course/{exam.course_id}/co-attainment",
        )

    await invalidate_course_report_cache(exam.course_id)
    await invalidate_exam_preview_cache(exam_id)

    return {
        "exam_id": exam_id,
        "course_id": exam.course_id,
        "status": "approved",
        "task_id": task.id,
    }


@router.post("/marks/{exam_id}/unlock", summary="Unlock marks editing")
async def marks_unlock(
    exam_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.core.infrastructure.redis_client import delete_key

    await _assert_faculty_owns_exam(session, current_user, exam_id)

    deleted = await delete_key(f"marks_lock:{exam_id}")
    ex_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = ex_result.scalar_one_or_none()
    if exam:
        await invalidate_course_report_cache(exam.course_id)
        await invalidate_exam_preview_cache(exam_id)
    await _add_notification(
        user_id=str(current_user.id),
        title="Marks Unlocked",
        message=f"Marks editing unlocked for exam {exam_id}.",
        notification_type="marks_returned",
        action_link=f"/faculty/marks/{exam_id}",
    )
    return {"exam_id": exam_id, "status": "unlocked", "lock_removed": bool(deleted)}


# ══════════════════════════════════════════════════════════════════════════════
# NBA FIXED POs + DEPARTMENT PSOs
# ══════════════════════════════════════════════════════════════════════════════

_NBA_POS = [
    {"code": "PO1",  "name": "Engineering Knowledge",                          "statement": "Apply knowledge of mathematics, science, engineering fundamentals and an engineering specialisation to the solution of complex engineering problems.", "editable": False},
    {"code": "PO2",  "name": "Problem Analysis",                                "statement": "Identify, formulate, review research literature, and analyse complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences and engineering sciences.", "editable": False},
    {"code": "PO3",  "name": "Design/Development of Solutions",                 "statement": "Design solutions for complex engineering problems and design system components or processes that meet the specified needs with appropriate consideration for the public health and safety, and the cultural, societal, and environmental considerations.", "editable": False},
    {"code": "PO4",  "name": "Conduct Investigations of Complex Problems",       "statement": "Use research-based knowledge and research methods including design of experiments, analysis and interpretation of data, and synthesis of the information to provide valid conclusions.", "editable": False},
    {"code": "PO5",  "name": "Modern Tool Usage",                               "statement": "Create, select, and apply appropriate techniques, resources, and modern engineering and IT tools including prediction and modelling to complex engineering activities with an understanding of the limitations.", "editable": False},
    {"code": "PO6",  "name": "The Engineer and Society",                        "statement": "Apply reasoning informed by the contextual knowledge to assess societal, health, safety, legal and cultural issues and the consequent responsibilities relevant to the professional engineering practice.", "editable": False},
    {"code": "PO7",  "name": "Environment and Sustainability",                  "statement": "Understand the impact of the professional engineering solutions in societal and environmental contexts, and demonstrate the knowledge of, and need for sustainable development.", "editable": False},
    {"code": "PO8",  "name": "Ethics",                                          "statement": "Apply ethical principles and commit to professional ethics and responsibilities and norms of the engineering practice.", "editable": False},
    {"code": "PO9",  "name": "Individual and Team Work",                        "statement": "Function effectively as an individual, and as a member or leader in diverse teams, and in multidisciplinary settings.", "editable": False},
    {"code": "PO10", "name": "Communication",                                   "statement": "Communicate effectively on complex engineering activities with the engineering community and with society at large, such as, being able to comprehend and write effective reports and design documentation, make effective presentations, and give and receive clear instructions.", "editable": False},
    {"code": "PO11", "name": "Project Management and Finance",                  "statement": "Demonstrate knowledge and understanding of the engineering and management principles and apply these to one's own work, as a member and leader in a team, to manage projects and in multidisciplinary environments.", "editable": False},
    {"code": "PO12", "name": "Life-long Learning",                              "statement": "Recognise the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change.", "editable": False},
]


@router.get("/nba/pos", summary="Get all 12 NBA standard Program Outcomes (fixed, read-only)")
async def get_nba_pos(current_user: User = Depends(get_current_user)):
    """
    Returns the 12 fixed NBA POs.
    These are seeded once at deployment and are NEVER editable by any user.
    Rule: PO1-PO12 are permanently fixed by NBA across all engineering colleges.
    """
    return _NBA_POS


@router.get("/nba/psos/{department}", summary="Get department PSOs (HOD-managed, read-only for faculty)")
async def get_department_psos(
    department: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns PSOs for a department.
    Rule: PSOs are fixed per department — editable only by HOD role.
    Faculty can only read them.
    """
    dept_key = f"DEPT:{department.strip().upper()}"
    result = await session.execute(
        select(ProgramSpecificOutcome)
        .where(ProgramSpecificOutcome.program == dept_key)
        .order_by(ProgramSpecificOutcome.code)
    )
    psos = result.scalars().all()
    role = _role_value(current_user)
    return [
        {
            "code": p.code,
            "statement": p.statement,
            "description": p.description,
            "editable": role in {"admin", "hod"},
        }
        for p in psos
    ]


@router.put("/nba/psos/{department}/{pso_code}", summary="Update a department PSO (HOD/Admin only)")
async def update_department_pso(
    department: str,
    pso_code: str,
    payload: ProgramOutcomePayload,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update a department PSO.
    Rule: Only HOD or Admin can edit PSOs.
    Faculty attempting this will receive 403.
    Warning: Changing PSO definition affects attainment reports for ALL courses in the department.
    """
    role = _role_value(current_user)
    if role not in {"admin", "hod"}:
        raise HTTPException(
            status_code=403,
            detail="PSOs are department-level definitions. Contact your HOD or Program Coordinator to update PSOs.",
        )
    dept_key = f"DEPT:{department.strip().upper()}"
    result = await session.execute(
        select(ProgramSpecificOutcome).where(
            ProgramSpecificOutcome.program == dept_key,
            ProgramSpecificOutcome.code == pso_code,
        )
    )
    pso = result.scalar_one_or_none()
    if not pso:
        raise HTTPException(status_code=404, detail=f"PSO {pso_code} not found for department {department}")

    pso.statement = payload.statement
    pso.description = payload.description
    await session.commit()

    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        entity_type="pso",
        action=f"PSO {pso_code} updated for {department} by {current_user.username}",
        user_id=str(current_user.id),
        timestamp=datetime.utcnow(),
    )
    session.add(audit)
    await session.commit()

    return {
        "code": pso.code,
        "statement": pso.statement,
        "description": pso.description,
        "warning": "Changing PSO definition affects attainment reports for ALL courses in this department.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# PROGRAM OUTCOMES (PO) & PROGRAM SPECIFIC OUTCOMES (PSO)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/programs/{program_id}/outcomes", summary="Add a Program Outcome (PO)")
async def create_program_outcome(
    program_id: str,
    payload: ProgramOutcomePayload,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Upsert by code+program
    existing = await session.execute(
        select(ProgramOutcome).where(
            ProgramOutcome.program == program_id,
            ProgramOutcome.code == payload.code,
        )
    )
    po = existing.scalar_one_or_none()
    if po:
        po.statement = payload.statement
        po.description = payload.description
    else:
        po = ProgramOutcome(
            id=str(uuid.uuid4()),
            code=payload.code,
            statement=payload.statement,
            description=payload.description,
            program=program_id,
        )
        session.add(po)
    await session.commit()
    return {"id": po.id, "program": program_id, "code": po.code, "statement": po.statement}


@router.get("/programs/{program_id}/outcomes", summary="List all POs for a program")
async def list_program_outcomes(
    program_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.program == program_id)
        .order_by(ProgramOutcome.code)
    )
    pos = result.scalars().all()
    return [{"id": po.id, "code": po.code, "statement": po.statement, "description": po.description} for po in pos]


@router.get("/programs/{program_id}/outcomes/{po_id}", summary="Get one PO")
async def get_program_outcome(
    program_id: str,
    po_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.id == po_id, ProgramOutcome.program == program_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Program outcome not found")
    return {"id": po.id, "program": po.program, "code": po.code, "statement": po.statement, "description": po.description}


@router.put("/programs/{program_id}/outcomes/{po_id}", summary="Update a Program Outcome (PO)")
async def update_program_outcome(
    program_id: str,
    po_id: str,
    payload: ProgramOutcomePayload,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.id == po_id, ProgramOutcome.program == program_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Program outcome not found")

    po.code = payload.code
    po.statement = payload.statement
    po.description = payload.description
    await session.commit()
    return {"id": po.id, "program": po.program, "code": po.code, "statement": po.statement, "description": po.description}


@router.delete("/programs/{program_id}/outcomes/{po_id}", summary="Delete a Program Outcome (PO)")
async def delete_program_outcome(
    program_id: str,
    po_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.id == po_id, ProgramOutcome.program == program_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Program outcome not found")

    await session.delete(po)
    await session.commit()
    return {"status": "deleted", "program": program_id, "id": po_id}


@router.post("/programs/{program_id}/pso", summary="Add a Program Specific Outcome (PSO)")
async def create_program_specific_outcome(
    program_id: str,
    payload: ProgramOutcomePayload,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    existing = await session.execute(
        select(ProgramSpecificOutcome).where(
            ProgramSpecificOutcome.program == program_id,
            ProgramSpecificOutcome.code == payload.code,
        )
    )
    pso = existing.scalar_one_or_none()
    if pso:
        pso.statement = payload.statement
        pso.description = payload.description
    else:
        pso = ProgramSpecificOutcome(
            id=str(uuid.uuid4()),
            code=payload.code,
            statement=payload.statement,
            description=payload.description,
            program=program_id,
        )
        session.add(pso)
    await session.commit()
    return {"id": pso.id, "program": program_id, "code": pso.code, "statement": pso.statement}


@router.get("/programs/{program_id}/pso", summary="List all PSOs for a program")
async def list_program_specific_outcomes(
    program_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramSpecificOutcome).where(ProgramSpecificOutcome.program == program_id)
        .order_by(ProgramSpecificOutcome.code)
    )
    psos = result.scalars().all()
    return [{"id": p.id, "code": p.code, "statement": p.statement, "description": p.description} for p in psos]


@router.get("/programs/{program_id}/pso/{pso_id}", summary="Get one PSO")
async def get_program_specific_outcome(
    program_id: str,
    pso_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramSpecificOutcome).where(
            ProgramSpecificOutcome.id == pso_id,
            ProgramSpecificOutcome.program == program_id,
        )
    )
    pso = result.scalar_one_or_none()
    if not pso:
        raise HTTPException(status_code=404, detail="Program specific outcome not found")
    return {"id": pso.id, "program": pso.program, "code": pso.code, "statement": pso.statement, "description": pso.description}


@router.put("/programs/{program_id}/pso/{pso_id}", summary="Update a Program Specific Outcome (PSO)")
async def update_program_specific_outcome(
    program_id: str,
    pso_id: str,
    payload: ProgramOutcomePayload,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramSpecificOutcome).where(
            ProgramSpecificOutcome.id == pso_id,
            ProgramSpecificOutcome.program == program_id,
        )
    )
    pso = result.scalar_one_or_none()
    if not pso:
        raise HTTPException(status_code=404, detail="Program specific outcome not found")

    pso.code = payload.code
    pso.statement = payload.statement
    pso.description = payload.description
    await session.commit()
    return {"id": pso.id, "program": pso.program, "code": pso.code, "statement": pso.statement, "description": pso.description}


@router.delete("/programs/{program_id}/pso/{pso_id}", summary="Delete a Program Specific Outcome (PSO)")
async def delete_program_specific_outcome(
    program_id: str,
    pso_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ProgramSpecificOutcome).where(
            ProgramSpecificOutcome.id == pso_id,
            ProgramSpecificOutcome.program == program_id,
        )
    )
    pso = result.scalar_one_or_none()
    if not pso:
        raise HTTPException(status_code=404, detail="Program specific outcome not found")

    await session.delete(pso)
    await session.commit()
    return {"status": "deleted", "program": program_id, "id": pso_id}


# ══════════════════════════════════════════════════════════════════════════════
# CO-PO / CO-PSO SEMANTIC MAPPING
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/map-co-po", summary="Semantic embedding-based CO → PO mapping")
async def map_co_to_po(
    course_id: str = Query(...),
    program_id: Optional[str] = Query(None),
    threshold: float = Query(0.3, description="Minimum similarity score (0-1)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Uses Gemini embeddings to compute semantic similarity between COs and POs.
    Creates CO-PO mappings with similarity scores.
    Similarity → mapping level: ≥0.75=3(strong), ≥0.50=2(medium), ≥0.10=1(weak)
    """
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="po")
    svc = SemanticMappingService(session)
    mappings = await svc.auto_map_cos_to_pos(course_id, resolved_program_id, threshold=threshold)
    logger.info(f"CO-PO mapping: {len(mappings)} for course {course_id}")
    return {
        "mappings_created": len(mappings),
        "mappings": mappings,
        "requested_program_id": program_id,
        "resolved_program_id": resolved_program_id,
    }


@router.post("/map-co-po/llm", summary="LLM-powered CO → PO mapping with reasoning (Gemini/OpenAI)")
async def map_co_to_po_llm(
    course_id: str = Query(...),
    program_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Uses the configured LLM (Gemini/OpenAI/Ollama) to reason about CO-PO alignment.
    For each CO the LLM assigns a level (0/1/2/3) to every PO with a justification.
    Stores results as similarity_score = level/3.0 in co_po_mapping_table.
    Falls back to semantic similarity if LLM is unavailable.
    """
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="po")

    # Load COs
    cos_result = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
    )
    cos = list(cos_result.scalars().all())
    if not cos:
        raise HTTPException(status_code=404, detail="No course outcomes found for this course")

    # Load POs
    pos_result = await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.program == resolved_program_id).order_by(ProgramOutcome.code)
    )
    pos = list(pos_result.scalars().all())
    if not pos:
        raise HTTPException(status_code=404, detail="No program outcomes found")

    from app.ai_engine.llm.llm_client import llm_client
    from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
    import json as _json

    po_list_text = "\n".join(f"  {po.code}: {po.statement}" for po in pos)
    all_mappings: List[Dict[str, Any]] = []
    llm_used = False

    for co in cos:
        prompt = (
            f"You are an OBE (Outcome-Based Education) expert for NBA accreditation.\n"
            f"Course Outcome (CO):\n  {co.code}: {co.statement}\n\n"
            f"Program Outcomes (POs):\n{po_list_text}\n\n"
            f"For each PO, assign a correlation level:\n"
            f"  3 = Strong (CO directly addresses this PO)\n"
            f"  2 = Medium (CO partially addresses this PO)\n"
            f"  1 = Weak (CO has minor relevance to this PO)\n"
            f"  0 = None (no meaningful correlation)\n\n"
            f"Return ONLY a JSON object mapping PO code to level integer, e.g.:\n"
            f'{{"PO1": 3, "PO2": 1, "PO3": 0, ...}}\n'
            f"Include ALL {len(pos)} POs. No explanation, just JSON."
        )
        co_levels: Dict[str, int] = {}
        try:
            llm_response = await llm_client.generate_completion(prompt)
            if llm_response:
                clean = llm_response.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                parsed = _json.loads(clean)
                if isinstance(parsed, dict):
                    co_levels = {k: max(0, min(3, int(v))) for k, v in parsed.items() if isinstance(v, (int, float))}
                    llm_used = True
        except Exception:
            pass

        if not co_levels:
            # Fallback: semantic similarity — include all POs above threshold
            try:
                svc = SemanticMappingService(session)
                for po in pos:
                    sim = await svc._combined_similarity(co.statement, po.statement)
                    lvl = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.30 else 0))
                    if lvl > 0:
                        co_levels[po.code] = lvl
            except Exception:
                co_levels = {}

        for po in pos:
            lvl = co_levels.get(po.code, 0)
            if lvl <= 0:
                continue
            all_mappings.append({
                "course_outcome_id": co.id,
                "program_outcome_id": po.id,
                "similarity_score": round(lvl / 3.0, 6),
                "co_code": co.code,
                "po_code": po.code,
                "level": lvl,
            })

    # Persist to DB
    co_ids = [co.id for co in cos]
    await session.execute(
        co_po_mapping_table.delete().where(co_po_mapping_table.c.course_outcome_id.in_(co_ids))
    )
    if all_mappings:
        await session.execute(
            co_po_mapping_table.insert().values([
                {
                    "course_outcome_id": m["course_outcome_id"],
                    "program_outcome_id": m["program_outcome_id"],
                    "similarity_score": m["similarity_score"],
                }
                for m in all_mappings
            ])
        )
    await session.commit()
    await invalidate_course_report_cache(course_id)

    logger.info(f"LLM CO-PO mapping: {len(all_mappings)} for course {course_id}, llm_used={llm_used}")
    return {
        "mappings_created": len(all_mappings),
        "mappings": all_mappings,
        "resolved_program_id": resolved_program_id,
        "llm_used": llm_used,
        "method": "llm" if llm_used else "semantic_fallback",
    }


@router.post("/map-co-pso", summary="Semantic embedding-based CO → PSO mapping")
async def map_co_to_pso(
    course_id: str = Query(...),
    program_id: Optional[str] = Query(None),
    threshold: float = Query(0.3),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="pso")
    svc = SemanticMappingService(session)
    result = await svc.map_cos_to_psos(session, course_id, resolved_program_id, threshold=threshold)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("error") or "Failed to map CO to PSO")
    mappings = result.get("mappings", [])
    logger.info(f"CO-PSO mapping: {len(mappings)} for course {course_id}")
    return {
        "mappings_created": len(mappings),
        "mappings": mappings,
        "requested_program_id": program_id,
        "resolved_program_id": resolved_program_id,
    }


@router.get("/mapping/graph/co/{co_id}/po-impact", summary="Get CO to PO impact path from Neo4j graph")
async def get_co_po_impact_path(
    co_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.modules.mapping.services.graph_mapping_service import GraphMappingService
    try:
        service = GraphMappingService()
        rows = await service.get_po_impact_path(co_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"co_id": co_id, "impact_paths": rows}


# ══════════════════════════════════════════════════════════════════════════════
# ATTAINMENT CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/attainment/indirect", summary="Set indirect CO attainment from survey data (NBA 80/20 blend)")
async def set_indirect_co_attainment(
    course_id: str = Query(...),
    co_id: str = Query(...),
    survey_avg: float = Query(..., description="Mean Likert score (e.g. 3.8)"),
    scale: float = Query(5.0, description="Max scale value (default 5)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Store indirect CO attainment from exit survey / course-end feedback.
    NBA mandates: Final_CO = Direct*0.80 + Indirect*0.20
    survey_avg is the mean Likert score on a `scale`-point scale.
    Indirect% = (survey_avg / scale) * 100
    """
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    result = await svc.set_indirect_attainment(course_id, co_id, survey_avg, scale)
    return {"status": "saved", **result}


@router.get("/attainment/indirect/{course_id}", summary="Get all indirect CO attainment survey data for a course")
async def get_indirect_co_attainments(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    cos_result = await session.execute(select(CourseOutcome.id, CourseOutcome.code).where(CourseOutcome.course_id == course_id))
    cos = cos_result.all()
    svc = AttainmentService(session)
    items = []
    for co_id, co_code in cos:
        indirect = await svc._get_indirect_attainment(course_id, co_id)
        items.append({"co_id": co_id, "co_code": co_code, "indirect_pct": indirect, "has_survey": indirect is not None})
    return {"course_id": course_id, "items": items}


@router.get("/attainment/gap-analysis/{course_id}", summary="CO/PO gap analysis — achieved vs target level")
async def get_gap_analysis(
    course_id: str,
    threshold_pct: float = Query(0.40),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns COs and POs that are below their target level.
    CO target level is configurable (default Level 2).
    Includes remedial action recommendations.
    """
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    weighted = await svc.calculate_weighted_co_attainments(course_id, threshold_pct)
    summary = await svc.get_course_attainment_summary(course_id)
    gap_cos = [c for c in weighted if c.get("gap_flag")]
    gap_pos = [p for p in summary.get("po_attainments", []) if p.get("attainment_level") == "Level 1"]
    return {
        "course_id": course_id,
        "gap_cos": gap_cos,
        "gap_pos": gap_pos,
        "total_gap_cos": len(gap_cos),
        "total_gap_pos": len(gap_pos),
        "action_required": len(gap_cos) > 0 or len(gap_pos) > 0,
        "recommendations": [
            {
                "co_code": c["co_code"],
                "achieved_level": c["attainment_level"],
                "target_level": c["target_level"],
                "attainment_pct": c["attainment_percentage"],
                "action": c.get("gap_action", "Remedial action required"),
            }
            for c in gap_cos
        ],
    }


@router.get("/attainment/matrix/{course_id}", summary="Get CO-PO correlation matrix for a course")
async def get_co_po_matrix(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the CO-PO matrix with integer levels 0-3 derived from stored similarity scores.
    Level thresholds: sim>=0.75 → 3, sim>=0.50 → 2, sim>=0.10 → 1, else 0.
    """
    course = await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    matrix = await svc.get_co_po_matrix(course.id)
    return matrix


@router.get("/attainment/students/{course_id}", summary="Get per-student CO attainment breakdown")
async def get_student_performance(
    course_id: str,
    exam_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    course = await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    rows = await svc.get_student_performance(course.id, exam_id)
    return {"course_id": course.id, "students": rows, "total": len(rows)}


@router.post("/attainment/calculate-co", summary="Calculate CO attainment (threshold-based) for one exam")
async def calculate_co_attainment(
    course_id: str = Query(...),
    exam_id:   str = Query(...),
    threshold_pct: float = Query(0.40, description="Students must score >= threshold*max_marks to clear CO"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    svc = AttainmentService(session)
    attainments = await svc.calculate_course_outcome_attainments(
        course_id, exam_id, threshold_pct=threshold_pct
    )
    logger.info(f"CO attainment for course {course_id}, exam {exam_id}")
    return {
        "course_id": course_id,
        "exam_id": exam_id,
        "attainments": attainments,
        "co_attainments": attainments,
    }


@router.get("/attainment/weighted/{course_id}", summary="Weighted CO attainment across all exams")
async def get_weighted_co_attainment(
    course_id: str,
    threshold_pct: float = Query(0.40),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    svc = AttainmentService(session)
    result = await svc.calculate_weighted_co_attainments(course_id, threshold_pct)
    return {
        "course_id": course_id,
        # expose under all keys the frontend may read
        "weighted_attainments": result,
        "attainments": result,
        "co_attainments": result,
    }


@router.post("/attainment/calculate-po", summary="Calculate PO attainment from CO-PO mappings")
async def calculate_po_attainment(
    course_id:  str = Query(...),
    program_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="po")
    svc = AttainmentService(session)
    attainments = await svc.calculate_program_outcome_attainments(course_id, resolved_program_id)
    logger.info(f"PO attainment for course {course_id}")
    return {
        "course_id": course_id,
        "program_id": resolved_program_id,
        "requested_program_id": program_id,
        "attainments": attainments,
        "po_attainments": attainments,
    }


@router.post("/attainment/calculate-pso", summary="Calculate PSO attainment from CO-PSO mappings")
async def calculate_pso_attainment(
    course_id:  str = Query(...),
    program_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="pso")
    svc = AttainmentService(session)
    attainments = await svc.calculate_pso_attainments(course_id, resolved_program_id)
    return {
        "course_id": course_id,
        "program_id": resolved_program_id,
        "requested_program_id": program_id,
        "attainments": attainments,
        "pso_attainments": attainments,
    }


@router.post("/attainment/full-pipeline", summary="Run the complete OBE attainment pipeline")
async def run_full_attainment_pipeline(
    course_id:     str   = Query(...),
    program_id:    Optional[str] = Query(None),
    threshold_pct: float = Query(0.40, description="CO attainment threshold (0-1)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    One-shot full OBE attainment:
    1. CO attainment per exam (threshold-based)
    2. Weighted CO attainment (across all exams)
    3. PO attainment (Σ CO×level / Σ level)
    4. PSO attainment
    5. CO-PO correlation matrix
    6. Summary statistics
    """
    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="po")
    svc = AttainmentService(session)
    result = await svc.run_full_attainment_pipeline(course_id, resolved_program_id, threshold_pct)
    result["program_id"] = resolved_program_id
    result["requested_program_id"] = program_id
    logger.info(f"Full attainment pipeline complete for course {course_id}")
    return result


@router.post("/attainment/full-pipeline/async", summary="Queue full attainment pipeline via Celery")
async def queue_full_attainment_pipeline(
    course_id:     str   = Query(...),
    program_id:    Optional[str] = Query(None),
    threshold_pct: float = Query(0.40, description="CO attainment threshold (0-1)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    resolved_program_id = await _resolve_program_key_for_course(session, course_id, program_id, require="po")
    task = run_full_pipeline_task.delay(course_id, resolved_program_id, threshold_pct)
    logger.info(f"Queued attainment pipeline task {task.id} for course {course_id}")
    return {
        "task_id": task.id,
        "status": "queued",
        "course_id": course_id,
        "program_id": resolved_program_id,
        "requested_program_id": program_id,
        "threshold_pct": threshold_pct,
    }


@router.get("/tasks/{task_id}", summary="Get Celery task status and result")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    task = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": task.status,
    }
    if task.ready():
        if task.successful():
            response["result"] = task.result
        else:
            response["error"] = str(task.result)
    return response


@router.get("/attainment/course/{course_id}", summary="Get attainment summary for a course")
async def get_course_attainment(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    course = await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    summary = await svc.get_course_attainment_summary(course.id)
    # normalise: expose co_attainments under both keys the frontend reads
    co_rows = summary.get("co_attainments", [])
    po_rows = summary.get("po_attainments", [])
    return {
        **summary,
        "attainments": co_rows,
        "co_attainments": co_rows,
        "po_attainments": po_rows,
    }


@router.get("/courses/{course_id}/obe-workflow-v1", summary="Legacy NBA OBE workflow — CO/PO attainment with formulas")
async def get_obe_workflow_v1(
    course_id: str,
    threshold_pct: float = Query(0.40),
    fa_method: str = Query("best_n_of_m"),
    fa_best_n: int = Query(3),
    fa_weight: float = Query(0.40),
    sa_weight: float = Query(0.60),
    direct_weight: float = Query(0.80),
    indirect_weight: float = Query(0.20),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Returns the full NBA-compliant OBE workflow data for the CO Attainment page."""
    course = await _assert_faculty_owns_course(session, current_user, course_id)
    resolved_course_id = course.id
    svc = AttainmentService(session)

    weighted_cos = await svc.calculate_weighted_co_attainments(resolved_course_id, threshold_pct)
    summary_data = await svc.get_course_attainment_summary(resolved_course_id)
    po_rows = summary_data.get("po_attainments", [])

    # Build per-CO rows in the shape the page expects
    co_attainments = []
    for co in weighted_cos:
        direct = co.get("direct_attainment_percentage", 0.0)
        indirect = co.get("indirect_attainment_percentage")
        final = co.get("attainment_percentage", 0.0)
        has_indirect = co.get("has_indirect", False)
        gap = co.get("gap_flag", False)
        level = co.get("attainment_level", "Level 1")

        fa_formula = f"FA = best {fa_best_n} of FA exams, avg × FA weight"
        sa_formula = f"SA = end-term attainment × SA weight"
        direct_formula = f"Direct = FA×{fa_weight} + SA×{sa_weight}"
        final_formula = (
            f"Final = Direct×{direct_weight} + Indirect×{indirect_weight}"
            if has_indirect else f"Final = Direct (no indirect survey data)"
        )

        co_attainments.append({
            "co_code": co.get("co_code") or co.get("code"),
            "co_statement": co.get("co_statement") or co.get("statement"),
            "bloom_level": co.get("bloom_level"),
            "fa_att": round(direct, 1),
            "sa_att": None,
            "direct_att": round(direct, 1),
            "indirect_att": round(indirect, 1) if indirect is not None else None,
            "final_att": round(final, 1),
            "attainment_level": level,
            "attainment_percentage": round(final, 2),
            "gap_flag": gap,
            "has_indirect": has_indirect,
            "target_level": co.get("target_level", 2),
            "status": "CAP Required ✗" if gap else "Attained ✓",
            "cap_action": co.get("gap_action") if gap else None,
            "fa_formula": fa_formula,
            "sa_formula": sa_formula,
            "direct_formula": direct_formula,
            "final_formula": final_formula,
        })

    cos_attained = sum(1 for c in co_attainments if not c["gap_flag"])
    cos_gap = sum(1 for c in co_attainments if c["gap_flag"])
    avg_final = (
        sum(c["final_att"] for c in co_attainments) / len(co_attainments)
        if co_attainments else 0.0
    )

    # Determine overall level
    s = get_settings()
    l3 = getattr(s, "attainment_level_3_threshold", 0.60) * 100
    l2 = getattr(s, "attainment_level_2_threshold", 0.50) * 100
    overall_level = "Level 3" if avg_final >= l3 else ("Level 2" if avg_final >= l2 else "Level 1")

    return {
        "course_id": resolved_course_id,
        "requested_course": course_id,
        "co_attainments": co_attainments,
        "po_attainments": po_rows,
        "config": {
            "threshold_pct": int(threshold_pct * 100),
            "fa_method": fa_method,
            "fa_best_n": fa_best_n,
            "fa_weight": fa_weight,
            "sa_weight": sa_weight,
            "direct_weight": direct_weight,
            "indirect_weight": indirect_weight,
        },
        "nba_formulas": {
            "co_attainment": f"CO_att = (students_cleared / total_students) × 100",
            "fa_blend": f"FA = best {fa_best_n} of FA exams (T1-T5), simple avg",
            "direct_blend": f"Direct = FA×{fa_weight} + SA×{sa_weight}",
            "final_blend": f"Final = Direct×{direct_weight} + Indirect×{indirect_weight} (NBA 80:20)",
            "po_attainment": "PO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)",
        },
        "summary": {
            "total_cos": len(co_attainments),
            "cos_attained": cos_attained,
            "cos_gap": cos_gap,
            "avg_final_attainment": round(avg_final, 2),
            "overall_level": overall_level,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/visualization/{course_id}", summary="Chart-ready JSON for CO/PO/Bloom/Grade charts")
async def get_visualization_data(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Returns data ready for bar charts, pie charts, and distribution graphs."""
    await _assert_faculty_owns_course(session, current_user, course_id)
    from app.core.infrastructure.multi_tier_cache import get_or_compute

    async def _compute_visualization() -> Dict[str, Any]:
        svc = AttainmentService(session)
        return await svc.get_visualization_data(course_id)

    payload, source = await get_or_compute(
        key=f"viz:{course_id}",
        compute_fn=_compute_visualization,
        fresh_ttl=180,
        stale_ttl=600,
    )
    return {"source": source, **payload}


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/reports/generate", summary="Generate and store an OBE report")
async def generate_report(
    course_id:   str = Query(...),
    report_type: str = Query(..., description="co_attainment | po_attainment | student_performance | full"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    matrix_validation = await validate_course_matrix_before_save(session, course_id)
    if not matrix_validation.get("can_save", False):
        raise HTTPException(status_code=400, detail={
            "message": "Cannot generate report because matrix has hard validation errors",
            "errors": matrix_validation.get("errors", []),
            "warnings": matrix_validation.get("warnings", []),
        })

    svc = AttainmentService(session)
    report = await svc.generate_report(course_id, report_type, current_user.id)
    logger.info(f"Report generated: {report.id}")
    return {
        "status": "success",
        "report_id": report.id,
        "generated_at": datetime.utcnow(),
        "matrix_warnings": matrix_validation.get("warnings", []),
    }


@router.get("/reports/status/{job_id}", summary="Get report generation task status")
async def report_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    task = AsyncResult(job_id, app=celery_app)
    return {"job_id": job_id, "status": task.status}


@router.get("/reports/download/{job_id}", summary="Get report job result")
async def report_download_by_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    task = AsyncResult(job_id, app=celery_app)
    if not task.ready():
        raise HTTPException(status_code=409, detail="Report job is not ready")
    if not task.successful():
        raise HTTPException(status_code=500, detail=str(task.result))
    return {"job_id": job_id, "result": task.result}


@router.get("/reports/{course_id}/download", summary="Download OBE report as PDF, Excel, or NBA Excel")
async def download_report(
    course_id: str,
    format: str = Query("pdf", description="pdf or excel or nba"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Download the full OBE attainment report as PDF, Excel, or NBA-format Excel."""
    await _assert_faculty_owns_course(session, current_user, course_id)

    role = _role_value(current_user)
    if format.lower().strip() in {"nba", "nba_excel", "nba-xlsx"} and role not in {"hod", "admin"}:
        raise HTTPException(status_code=403, detail="NBA export is allowed only for HOD/Admin")

    from app.core.infrastructure.multi_tier_cache import get_or_compute

    async def _compute_course_report_payload() -> Dict[str, Any]:
        att_svc = AttainmentService(session)
        summary = await att_svc.get_course_attainment_summary(course_id)
        matrix = await att_svc.get_co_po_matrix(course_id)
        students = await att_svc.get_student_performance(course_id)

        course_result = await session.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one_or_none()

        return {
            **summary,
            "co_po_matrix": matrix,
            "student_performance": students,
            "course_code": getattr(course, "course_code", ""),
            "course_name": getattr(course, "course_name", ""),
        }

    course_data, data_source = await get_or_compute(
        key=f"report_payload:{course_id}",
        compute_fn=_compute_course_report_payload,
        fresh_ttl=300,
        stale_ttl=900,
    )

    from app.services.report_export_service import (
        generate_pdf_report,
        generate_excel_report,
        generate_nba_excel_report,
    )
    fmt = format.lower().strip()
    if fmt in ("pdf",):
        content = generate_pdf_report(course_data)
        media_type = "application/pdf"
        filename = f"obe_report_{course_id}.pdf"
    elif fmt in ("excel", "xlsx"):
        content = generate_excel_report(course_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"obe_report_{course_id}.xlsx"
    elif fmt in ("nba", "nba_excel", "nba-xlsx"):
        content = generate_nba_excel_report(course_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"nba_report_{course_id}.xlsx"
    else:
        raise HTTPException(status_code=400, detail="format must be 'pdf', 'excel', or 'nba'")

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Cache-Source": data_source,
    }
    logger.info(f"Report downloaded: {filename}")
    return Response(content=content, media_type=media_type, headers=headers)


@router.get("/workflows/graphs", summary="List distinct LangGraph workflows")
async def list_workflow_graphs(
    current_user: User = Depends(get_current_user),
):
    from app.agents.langgraph_workflow import get_graph_inventory

    inventory = get_graph_inventory()
    return {
        "status": "ok",
        "framework": "langgraph",
        **inventory,
    }


# ══════════════════════════════════════════════════════════════════════════════
# OBE CHATBOT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/chatbot/message", summary="OBE AI chatbot for conversational OBE assistance")
async def chatbot_message(
    payload: ChatMessage,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    AI-powered OBE chatbot. Supports:
    - Generate COs from syllabus
    - Map CO → PO/PSO
    - Calculate attainment
    - Detect Bloom levels
    - Generate reports
    - Student marks guidance
    - Course information queries
    """
    user_id = str(current_user.id)
    role = _role_value(current_user)
    message_text = (payload.message or payload.text or "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="message or text is required")

    # New deterministic three-message architecture
    if payload.message_number in {1, 2, 3}:
        session_token = payload.session_id or str(uuid.uuid4())
        three_flow = ThreeMessageFlowService(session=session, user_id=user_id, user_role=role)
        response = await three_flow.process_message(
            text=message_text,
            session_id=session_token,
            message_number=payload.message_number,
            course_id=payload.course_id,
        )
        live_state = await three_flow._load_state(session_token)
        from app.agents.langgraph_workflow import _fmt_wizard_status

        response["reply"] = _fmt_wizard_status(response)
        response["session_id"] = response.get("session_id") or session_token

        course_scope_id = (
            live_state.get("course_db_id")
            or response.get("db_course_id")
            or response.get("course_db_id")
            or payload.course_id
        )
        if course_scope_id:
            safe_response = json.loads(json.dumps(response, default=str))
            safe_live_state = json.loads(json.dumps(live_state, default=str))
            await _safe_set_json(
                f"chatbot_state:{current_user.id}:{course_scope_id}",
                {
                    "course_id": course_scope_id,
                    "step": safe_live_state.get("stage") or safe_response.get("status") or "course_info",
                    "session_data": {
                        "session_id": session_token,
                        "workflow_step": safe_response.get("workflow_step"),
                        "status": safe_response.get("status"),
                        "three_flow": safe_response,
                        "live_state": safe_live_state,
                    },
                    "updated_at": _now_iso(),
                },
                ttl_seconds=86400,
            )
        logger.info(f"Chatbot three-flow status={response.get('status')} user={user_id}")
        return response

    if payload.course_id:
        await _assert_faculty_owns_course(session, current_user, payload.course_id)

    # If a CO wizard session is in progress force routing to generate_co_node
    force_node: Optional[str] = None
    if payload.course_id:
        step_key = f"chatbot_state:{user_id}:{payload.course_id}"
        state_payload = await _safe_get_json(step_key)
        active_step = (state_payload or {}).get("step", "course_info")
        if active_step not in ("course_info", "save", None, ""):
            force_node = "generate_co_node"

    from app.services.chatbot_service import ChatbotService
    svc = ChatbotService(session)
    response = await svc.process_message(
        message=message_text,
        course_id=payload.course_id,
        session_id=payload.session_id,
        user_id=user_id,
        force_node=force_node,
    )
    logger.info(f"Chatbot intent={response.get('intent')} user={user_id}")
    return response


@router.post("/chatbot/validate_matrix", summary="Validate CO-PO matrix with hard/soft rules")
async def chatbot_validate_matrix(
    payload: ChatbotValidateMatrixRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)
    state_key = ThreeMessageFlowService._session_key(user_id, payload.session_id)
    state = await _safe_get_json(state_key)

    course_db_id = (state or {}).get("course_db_id")
    if not course_db_id and payload.course_id:
        course_result = await session.execute(
            select(Course).where((Course.id == payload.course_id) | (Course.course_code == payload.course_id))
        )
        found = course_result.scalar_one_or_none()
        course_db_id = found.id if found else None

    if not course_db_id:
        raise HTTPException(status_code=400, detail="Unable to resolve course for matrix validation")

    await _assert_faculty_owns_course(session, current_user, course_db_id)

    co_rows = (await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_db_id).order_by(CourseOutcome.code)
    )).scalars().all()
    cos = [{"id": co.code, "statement": co.statement} for co in co_rows]

    course_result = await session.execute(select(Course).where(Course.id == course_db_id))
    course = course_result.scalar_one_or_none()
    dept_key = f"DEPT:{((course.department or 'General').strip() or 'General').upper()}" if course else "DEPT:GENERAL"

    po_rows = (await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.program == dept_key).order_by(ProgramOutcome.code)
    )).scalars().all()

    if po_rows:
        pos = [{"id": po.code, "statement": po.statement} for po in po_rows]
    else:
        po_ids = sorted({
            key.split("_", 1)[1]
            for key in payload.mapping.keys()
            if isinstance(key, str) and "_" in key
        })
        pos = [{"id": po_id, "statement": po_id} for po_id in po_ids]

    result = validate_matrix(cos=cos, pos=pos, mapping_matrix=payload.mapping)
    return result


@router.get("/chatbot/sessions/{course_id}/state", summary="Get chatbot stepwise state for faculty course")
async def get_chatbot_session_state(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    key = f"chatbot_state:{current_user.id}:{course_id}"
    payload = await _safe_get_json(key)
    if payload:
        return payload
    return {
        "course_id": course_id,
        "step": "course_info",
        "session_data": {},
        "updated_at": _now_iso(),
    }


@router.post("/chatbot/sessions/{course_id}/state", summary="Update chatbot stepwise state for faculty course")
async def update_chatbot_session_state(
    course_id: str,
    step: str = Query(..., description="course_info|syllabus|po_pso_confirm|co_count|generate|review|save"),
    session_data: Dict[str, Any] = Body(default={}),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _assert_faculty_owns_course(session, current_user, course_id)
    key = f"chatbot_state:{current_user.id}:{course_id}"
    current_payload = await _safe_get_json(key) or {
        "course_id": course_id,
        "step": "course_info",
        "session_data": {},
        "updated_at": _now_iso(),
    }
    if step != current_payload.get("step", "course_info"):
        raise HTTPException(
            status_code=409,
            detail="Manual chatbot step changes are disabled. Progress through the guided workflow in order or reset the session.",
        )

    payload = {
        "course_id": course_id,
        "step": current_payload.get("step", "course_info"),
        "session_data": session_data,
        "updated_at": _now_iso(),
    }
    await _safe_set_json(key, payload, ttl_seconds=86400)
    return payload


@router.post("/chatbot/sessions/{course_id}/reset", summary="Reset CO generation wizard back to step 1")
async def reset_chatbot_session(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Clears all step state for this user+course session, restarting the CO generation wizard."""
    await _assert_faculty_owns_course(session, current_user, course_id)
    key = f"chatbot_state:{current_user.id}:{course_id}"
    reset_payload = {
        "course_id": course_id,
        "step": "course_info",
        "session_data": {},
        "updated_at": _now_iso(),
    }
    await _safe_set_json(key, reset_payload, ttl_seconds=86400)
    return {"status": "reset", "course_id": course_id, "step": "course_info"}


@router.post("/files/upload", summary="Upload a file to object storage")
async def files_upload(
    file: UploadFile = File(...),
    bucket: str = Query("obe-uploads"),
    folder: str = Query("uploads"),
    current_user: User = Depends(get_current_user),
):
    from app.core.infrastructure.object_storage_client import upload_bytes

    content = await file.read()
    object_key = f"{folder}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    try:
        key = upload_bytes(content, bucket=bucket, key=object_key, content_type=file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"bucket": bucket, "key": key, "size": len(content)}


@router.post("/files/presigned", summary="Get pre-signed file download URL")
async def files_presigned(
    payload: PresignRequest,
    current_user: User = Depends(get_current_user),
):
    from app.core.infrastructure.object_storage_client import presigned_get_url

    try:
        url = presigned_get_url(payload.bucket, payload.key, payload.expires_in)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"bucket": payload.bucket, "key": payload.key, "url": url}


@router.get("/files/local/{bucket}/{key:path}", summary="Download local fallback file")
async def files_local_download(
    bucket: str,
    key: str,
    current_user: User = Depends(get_current_user),
):
    from app.core.infrastructure.object_storage_client import get_local_file_path

    file_path = get_local_file_path(bucket, key)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path)


@router.post("/search/questions", summary="Search question bank via Elasticsearch")
async def search_questions(
    payload: QuestionSearchRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.core.infrastructure.search_client import search_questions as search_in_index

    try:
        hits = search_in_index(payload.query, payload.size)
        source = "elasticsearch"
    except RuntimeError:
        stmt = (
            select(ExamQuestion)
            .where(ExamQuestion.question_text.ilike(f"%{payload.query}%"))
            .limit(payload.size)
        )
        rows = (await session.execute(stmt)).unique().scalars().all()
        hits = [
            {
                "id": row.id,
                "exam_id": row.exam_id,
                "question_number": row.question_number,
                "question_text": row.question_text,
                "marks": row.marks,
                "bloom_level": str(row.bloom_level.value) if row.bloom_level else None,
                "source": "database",
            }
            for row in rows
        ]
        source = "database"

    return {"query": payload.query, "count": len(hits), "source": source, "hits": hits}


# ══════════════════════════════════════════════════════════════════════════════
# OBE FULL WORKFLOW STATE (NBA formula-transparent endpoint)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/courses/{course_id}/obe-workflow", summary="Full NBA-compliant OBE workflow state with all intermediate values")
async def get_obe_workflow(
    course_id: str,
    threshold_pct: float = Query(0.40, description="CO pass threshold (0.40=40%, 0.50=50%, 0.60=60%)"),
    fa_method: str = Query("best_n_of_m", description="FA method: best_n_of_m | simple_avg | weighted"),
    fa_best_n: int = Query(3, description="N for Best-N-of-M (default 3)"),
    fa_weight: float = Query(0.40, description="FA weight in Direct blend (default 0.40)"),
    sa_weight: float = Query(0.60, description="SA weight in Direct blend (default 0.60)"),
    direct_weight: float = Query(0.80, description="Direct weight in Final blend (default 0.80)"),
    indirect_weight: float = Query(0.20, description="Indirect weight in Final blend (default 0.20)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the complete NBA OBE calculation state for a course with ALL intermediate values:
    - Per-exam CO attainment (threshold-based pass count)
    - FA attainment (Best-N-of-M / simple avg / weighted)
    - SA attainment
    - Direct CO attainment (FA*fa_weight + SA*sa_weight)
    - Indirect CO attainment (from survey Redis data)
    - Final CO attainment (Direct*0.80 + Indirect*0.20)
    - CO level classification (L1/L2/L3) and gap analysis
    - PO/PSO attainment (weighted by mapping level)
    - Full formula strings for each calculation step
    """
    course = await _assert_faculty_owns_course(session, current_user, course_id)
    resolved_course_id = course.id

    # ── Load course, COs, exams ──────────────────────────────────────────────
    course_r = await session.execute(select(Course).where(Course.id == resolved_course_id))
    course = course_r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    cos_r = await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == resolved_course_id).order_by(CourseOutcome.code)
    )
    cos = list(cos_r.scalars().all())

    exams_r = await session.execute(select(Exam).where(Exam.course_id == resolved_course_id).order_by(Exam.created_at))
    exams = list(exams_r.scalars().all())

    from app.modules.attainment_engine.services.attainment_service import AttainmentService, _level, _EXAM_WEIGHTS, _FA_KEYS, _SA_KEYS, _is_fa_exam, _level_thresholds_live
    svc = AttainmentService(session)
    live_thresholds = await _level_thresholds_live()
    l3_pct, l2_pct = live_thresholds  # e.g. (60.0, 50.0)

    # ── Step A: Per-exam CO attainment ───────────────────────────────────────
    _FA_WEIGHTED_KEYS = {"t1": 0.10, "t2": 0.15, "t3": 0.20, "t4": 0.25, "t5": 0.30}
    per_exam_results: List[Dict] = []
    co_exam_matrix: Dict[str, Dict[str, float]] = {co.code: {} for co in cos}
    co_exam_entries: Dict[str, List[Dict[str, Any]]] = {co.code: [] for co in cos}

    for exam in exams:
        etype = str(exam.exam_type.value if hasattr(exam.exam_type, "value") else exam.exam_type).lower().replace("-", "_").replace(" ", "_")
        is_sa = etype in _SA_KEYS
        is_fa = _is_fa_exam(etype)
        exam_weight = _EXAM_WEIGHTS.get(etype, 60.0 if is_sa else 10.0)

        att_list = await svc.calculate_course_outcome_attainments(resolved_course_id, exam.id, threshold_pct)
        exam_entry = {
            "exam_id": exam.id,
            "exam_name": exam.exam_name,
            "exam_type": etype,
            "weight": exam_weight,
            "is_fa": is_fa,
            "is_sa": is_sa,
            "co_attainments": att_list,
            "formula": f"CO_att% = (students_scoring >= {int(threshold_pct*100)}% of CO_max_marks) / total_students × 100",
        }
        per_exam_results.append(exam_entry)
        for att in att_list:
            co_code = att.get("co_code") or att.get("code", "")
            if not co_code or att.get("not_assessed"):
                continue
            att_pct = float(att.get("attainment_percentage", 0.0) or 0.0)
            co_exam_matrix.setdefault(co_code, {})[etype] = att_pct
            co_exam_entries.setdefault(co_code, []).append({
                "exam_type": etype,
                "attainment": att_pct,
                "weight": exam_weight,
                "is_fa": is_fa,
                "is_sa": is_sa,
            })

    # ── Step B: FA attainment per CO ─────────────────────────────────────────
    fa_results: Dict[str, Dict] = {}
    for co in cos:
        entries = co_exam_entries.get(co.code, [])
        fa_entries = [e for e in entries if _is_fa_exam(str(e.get("exam_type", "")))]
        fa_scores_clean = [float(e.get("attainment", 0.0) or 0.0) for e in fa_entries]

        if fa_method == "best_n_of_m" and fa_scores_clean:
            best = sorted(fa_scores_clean, reverse=True)[:fa_best_n]
            fa_att = sum(best) / len(best)
            formula = f"FA = avg(top {fa_best_n} of {len(fa_scores_clean)} FA scores) = avg({', '.join(f'{v:.1f}' for v in best)}) = {fa_att:.2f}%"
        elif fa_method == "weighted" and fa_entries:
            # Prefer explicit T1-T5 weights when available; otherwise use exam weights.
            if all(str(e.get("exam_type", "")) in _FA_WEIGHTED_KEYS for e in fa_entries):
                fa_att = sum(_FA_WEIGHTED_KEYS[str(e.get("exam_type", ""))] * float(e.get("attainment", 0.0) or 0.0) for e in fa_entries)
                formula = "FA = 0.10×T1 + 0.15×T2 + 0.20×T3 + 0.25×T4 + 0.30×T5"
            else:
                total_w = sum(float(e.get("weight", 0.0) or 0.0) for e in fa_entries)
                fa_att = (
                    sum((float(e.get("weight", 0.0) or 0.0) * float(e.get("attainment", 0.0) or 0.0)) for e in fa_entries) / total_w
                ) if total_w > 0 else 0.0
                formula = "FA = Σ(FA_exam_att × exam_weight) / Σ(exam_weight)"
        elif fa_scores_clean:
            fa_att = sum(fa_scores_clean) / len(fa_scores_clean)
            formula = f"FA = ({' + '.join(f'{v:.1f}' for v in fa_scores_clean)}) / {len(fa_scores_clean)} = {fa_att:.2f}%"
        else:
            fa_att = 0.0
            formula = "FA = 0% (no FA exams found)"

        fa_results[co.code] = {"fa_att": round(fa_att, 2), "fa_scores": fa_scores_clean, "formula": formula, "method": fa_method}

    # ── Step C: SA attainment per CO ─────────────────────────────────────────
    sa_results: Dict[str, Dict] = {}
    for co in cos:
        sa_entries = [e for e in co_exam_entries.get(co.code, []) if str(e.get("exam_type", "")) in _SA_KEYS]
        if sa_entries:
            # Use the highest-weight SA exam.
            best_sa = max(sa_entries, key=lambda e: float(e.get("weight", 0.0) or 0.0))
            sa_att = float(best_sa.get("attainment", 0.0) or 0.0)
            sa_key = str(best_sa.get("exam_type", "sa"))
            formula = f"SA = {sa_key}({sa_att:.2f}%)"
        else:
            sa_att = 0.0
            formula = "SA = 0% (no SA/final exam found — using FA only)"
        sa_results[co.code] = {"sa_att": round(sa_att, 2), "formula": formula}

    # ── Step D: Direct CO attainment ─────────────────────────────────────────
    direct_results: Dict[str, Dict] = {}
    _eff_fa_w = fa_weight if sa_results and any(v["sa_att"] > 0 for v in sa_results.values()) else 1.0
    _eff_sa_w = sa_weight if _eff_fa_w < 1.0 else 0.0
    for co in cos:
        fa_v = fa_results[co.code]["fa_att"]
        sa_v = sa_results[co.code]["sa_att"]
        direct = fa_v * _eff_fa_w + sa_v * _eff_sa_w
        formula = f"Direct = FA({fa_v:.2f}%) × {_eff_fa_w} + SA({sa_v:.2f}%) × {_eff_sa_w} = {direct:.2f}%"
        direct_results[co.code] = {"direct_att": round(direct, 2), "fa_att": fa_v, "sa_att": sa_v, "fa_weight": _eff_fa_w, "sa_weight": _eff_sa_w, "formula": formula}

    # ── Step E: Indirect + Final CO attainment ───────────────────────────────
    final_results: List[Dict] = []
    s = get_settings()
    target_level: int = getattr(s, "co_target_level", 2)

    for co in cos:
        indirect_pct = await svc._get_indirect_attainment(resolved_course_id, co.id)
        direct_v = direct_results[co.code]["direct_att"]

        if indirect_pct is not None:
            final = direct_v * direct_weight + indirect_pct * indirect_weight
            final_formula = f"Final = Direct({direct_v:.2f}%) × {direct_weight} + Indirect({indirect_pct:.2f}%) × {indirect_weight} = {final:.2f}%"
            has_indirect = True
        else:
            final = direct_v
            final_formula = f"Final = Direct({direct_v:.2f}%) [Indirect survey not available]"
            has_indirect = False

        achieved_level = _level(final, live_thresholds)
        level_num = {"Level 1": 1, "Level 2": 2, "Level 3": 3}.get(achieved_level, 1)
        gap = level_num < target_level
        # gap_pct = how far below the NBA level threshold the CO is
        target_threshold = l3_pct if target_level == 3 else (l2_pct if target_level == 2 else 40.0)
        gap_pct = max(0.0, target_threshold - final)

        # CAP recommendation based on gap severity
        if gap:
            if gap_pct > 15:
                cap = "Redesign CO statement, change teaching method, add remedial class"
            elif gap_pct > 10:
                cap = "Add more practice problems, increase feedback frequency"
            else:
                cap = "Minor adjustment to question difficulty or marking scheme"
        else:
            cap = None

        final_results.append({
            "co_id": co.id,
            "co_code": co.code,
            "co_statement": co.statement,
            "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
            # All intermediate values
            "fa_att": fa_results[co.code]["fa_att"],
            "fa_formula": fa_results[co.code]["formula"],
            "sa_att": sa_results[co.code]["sa_att"],
            "sa_formula": sa_results[co.code]["formula"],
            "direct_att": direct_results[co.code]["direct_att"],
            "direct_formula": direct_results[co.code]["formula"],
            "indirect_att": round(indirect_pct, 2) if indirect_pct is not None else None,
            "has_indirect": has_indirect,
            "final_att": round(final, 2),
            "final_formula": final_formula,
            "attainment_level": achieved_level,
            "target_level": target_level,
            "target_met": not gap,
            "gap_flag": gap,
            "cap_action": cap,
            "status": "Attained ✓" if not gap else "CAP Required ✗",
        })

    # ── Step F: PO/PSO attainment ────────────────────────────────────────────
    po_attainments = await svc.get_course_attainment_summary(resolved_course_id)
    matrix = await svc.get_co_po_matrix(resolved_course_id)

    # ── Summary ──────────────────────────────────────────────────────────────
    avg_final = sum(r["final_att"] for r in final_results) / max(len(final_results), 1)
    gap_cos = [r for r in final_results if r["gap_flag"]]

    return {
        "course_id": resolved_course_id,
        "requested_course": course_id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "config": {
            "threshold_pct": int(threshold_pct * 100),
            "fa_method": fa_method,
            "fa_best_n": fa_best_n,
            "fa_weight": _eff_fa_w,
            "sa_weight": _eff_sa_w,
            "direct_weight": direct_weight,
            "indirect_weight": indirect_weight,
            "target_level": target_level,
        },
        "nba_formulas": {
            "co_per_exam": "CO_att%(E,CO) = pass_count(students >= threshold×CO_max) / total_students × 100",
            "fa_best_n_of_m": f"FA_CO_att = avg(top {fa_best_n} of M FA scores)",
            "fa_simple_avg": "FA_CO_att = sum(all FA scores) / M",
            "fa_weighted": "FA_CO_att = 0.10×T1 + 0.15×T2 + 0.20×T3 + 0.25×T4 + 0.30×T5",
            "direct": f"Direct_CO_att = FA×{_eff_fa_w} + SA×{_eff_sa_w}",
            "indirect": "Indirect_CO_att = (mean_Likert / 5) × 100",
            "final": f"Final_CO_att = Direct×{direct_weight} + Indirect×{indirect_weight}",
            "po": "Course_PO_att = Σ(Final_CO_att × mapping_weight) / Σ(mapping_weight)",
            "level": f"L3 ≥ {l3_pct:.0f}% | L2 {l2_pct:.0f}–{l3_pct-1:.0f}% | L1 < {l2_pct:.0f}%",
        },
        "per_exam": per_exam_results,
        "co_attainments": final_results,
        "po_attainments": po_attainments.get("po_attainments", []),
        "co_po_matrix": matrix,
        "gap_analysis": {
            "cos_below_target": gap_cos,
            "total_gap_cos": len(gap_cos),
            "action_required": len(gap_cos) > 0,
        },
        "summary": {
            "total_cos": len(final_results),
            "cos_attained": len(final_results) - len(gap_cos),
            "cos_gap": len(gap_cos),
            "avg_final_attainment": round(avg_final, 2),
            "overall_level": _level(avg_final),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/health", summary="Server health check")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow(), "service": "OBE-API"}