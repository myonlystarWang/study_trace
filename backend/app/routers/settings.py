from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models import Subject
from backend.app.schemas import SubjectOut, SubjectCreate
from backend.app.auth import verify_pin, change_pin

router = APIRouter(prefix="/api/settings", tags=["系统设置与门禁"])


class PinVerifyIn(BaseModel):
    pin: str


class PinChangeIn(BaseModel):
    old_pin: str
    new_pin: str


@router.get("/subjects", response_model=List[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    """获取所有学科列表"""
    return db.query(Subject).order_by(Subject.sort_order.asc()).all()


@router.post("/subjects", response_model=SubjectOut)
def create_subject(sub_in: SubjectCreate, db: Session = Depends(get_db)):
    """新增或更新学科"""
    existing = db.query(Subject).filter(Subject.name == sub_in.name).first()
    if existing:
        existing.full_score = sub_in.full_score
        existing.sort_order = sub_in.sort_order
        db.commit()
        db.refresh(existing)
        return existing

    sub = Subject(
        name=sub_in.name,
        full_score=sub_in.full_score,
        sort_order=sub_in.sort_order,
        is_default=sub_in.is_default
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/verify-pin")
def api_verify_pin(body: PinVerifyIn, db: Session = Depends(get_db)):
    """校验家长端进入 PIN 口令"""
    verify_pin(body.pin, db)
    return {"status": "ok", "message": "口令校验成功"}


@router.put("/pin")
def api_change_pin(body: PinChangeIn, db: Session = Depends(get_db)):
    """修改家长端进入 PIN 口令"""
    change_pin(body.old_pin, body.new_pin, db)
    return {"status": "ok", "message": "口令已成功修改"}
