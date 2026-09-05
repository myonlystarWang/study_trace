from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    slot = Column(String(20), nullable=False)  # "17:30", "19:30", "21:00"
    channel = Column(String(30), nullable=False)  # "webhook", "bark", "webpush"
    sent_at = Column(DateTime, default=datetime.now)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_label = Column(String(100), nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
