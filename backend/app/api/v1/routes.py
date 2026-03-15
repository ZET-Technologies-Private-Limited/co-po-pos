"""
OBE System – Complete API Routes
All routes implement real OBE algorithms with no mocks.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, delete, func, and_
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
    result = await session.execute(
        select(User).where(User.username == employee_id, User.email == email)
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


async def _get_ay_configs() -> List[Dict[str, Any]]:
    cached = await _safe_get_json("faculty:ay_configs")
    if cached and isinstance(cached.get("items"), list):
        return cached["items"]
    return []


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


async def _assert_faculty_owns_course(session: AsyncSession, user: User, course_id: str) -> None:
    if _role_value(user) != "faculty":
        return

    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if str(course.created_by) != str(user.id):
        raise HTTPException(status_code=403, detail="Faculty can access only own courses")


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


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/auth/register", response_model=TokenResponse, summary="Register a new user")
async def register(payload: UserRegister, session: AsyncSession = Depends(get_session)):
    svc = AuthService(session)
    try:
        user = await svc.register_user(
            username=payload.username, email=payload.email, password=payload.password,
            full_name=payload.full_name, role=payload.role or "faculty",
            department=getattr(payload, "department", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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
    return {
        "status": "otp_sent",
        "email": str(payload.email),
        "expires_in_seconds": _seconds_remaining(issued["expires_at"]),
        "resend_in_seconds": _seconds_remaining(issued["resend_after"]),
    }


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
    cached = await get_json("obe:thresholds")
    if cached:
        return {"level2": cached.get("level2", 0.6), "level3": cached.get("level3", 0.7)}
    s = get_settings()
    return {
        "level2": getattr(s, "attainment_level_2_threshold", 0.6),
        "level3": getattr(s, "attainment_level_3_threshold", 0.7),
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
    if level2 is not None and not (0 <= level2 <= 1):
        raise HTTPException(status_code=400, detail="level2 must be between 0 and 1")
    if level3 is not None and not (0 <= level3 <= 1):
        raise HTTPException(status_code=400, detail="level3 must be between 0 and 1")
    current = await get_json("obe:thresholds") or {}
    if level2 is not None:
        current["level2"] = float(level2)
    if level3 is not None:
        current["level3"] = float(level3)
    await set_json("obe:thresholds", current)
    return {"status": "saved", "thresholds": current}


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
            "userId": str(r.user_id) if r.user_id else "",
            "action": r.action or "",
            "ip": r.ip_address or "",
        }
        for r in rows
    ]


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
    if role != "faculty":
        raise HTTPException(status_code=403, detail="Faculty dashboard is available only for faculty role")

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
                "action_link": f"/faculty/course/{course.id}/marks/{str(ex.exam_type.value if hasattr(ex.exam_type, 'value') else ex.exam_type)}",
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
                    "action_link": f"/faculty/course/{course.id}/marks/{str(ex.exam_type.value if hasattr(ex.exam_type, 'value') else ex.exam_type)}",
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
    svc = CourseService(session)
    course = await svc.create_course(
        course_code=payload.course_code, course_name=payload.course_name,
        credits=payload.credits, semester=payload.semester,
        description=payload.description, faculty_id=current_user.id,
    )
    logger.info(f"Course created: {course.id}")
    return course


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
    svc = CourseService(session)
    course = await svc.get_course(course_id)
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
    if lock.get("locked"):
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
    if lock.get("locked"):
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
    if lock.get("locked"):
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
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    filename = (file.filename or "").lower()
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

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
            raise HTTPException(status_code=422, detail=f"PDF text extraction failed: {exc}")
    elif filename.endswith(".docx"):
        try:
            import io
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"DOCX text extraction failed: {exc}")
    else:
        raise HTTPException(status_code=415, detail="Unsupported file type. Accepted: .pdf, .docx, .txt")

    text = text[:5000]
    course.syllabus = text
    await session.commit()
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

    # Re-insert PO mappings by code lookup
    # Re-insert PO mappings by code lookup (deduplicated — one mapping per code)
    if payload.po_codes:
        po_filter = ProgramOutcome.code.in_(payload.po_codes)
        if payload.program_id:
            po_filter = (ProgramOutcome.code.in_(payload.po_codes)) & (ProgramOutcome.program == payload.program_id)
        po_objs = (await session.execute(select(ProgramOutcome).where(po_filter))).scalars().all()
        seen_po: set = set()
        for po_obj in po_objs:
            if po_obj.code in seen_po:
                continue
            seen_po.add(po_obj.code)
            await session.execute(
                co_po_mapping_table.insert().values(
                    course_outcome_id=co_id,
                    program_outcome_id=po_obj.id,
                    similarity_score=1.0,
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
                    similarity_score=1.0,
                )
            )
            pso_inserted.append(pso_obj.code)

    await session.commit()
    await invalidate_course_report_cache(course_id)
    return {
        "co_id": co_id,
        "po_mappings": po_inserted,
        "pso_mappings": pso_inserted,
        "status": "updated",
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
    if lock.get("locked"):
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
    cos = co_result.scalars().all()
    co_statements_lower = [(co.code, co.statement.lower()) for co in cos]

    import re as _re

    # Parse syllabus into units/topics by detecting unit headers
    unit_pattern = _re.compile(
        r"(?:unit|chapter|module|section|topic)\s*[-:]?\s*\d+[^\n]*|^\d+\.\s+[A-Z][^\n]+",
        _re.IGNORECASE | _re.MULTILINE,
    )
    unit_matches = list(unit_pattern.finditer(syllabus))

    units: List[Dict] = []
    if unit_matches:
        for i, m in enumerate(unit_matches):
            start = m.end()
            end = unit_matches[i + 1].start() if i + 1 < len(unit_matches) else len(syllabus)
            unit_name = m.group(0).strip()
            unit_body = syllabus[start:end].strip()
            units.append({"name": unit_name, "body": unit_body})
    else:
        # No unit headers — treat paragraphs as topics
        paragraphs = [p.strip() for p in syllabus.split("\n\n") if len(p.strip()) > 20]
        for i, para in enumerate(paragraphs[:10], 1):
            units.append({"name": f"Topic {i}", "body": para})

    def _keywords(text: str) -> set:
        words = set(_re.findall(r"\b[a-z]{4,}\b", text.lower()))
        stop = {"will", "able", "student", "students", "course", "this", "that", "with", "from",
                "have", "been", "unit", "chapter", "topic", "section", "module", "each", "also"}
        return words - stop

    coverage_items = []
    covered_count = 0
    for unit in units:
        unit_kw = _keywords(unit["name"] + " " + unit["body"][:400])
        covered_by: List[str] = []
        for co_code, co_stmt in co_statements_lower:
            co_kw = _keywords(co_stmt)
            overlap = len(unit_kw & co_kw)
            # require at least 2 overlapping keywords for coverage
            if overlap >= 2:
                covered_by.append(co_code)
        is_covered = bool(covered_by)
        if is_covered:
            covered_count += 1
        coverage_items.append({
            "unit": unit["name"],
            "is_covered": is_covered,
            "covered_by": covered_by,
            "color": "green" if is_covered else "amber",
        })

    total = len(coverage_items)
    return {
        "course_id": course_id,
        "has_syllabus": True,
        "total_units": total,
        "covered_units": covered_count,
        "uncovered_units": total - covered_count,
        "coverage_pct": round((covered_count / total * 100) if total else 0, 1),
        "units": coverage_items,
    }


# ── F3-29: Export CO list (PDF / CSV) ─────────────────────────────────────────

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
    if lock.get("locked"):
        raise HTTPException(status_code=409, detail="CO generation is locked for this course")

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
    return {
        "total_cos": len(cos_out),
        "course_outcomes": cos_out,
        "co_po_mappings": result["co_po_mappings"],
        "co_pso_mappings": result["co_pso_mappings"],
    }


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
        has_override = bool(q.get("bloom_level") or q.get("co_mapped"))
        if has_override and not (q.get("override_reason") or "").strip():
            raise HTTPException(status_code=400, detail="override_reason is required when overriding BT level or CO mapping")

    svc = QuestionAnalysisService(session)
    created = await svc.add_questions(
        exam_id, prepared_questions, detect_bloom_with_llm=True
    )

    question_meta = []
    for source_q, created_q in zip(prepared_questions, created):
        question_meta.append(
            {
                "question_id": created_q.id,
                "question_number": source_q.get("question_number"),
                "part_label": source_q.get("part_label"),
                "either_or_pair": source_q.get("either_or_pair"),
                "co_mapped": source_q.get("co_mapped") or [],
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
    """
    content = await file.read()
    svc = QuestionAnalysisService(session)
    result = await svc.process_marks_file(exam_id, content, filename=file.filename or "")
    ex_result = await session.execute(select(Exam).where(Exam.id == exam_id))
    exam = ex_result.scalar_one_or_none()
    if exam:
        await invalidate_course_report_cache(exam.course_id)
        await invalidate_exam_preview_cache(exam_id)
    logger.info(f"Marks file uploaded for exam {exam_id}: {result.get('rows_processed',0)} rows")
    return {"exam_id": exam_id, "status": "success", **result}


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


