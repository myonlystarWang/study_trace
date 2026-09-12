from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.config import UPLOADS_DIR
from backend.app.database import get_db
from backend.app.models import MistakeRecord, MistakeReview, Subject
from backend.app.schemas import (
    MistakeRecordCreate, MistakeRecordOut, MistakeReviewCreate, MistakeReviewOut, MistakeBatchDeleteIn
)
from backend.app.utils.image_handler import save_image_bytes

router = APIRouter(prefix="/api/mistakes", tags=["错题本"])

# 错题记录上所有指向图片的三列，删除错题或删图时据此判断文件是否还被引用
IMAGE_FIELDS = ("original_image_path", "thumbnail_path", "cropped_diagram_path")
# 允许显式传 null 清空的字段（其余字段传 null 视为"未修改"）
NULLABLE_IMAGE_FIELDS = set(IMAGE_FIELDS)

# kind -> 该 kind 对应的字段集合
IMAGE_KIND_FIELDS = {
    "question": ("original_image_path", "thumbnail_path"),
    "diagram": ("cropped_diagram_path",),
}


def _resolve_upload_file(rel_path: Optional[str]) -> Optional[Path]:
    """把 /uploads/... 形式的相对 URL 解析为磁盘绝对路径（越界路径一律拒绝）。

    以 UPLOADS_DIR 为根（它可被 STUDYTRACE_UPLOADS_DIR 重定向到测试目录），
    不再硬拼 DATA_DIR/"uploads"，否则测试隔离下永远找不到文件。
    """
    if not rel_path or not rel_path.startswith("/uploads/"):
        return None
    candidate = (UPLOADS_DIR / rel_path[len("/uploads/"):]).resolve()
    uploads_root = UPLOADS_DIR.resolve()
    if uploads_root not in candidate.parents:
        return None
    return candidate


def _sibling_paths(abs_path: Path) -> List[Path]:
    """同一 sha256 文件在 originals/ 与 thumbnails/ 下成对存在，删除时要一起带走。"""
    paths = [abs_path]
    parts = list(abs_path.parts)
    if "originals" in parts:
        idx = parts.index("originals")
        twin = Path(*parts[:idx], "thumbnails", *parts[idx + 1:])
        paths.append(twin)
    elif "thumbnails" in parts:
        idx = parts.index("thumbnails")
        twin = Path(*parts[:idx], "originals", *parts[idx + 1:])
        paths.append(twin)
    return paths


def _purge_image_if_unreferenced(db: Session, rel_path: Optional[str]) -> bool:
    """仅当没有任何错题记录再引用该图片时，才删除磁盘文件。返回是否真的删除。"""
    if not rel_path:
        return False
    still_used = db.query(MistakeRecord).filter(
        or_(*[getattr(MistakeRecord, f) == rel_path for f in IMAGE_FIELDS])
    ).first()
    if still_used:
        return False

    abs_path = _resolve_upload_file(rel_path)
    if not abs_path:
        return False
    if not abs_path.exists():
        return False

    # 仅当同源文件确实已无引用，才删对应缩略图；逐个再查一次，避免误删仍被引用的缩略图
    removed = False
    for path in _sibling_paths(abs_path):
        if not path.exists():
            continue
        # 计算该文件的相对 URL，再用同样的引用检查兜一次
        try:
            rel = "/uploads/" + path.relative_to(UPLOADS_DIR).as_posix()
        except ValueError:
            continue
        referenced = db.query(MistakeRecord).filter(
            or_(*[getattr(MistakeRecord, f) == rel for f in IMAGE_FIELDS])
        ).first()
        if referenced:
            continue
        try:
            path.unlink()
            removed = True
        except OSError:
            pass
    return removed


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """上传图片接口：支持自动 EXIF 矫正、Pillow 压缩与缩略图生成"""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件内容为空")
    
    sha256, orig_url, thumb_url = save_image_bytes(content, file.filename or "image.jpg")
    storage_key = orig_url.lstrip("/").removeprefix("uploads/")
    return {
        "sha256": sha256,
        "original_url": orig_url,
        "thumbnail_url": thumb_url,
        "storage_key": storage_key
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
            "answer": r.answer,
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
        answer=item.answer,
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
        "answer": r.answer,
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

    # 图片类字段允许显式传 null 以清空（清空后由 /image 接口负责删磁盘文件）；
    # 其余文本字段沿用"非 None 才更新"，避免前端漏传字段被误清空。
    for field in [
        "extracted_text",
        "answer",
        "error_type",
        "cropped_diagram_path",
        "mastery_status",
        "source_reference",
        "subject_id",
        "original_image_path",
        "thumbnail_path",
    ]:
        if field not in item_in:
            continue
        if item_in[field] is None and field not in NULLABLE_IMAGE_FIELDS:
            continue
        setattr(r, field, item_in[field])

    db.commit()
    db.refresh(r)
    return r


@router.delete("/{mistake_id}/image/{kind}")
def delete_mistake_image(mistake_id: int, kind: str, db: Session = Depends(get_db)):
    """删除错题的图片。

    kind=question → 题干图（同时清空 thumbnail_path）
    kind=diagram  → 题目配图（数轴/几何图等）

    记录字段置空后，仅当磁盘文件不再被任何错题引用时才真正删除，避免误删共享文件。
    """
    if kind not in IMAGE_KIND_FIELDS:
        raise HTTPException(status_code=400, detail="kind 仅支持 question 或 diagram")

    r = db.query(MistakeRecord).filter(MistakeRecord.id == mistake_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="未找到该错题记录")

    cleared_paths: List[str] = []
    for field in IMAGE_KIND_FIELDS[kind]:
        current = getattr(r, field)
        if current:
            cleared_paths.append(current)
        setattr(r, field, None)
    db.commit()

    purged = sum(1 for p in cleared_paths if _purge_image_if_unreferenced(db, p))
    return {
        "status": "ok",
        "kind": kind,
        "cleared": cleared_paths,
        "files_deleted": purged,
        "message": "图片已删除" if cleared_paths else "该记录本就没有此图片",
    }


@router.delete("/{mistake_id}")
def delete_mistake(mistake_id: int, db: Session = Depends(get_db)):
    r = db.query(MistakeRecord).filter(MistakeRecord.id == mistake_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="未找到该错题记录")

    image_paths = [getattr(r, f) for f in IMAGE_FIELDS if getattr(r, f)]
    db.delete(r)
    db.commit()

    # 记录已删，再判断文件是否还被其它记录引用，未被引用则清理
    for path in image_paths:
        _purge_image_if_unreferenced(db, path)

    return {"status": "ok", "message": "错题已删除"}


@router.post("/batch-delete")
def batch_delete_mistakes(payload: MistakeBatchDeleteIn, db: Session = Depends(get_db)):
    if not payload.ids:
        return {"status": "ok", "deleted_count": 0}
    # 先清理关联的复习流水
    db.query(MistakeReview).filter(MistakeReview.mistake_id.in_(payload.ids)).delete(synchronize_session=False)
    # 批量清理错题记录
    count = db.query(MistakeRecord).filter(MistakeRecord.id.in_(payload.ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok", "deleted_count": count}


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
