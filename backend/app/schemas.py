from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# 通用响应契约
class HealthOut(BaseModel):
    status: str
    project: str
    version: str


# 学生契约
class StudentBase(BaseModel):
    name: str
    grade: Optional[str] = "初一"
    avatar: Optional[str] = None


class StudentCreate(StudentBase):
    pass


class StudentOut(StudentBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 学科契约
class SubjectBase(BaseModel):
    name: str
    full_score: float = 100.0
    is_default: bool = True
    sort_order: int = 0


class SubjectCreate(SubjectBase):
    pass


class SubjectOut(SubjectBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 作业契约（为 M1 预置）
class HomeworkItemBase(BaseModel):
    student_id: Optional[int] = 1
    subject_id: int
    date: date
    content: str
    is_completed: bool = False
    source_image_path: Optional[str] = None


class HomeworkItemCreate(HomeworkItemBase):
    pass


class HomeworkItemUpdate(BaseModel):
    is_completed: Optional[bool] = None
    content: Optional[str] = None


class HomeworkItemOut(HomeworkItemBase):
    id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 错题契约（为 M1 预置）
class MistakeRecordBase(BaseModel):
    student_id: Optional[int] = 1
    subject_id: int
    source_type: Optional[str] = "homework"  # homework / exam / exercise
    source_reference: Optional[str] = None
    original_image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    cropped_diagram_path: Optional[str] = None
    extracted_text: Optional[str] = None
    error_type: Optional[str] = None
    mastery_status: str = "未掌握"  # 未掌握 / 待复习 / 已掌握
    next_review_date: Optional[date] = None


class MistakeRecordCreate(MistakeRecordBase):
    pass


class MistakeRecordOut(MistakeRecordBase):
    id: int
    review_count: int = 0
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 错题复习流水契约（为 M1 预置）
class MistakeReviewCreate(BaseModel):
    mistake_id: int
    result: str  # remembered / forgotten


class MistakeReviewOut(BaseModel):
    id: int
    mistake_id: int
    reviewed_at: datetime
    result: str
    next_review_date: Optional[date]
    model_config = ConfigDict(from_attributes=True)


# OCR 识别契约（为 M2 预置）
class OcrLineOut(BaseModel):
    text: str
    confidence: float
    box: List[List[int]] = []


class OcrResultOut(BaseModel):
    lines: List[OcrLineOut]
    text: str
    confidence: float
    engine: str
    cost_ms: int


class OcrTaskOut(BaseModel):
    task_id: str
    status: str  # pending / processing / succeeded / failed
    progress: int = 0
    engine: Optional[str] = None
    result: Optional[OcrResultOut] = None
    error: Optional[str] = None
    created_at: float
    cost_ms: Optional[int] = None


class OcrEnginesOut(BaseModel):
    default: str
    detail: dict
