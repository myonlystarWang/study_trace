from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="初一同学")
    grade = Column(String(20), default="初一")
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    homework_items = relationship("HomeworkItem", back_populates="student", cascade="all, delete-orphan")
    mistake_records = relationship("MistakeRecord", back_populates="student", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(30), unique=True, nullable=False)
    full_score = Column(Float, default=100.0)
    is_default = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    homework_items = relationship("HomeworkItem", back_populates="subject")
    mistake_records = relationship("MistakeRecord", back_populates="subject")


class HomeworkItem(Base):
    __tablename__ = "homework_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, default=1, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, default=date.today, index=True)
    content = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    source_image_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    student = relationship("Student", back_populates="homework_items")
    subject = relationship("Subject", back_populates="homework_items")


class MistakeRecord(Base):
    __tablename__ = "mistake_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, default=1, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    source_type = Column(String(30), default="homework", index=True)  # homework / exam / exercise
    source_reference = Column(String(255), nullable=True)  # e.g., "10.12 数学作业第 4 题"
    
    original_image_path = Column(String(255), nullable=True)
    thumbnail_path = Column(String(255), nullable=True)
    cropped_diagram_path = Column(String(255), nullable=True)
    
    extracted_text = Column(Text, nullable=True)
    error_type = Column(String(50), nullable=True)  # 概念模糊 / 粗心大意 / 思路卡壳 / 计算错误
    mastery_status = Column(String(20), default="未掌握", index=True)  # 未掌握 / 待复习 / 已掌握
    
    review_count = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    student = relationship("Student", back_populates="mistake_records")
    subject = relationship("Subject", back_populates="mistake_records")
    reviews = relationship("MistakeReview", back_populates="mistake", cascade="all, delete-orphan", order_by="MistakeReview.reviewed_at.desc()")


class MistakeReview(Base):
    __tablename__ = "mistake_reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mistake_id = Column(Integer, ForeignKey("mistake_records.id"), nullable=False, index=True)
    reviewed_at = Column(DateTime, default=datetime.now)
    result = Column(String(20), nullable=False)  # remembered / forgotten
    next_review_date = Column(Date, nullable=True)

    mistake = relationship("MistakeRecord", back_populates="reviews")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint("date", "slot", "channel", name="uq_notification_date_slot_channel"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    slot = Column(String(20), nullable=False)  # "20:10", "21:10", "21:50", "manual"
    channel = Column(String(30), nullable=False)  # "pushplus", "serverchan", "bark", "webhook", "webpush"
    sent_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_label = Column(String(100), nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False, default="初一错题周末重练卷")
    subtitle = Column(String(100), nullable=True, default="满分: 100分 · 建议用时: 45分钟")
    mistake_ids = Column(Text, nullable=False)  # JSON 数组，如 "[1, 2, 3]"
    sort_by = Column(String(20), default="subject")  # subject / order / random
    space_level = Column(String(20), default="standard")  # compact / standard / spacious
    style_mode = Column(String(20), default="grid")  # grid / lined / blank
    show_error_type = Column(Boolean, default=False)
    estimated_pages = Column(Integer, default=1)
    warnings = Column(Text, nullable=True)  # JSON 数组，如 '["第 1 题内容较长..."]'
    student_name = Column(String(50), nullable=False, default="初一同学")
    status = Column(String(20), default="draft", index=True)  # draft / printed / reviewed
    created_at = Column(DateTime, default=datetime.now, index=True)