@router.get("/marks/{exam_id}/preview", summary="Live CO attainment preview from Redis cache")
async def marks_preview(
    exam_id: str,
    threshold_pct: float = Query(0.60),
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
    threshold_pct: float = Query(0.60),
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
    program_id: str = Query(...),
    threshold: float = Query(0.3, description="Minimum similarity score (0-1)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Uses Gemini embeddings to compute semantic similarity between COs and POs.
    Creates CO-PO mappings with similarity scores.
    Similarity → mapping level: ≥0.75=3(strong), ≥0.50=2(medium), ≥0.30=1(weak)
    """
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
    svc = SemanticMappingService(session)
    mappings = await svc.auto_map_cos_to_pos(course_id, program_id, threshold=threshold)
    logger.info(f"CO-PO mapping: {len(mappings)} for course {course_id}")
    return {"mappings_created": len(mappings), "mappings": mappings}


@router.post("/map-co-pso", summary="Semantic embedding-based CO → PSO mapping")
async def map_co_to_pso(
    course_id: str = Query(...),
    program_id: str = Query(...),
    threshold: float = Query(0.3),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
    svc = SemanticMappingService(session)
    result = await svc.map_cos_to_psos(session, course_id, program_id, threshold=threshold)
    mappings = result.get("mappings", [])
    logger.info(f"CO-PSO mapping: {len(mappings)} for course {course_id}")
    return {"mappings_created": len(mappings), "mappings": mappings}


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

@router.post("/attainment/calculate-co", summary="Calculate CO attainment (threshold-based) for one exam")
async def calculate_co_attainment(
    course_id: str = Query(...),
    exam_id:   str = Query(...),
    threshold_pct: float = Query(0.60, description="Students must score >= threshold*max_marks to clear CO"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    OBE standard CO attainment:
      threshold_marks = threshold_pct × max_marks_for_CO_questions
      CO_att = (students_cleared / total_students) × 100

    Level 3 ≥ 70%, Level 2 ≥ 60%, Level 1 < 60%
    """
    svc = AttainmentService(session)
    attainments = await svc.calculate_course_outcome_attainments(
        course_id, exam_id, threshold_pct=threshold_pct
    )
    logger.info(f"CO attainment for course {course_id}, exam {exam_id}")
    return {"course_id": course_id, "exam_id": exam_id, "attainments": attainments}


@router.get("/attainment/weighted/{course_id}", summary="Weighted CO attainment across all exams")
async def get_weighted_co_attainment(
    course_id: str,
    threshold_pct: float = Query(0.60),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregates CO attainment from all exams with exam-type weights:
    end_term=60, mid_term=20, T1-T5=5, practical=15, assignment=5
    """
    svc = AttainmentService(session)
    result = await svc.calculate_weighted_co_attainments(course_id, threshold_pct)
    return {"course_id": course_id, "weighted_attainments": result}


@router.post("/attainment/calculate-po", summary="Calculate PO attainment from CO-PO mappings")
async def calculate_po_attainment(
    course_id:  str = Query(...),
    program_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    PO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)
    Requires CO attainments to be computed first.
    """
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    svc = AttainmentService(session)
    attainments = await svc.calculate_program_outcome_attainments(course_id, program_id)
    logger.info(f"PO attainment for course {course_id}")
    return {"course_id": course_id, "program_id": program_id, "attainments": attainments}


@router.post("/attainment/calculate-pso", summary="Calculate PSO attainment from CO-PSO mappings")
async def calculate_pso_attainment(
    course_id:  str = Query(...),
    program_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if _role_value(current_user) == "faculty":
        await _assert_faculty_owns_course(session, current_user, course_id)

    svc = AttainmentService(session)
    attainments = await svc.calculate_pso_attainments(course_id, program_id)
    return {"course_id": course_id, "program_id": program_id, "attainments": attainments}


@router.post("/attainment/full-pipeline", summary="Run the complete OBE attainment pipeline")
async def run_full_attainment_pipeline(
    course_id:     str   = Query(...),
    program_id:    str   = Query(...),
    threshold_pct: float = Query(0.60, description="CO attainment threshold (0-1)"),
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
    svc = AttainmentService(session)
    result = await svc.run_full_attainment_pipeline(course_id, program_id, threshold_pct)
    logger.info(f"Full attainment pipeline complete for course {course_id}")
    return result


@router.post("/attainment/full-pipeline/async", summary="Queue full attainment pipeline via Celery")
async def queue_full_attainment_pipeline(
    course_id:     str   = Query(...),
    program_id:    str   = Query(...),
    threshold_pct: float = Query(0.60, description="CO attainment threshold (0-1)"),
    current_user: User = Depends(get_current_user),
):
    task = run_full_pipeline_task.delay(course_id, program_id, threshold_pct)
    logger.info(f"Queued attainment pipeline task {task.id} for course {course_id}")
    return {
        "task_id": task.id,
        "status": "queued",
        "course_id": course_id,
        "program_id": program_id,
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
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    return await svc.get_course_attainment_summary(course_id)


@router.get("/attainment/matrix/{course_id}", summary="CO × PO correlation matrix")
async def get_co_po_matrix(
    course_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the CO×PO mapping matrix.
    Cell value: 3(strong ≥0.75), 2(medium ≥0.50), 1(weak ≥0.30), 0(none)
    """
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    return await svc.get_co_po_matrix(course_id)


@router.get("/attainment/students/{course_id}", summary="Per-student performance analytics")
async def get_student_performance(
    course_id: str,
    exam_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Students ranked by percentage with per-CO breakdown and letter grade."""
    await _assert_faculty_owns_course(session, current_user, course_id)
    svc = AttainmentService(session)
    data = await svc.get_student_performance(course_id, exam_id)
    return {"course_id": course_id, "count": len(data), "students": data}


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
    svc = AttainmentService(session)
    report = await svc.generate_report(course_id, report_type, current_user.id)
    logger.info(f"Report generated: {report.id}")
    return {"status": "success", "report_id": report.id, "generated_at": datetime.utcnow()}


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
        message=payload.message,
        course_id=payload.course_id,
        session_id=payload.session_id,
        user_id=user_id,
        force_node=force_node,
    )
    logger.info(f"Chatbot intent={response.get('intent')} user={user_id}")
    return response


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
    allowed_steps = {"course_info", "syllabus", "po_pso_confirm", "co_count", "generate", "review", "save"}
    if step not in allowed_steps:
        raise HTTPException(status_code=400, detail="Invalid chatbot step")

    key = f"chatbot_state:{current_user.id}:{course_id}"
    payload = {
        "course_id": course_id,
        "step": step,
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
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/health", summary="Server health check")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow(), "service": "OBE-API"}