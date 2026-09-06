from datetime import datetime, date
from typing import Optional, List, Dict
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


# M3 提醒与通知契约
class NotificationConfig(BaseModel):
    enabled_channels: List[str] = ["pushplus"]
    pushplus_token: Optional[str] = ""
    serverchan_key: Optional[str] = ""
    bark_key: Optional[str] = ""
    webhook_url: Optional[str] = ""
    reminder_slots: List[str] = ["20:10", "21:10", "21:50"]


class NotificationTestIn(BaseModel):
    channel: str  # pushplus, serverchan, bark, webhook
    target: Optional[str] = None  # 临时测试用的 Token / Key / URL，若未传则用持久化的配置


class NotificationResultOut(BaseModel):
    channel: str
    success: bool
    message: str


class NotificationSendOut(BaseModel):
    success: bool
    details: Dict[str, NotificationResultOut]
    message: Optional[str] = None


# M3 月度作业打卡日历契约
class CalendarDayStatus(BaseModel):
    date: str  # YYYY-MM-DD
    total: int
    completed: int
    status: str  # green (100%), yellow (部分), red (0%), gray (无作业)


class MonthlyCalendarOut(BaseModel):
    month: str  # YYYY-MM
    days: List[CalendarDayStatus]


# M4 A4 周末重练卷契约
class PaperCandidateOut(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    extracted_text: Optional[str] = None
    original_image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error_type: Optional[str] = None
    mastery_status: str
    review_count: int
    next_review_date: Optional[date] = None
    created_at: datetime
    is_this_week: bool = False
    is_ebbinghaus: bool = False
    is_unmastered: bool = False
    model_config = ConfigDict(from_attributes=True)


class PaperComposeIn(BaseModel):
    mistake_ids: List[int]
    title: str = "初一错题周末重练卷"
    subtitle: Optional[str] = "满分: 100分 · 建议用时: 45分钟"
    sort_by: str = "subject"  # subject / order / random
    space_level: str = "standard"  # compact / standard / spacious
    style_mode: str = "grid"  # grid / lined / blank
    show_error_type: bool = False


class PaperQuestionOut(BaseModel):
    id: int  # mistake_id
    order_num: int
    subject_id: int
    subject_name: str
    extracted_text: Optional[str] = None
    original_image_path: Optional[str] = None
    error_type: Optional[str] = None
    space_mm: int = 45
    is_oversized: bool = False


class PaperComposeOut(BaseModel):
    paper_id: int
    title: str
    subtitle: Optional[str] = None
    student_name: str
    sort_by: str = "subject"
    space_level: str = "standard"
    style_mode: str = "grid"
    show_error_type: bool = False
    questions: List[PaperQuestionOut]
    total_questions: int
    estimated_pages: int
    warnings: List[str] = []
    status: str = "draft"
    created_at: datetime


class PaperBatchReviewItem(BaseModel):
    mistake_id: int
    result: str  # remembered / forgotten


class PaperBatchReviewIn(BaseModel):
    reviews: List[PaperBatchReviewItem]


class PaperBatchReviewFailedItem(BaseModel):
    mistake_id: int
    reason: str


class PaperBatchReviewOut(BaseModel):
    paper_id: int
    success: List[int]
    failed: List[PaperBatchReviewFailedItem] = []
    message: str


class PaperHistoryOut(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    student_name: str
    total_questions: int
    estimated_pages: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
