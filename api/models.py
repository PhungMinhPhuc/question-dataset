from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str  # "student" | "teacher"
    organization: Optional[str] = None  # chỉ dành cho teacher
    school: Optional[str] = None  # chỉ dành cho student

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: int
    email: str

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    school: Optional[str] = None
    password: Optional[str] = None


# ── Questions ────────────────────────────────────────────────────────────────

class QuestionFilter(BaseModel):
    subject: Optional[str] = None
    grade: Optional[int] = None
    chapter: Optional[str] = None
    lesson: Optional[str] = None
    question_type: Optional[str] = None  # mc, tf, sa, oe, st
    complexity: Optional[int] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20

class QuestionDetailUpdate(BaseModel):
    id: int
    content: Optional[str] = None
    is_correct: Optional[bool] = None

class QuestionUpdateRequest(BaseModel):
    subject: Optional[str] = None
    grade: Optional[int] = None
    chapter: Optional[str] = None
    lesson: Optional[str] = None
    complexity: Optional[int] = None
    content: Optional[str] = None
    solution: Optional[str] = None
    details: Optional[List[QuestionDetailUpdate]] = None


# ── Upload ───────────────────────────────────────────────────────────────────

class UploadConfirmRequest(BaseModel):
    teacher_id: int
    subject: str
    grade: int
    data: List[Any]  # danh sách parsed question dicts


# ── Classes ──────────────────────────────────────────────────────────────────

class ClassCreateRequest(BaseModel):
    class_name: str
    description: Optional[str] = None

class JoinClassRequest(BaseModel):
    class_public_id: str

class AddStudentRequest(BaseModel):
    identifier: str


# ── Contests ─────────────────────────────────────────────────────────────────

class ContestCreateRequest(BaseModel):
    class_id: Optional[int] = None
    title: str
    time_limit: int  # phút
    scoring_config: dict
    question_ids: List[int]
    status: str = "inactive"

class ContestSubmitRequest(BaseModel):
    contest_result_id: int
    answers: List[dict]  # [{question_id, student_choice, option_display_order}]

class StartContestRequest(BaseModel):
    student_id: Optional[int] = None  # None nếu thi không cần đăng nhập
    guest_name: Optional[str] = None
