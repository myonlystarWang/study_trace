from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from backend.app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="初一同学")
    grade = Column(String(20), default="初一")
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(30), unique=True, nullable=False)
    full_score = Column(Float, default=100.0)
    is_default = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
