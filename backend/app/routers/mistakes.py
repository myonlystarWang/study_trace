from datetime import date, datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.database import get_db
from backend.app.models import MistakeRecord, MistakeReview, Subject
from backend.app.schemas import (
    MistakeRecordCreate, MistakeRecordOut, MistakeReviewCreate, MistakeReviewOut
)
from backend.app.utils.image_handler import save_image_bytes

router = APIRouter(prefix="/api/mistakes", tags=["错题本"])


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """上传图片接口：支持自动 EXIF 矫正、Pillow 压缩与缩略图生成"""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件内容为空")
    
    sha256, orig_url, thumb_url = save_image_bytes(content, file.filename or "image.jpg")
    return {
        "sha256": sha256,
        "original_url": orig_url,
        "thumbnail_url": thumb_url
    }


@router.get("")
def get_mistakes(
    subject_id: Optional[int] = None,
    mastery_status: Optional[str] = None,
    source_type: Optional[str] = None,
    ebbinghaus_today: Optional[bool] = False,
    search: Optional[str] = None,
    student_id: int = 1,
    db: Session = Depends(get_db)
):
    query = db.query(MistakeRecord).filter(MistakeRecord.student_id == student_id)

    if subject_id:
        query = query.filter(MistakeRecord.subject_id == subject_id)
    if mastery_status:
        query = query.filter(MistakeRecord.mastery_status == mastery_status)
    if source_type:
        query = query.filter(MistakeRecord.source_type == source_type)
    if ebbinghaus_today:
        today = date.today()
        query = query.filter(
            MistakeRecord.next_review_date <= today,
            MistakeRecord.mastery_status != "已掌握"
        )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                MistakeRecord.extracted_text.like(pattern),
                MistakeRecord.source_reference.like(pattern)
            )
        )

    records = query.order_by(MistakeRecord.id.desc()).all()
    
    # 包装学科名称及统计
    results = []
    for r in records:
        results.append({
            "id": r.id,
            "student_id": r.student_id,
            "subject_id": r.subject_id,
            "subject_name": r.subject.name if r.subject else "",
            "source_type": r.source_type,
            "source_reference": r.source_reference,
            "original_image_path": r.original_image_path,
            "thumbnail_path": r.thumbnail_path,
            "cropped_diagram_path": r.cropped_diagram_path,
            "extracted_text": r.extracted_text,
            "error_type": r.error_type,
            "mastery_status": r.mastery_status,
            "review_count": r.review_count,
            "last_reviewed_at": r.last_reviewed_at,
            "next_review_date": r.next_review_date,
            "created_at": r.created_at,
        })
    return results


@router.post("", response_model=MistakeRecordOut)
def create_mistake(item: MistakeRecordCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == item.subject_id).first()
    if not subject:
        raise HTTPException(status_code=400, detail="未找到该学科")

    # 新录入错题，默认艾宾浩斯第 1 次复习设在明天 (today + 1)
    next_date = item.next_review_date or (date.today() + timedelta(days=1))

    record = MistakeRecord(
        student_id=item.student_id or 1,
        subject_id=item.subject_id,
        source_type=item.source_type or "homework",
        source_reference=item.source_reference,
        original_image_path=item.original_image_path,
        thumbnail_path=item.thumbnail_path or item.original_image_path,
        cropped_diagram_path=item.cropped_diagram_path,
        extracted_text=item.extracted_text,
        error_type=item.error_type,
        mastery_status=item.mastery_status or "未掌握",
        next_review_date=next_date,
        review_count=0
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{mistake_id}")
def get_mistake_detail(mistake_id: int, db: Session = Depends(get_db)):
    r = db.query(MistakeRecord).filter(MistakeRecord.id == mistake_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="未找到该错题记录")

    reviews = [
        {
            "id": rev.id,
            "reviewed_at": rev.reviewed_at,
            "result": rev.result,
            "next_review_date": rev.next_review_date
        } for rev in r.reviews
    ]

    return {
        "id": r.id,
        "student_id": r.student_id,
        "subject_id": r.subject_id,
        "subject_name": r.subject.name if r.subject else "",
        "source_type": r.source_type,
        "source_reference": r.source_reference,
        "original_image_path": r.original_image_path,
        "thumbnail_path": r.thumbnail_path,
        "cropped_diagram_path": r.cropped_diagram_path,
        "extracted_text": r.extracted_text,
        "error_type": r.error_type,
        "mastery_status": r.mastery_status,
        "review_count": r.review_count,
        "last_reviewed_at": r.last_reviewed_at,
        "next_review_date": r.next_review_date,
        "created_at": r.created_at,
        "reviews": reviews
    }


@router.put("/{mistake_id}")
def update_mistake(mistake_id: int, item_in: dict, db: Session = Depends(get_db)):
    r = db.query(MistakeRecord).filter(MistakeRecord.id == mistake_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="未找到该错题记录")

    for field in ["extracted_text", "error_type", "cropped_diagram_path", "mastery_status", "source_reference"]:
        if field in item_in and item_in[field] is not None:
            setattr(r, field, item_in[field])

    db.commit()
    db.refresh(r)
    return r


@router.delete("/{mistake_id}")
def delete_mistake(mistake_id: int, db: Session = Depends(get_db)):
    r = db.query(MistakeRecord).filter(MistakeRecord.id == mistake_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="未找到该错题记录")
    db.delete(r)
    db.commit()
    return {"status": "ok", "message": "错题已删除"}


@router.post("/{mistake_id}/review", response_model=MistakeRecordOut)
def record_review(mistake_id: int, review_in: MistakeReviewCreate, db: Session = Depends(get_db)):
    """
    艾宾浩斯状态机流转：
    掌握 (remembered) -> 进阶到第 3/7/15 天，第 4 次掌握即出队标记为「已掌握」；
    未掌握 (forgotten) -> 回退到第 1 天 (today + 1)，标记为「未掌握」。
    """
    r = db.query(MistakeRecord).filter(MistakeRecord.id == mistake_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="未找到该错题记录")

    now = datetime.now()
    today = date.today()

    if review_in.result == "remembered":
        r.review_count += 1
        r.last_reviewed_at = now
        
        # 梯度推进: 1 -> +3 -> +7 -> +15 -> 已掌握出队
        if r.review_count == 1:
            r.next_review_date = today + timedelta(days=3)
            r.mastery_status = "待复习"
        elif r.review_count == 2:
            r.next_review_date = today + timedelta(days=7)
            r.mastery_status = "待复习"
        elif r.review_count == 3:
            r.next_review_date = today + timedelta(days=15)
            r.mastery_status = "待复习"
        else:
            # 达到或超过 4 次掌握，出队
            r.next_review_date = None
            r.mastery_status = "已掌握"
    elif review_in.result == "forgotten":
        # 遗忘则回退到第 1 天，状态重置为未掌握
        r.mastery_status = "未掌握"
        r.next_review_date = today + timedelta(days=1)
        r.last_reviewed_at = now
    else:
        raise HTTPException(status_code=400, detail="无效的复习结果，需为 remembered 或 forgotten")

    # 写入复习流水记录
    log = MistakeReview(
        mistake_id=r.id,
        reviewed_at=now,
        result=review_in.result,
        next_review_date=r.next_review_date
    )
    db.add(log)
    db.commit()
    db.refresh(r)
    return r
