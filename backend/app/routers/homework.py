from datetime import date, datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import HomeworkItem, MistakeRecord, Subject
from backend.app.schemas import HomeworkItemCreate, HomeworkItemUpdate, HomeworkItemOut, MistakeRecordOut

router = APIRouter(prefix="/api/homework", tags=["作业打卡"])


def calculate_streak(student_id: int, db: Session) -> int:
    """
    实时聚合计算连续满打卡天数（Streak）：
    当天所有任务完成计入 streak；当天有未完成但昨天全完成时保持 streak 不断；
    跨月完全通过日期推算保障。
    """
    today = date.today()

    # 获取该学生有作业记录的所有去重日期
    dates_query = db.query(HomeworkItem.date).filter(
        HomeworkItem.student_id == student_id
    ).distinct().order_by(HomeworkItem.date.desc()).all()

    recorded_dates = [d[0] for d in dates_query]
    if not recorded_dates:
        return 0

    # 辅助函数：判断指定日期的作业是否全部完成
    def is_date_fully_completed(check_date: date) -> bool:
        items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == check_date
        ).all()
        if not items:
            return False
        return all(item.is_completed for item in items)

    streak = 0
    current_check = today

    # 1. 检查今日是否已完成
    today_items = db.query(HomeworkItem).filter(
        HomeworkItem.student_id == student_id,
        HomeworkItem.date == today
    ).all()

    if today_items and all(item.is_completed for item in today_items):
        streak += 1
        current_check = today - timedelta(days=1)
    else:
        # 今日还未全完成，检查昨日
        yesterday = today - timedelta(days=1)
        if is_date_fully_completed(yesterday):
            # 昨日完成了，从昨天开始往前倒推
            current_check = yesterday
        else:
            # 昨天都没完成，streak 为 0
            return 0

    # 2. 依次往前追溯前一天
    while True:
        if is_date_fully_completed(current_check):
            # 如果今日已经加过 1 且此时 current_check 就是 yesterday，避免重复加
            if current_check != today or streak == 0:
                streak += 1
            current_check -= timedelta(days=1)
        else:
            break

    return streak


@router.get("")
def get_homework_list(
    target_date: Optional[date] = Query(default=None, alias="date"),
    student_id: int = 1,
    db: Session = Depends(get_db)
):
    query_date = target_date or date.today()
    items = db.query(HomeworkItem).filter(
        HomeworkItem.student_id == student_id,
        HomeworkItem.date == query_date
    ).order_by(HomeworkItem.id.asc()).all()

    total = len(items)
    completed = sum(1 for item in items if item.is_completed)
    rate = int((completed / total) * 100) if total > 0 else 0
    streak = calculate_streak(student_id, db)

    # 包装学科名称输出
    items_out = []
    for item in items:
        item_dict = {
            "id": item.id,
            "student_id": item.student_id,
            "subject_id": item.subject_id,
            "subject_name": item.subject.name if item.subject else "",
            "date": item.date,
            "content": item.content,
            "is_completed": item.is_completed,
            "completed_at": item.completed_at,
            "source_image_path": item.source_image_path,
            "created_at": item.created_at,
        }
        items_out.append(item_dict)

    return {
        "date": query_date,
        "total": total,
        "completed": completed,
        "rate": rate,
        "streak": streak,
        "items": items_out
    }


@router.post("", response_model=HomeworkItemOut)
def create_homework(item: HomeworkItemCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == item.subject_id).first()
    if not subject:
        raise HTTPException(status_code=400, detail="未找到该学科")

    hw = HomeworkItem(
        student_id=item.student_id or 1,
        subject_id=item.subject_id,
        date=item.date,
        content=item.content,
        is_completed=item.is_completed,
        source_image_path=item.source_image_path,
    )
    if hw.is_completed:
        hw.completed_at = datetime.now()

    db.add(hw)
    db.commit()
    db.refresh(hw)
    return hw


@router.put("/{homework_id}")
def update_homework(
    homework_id: int,
    item_in: HomeworkItemUpdate,
    db: Session = Depends(get_db)
):
    hw = db.query(HomeworkItem).filter(HomeworkItem.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="未找到该作业条目")

    if item_in.is_completed is not None:
        hw.is_completed = item_in.is_completed
        hw.completed_at = datetime.now() if item_in.is_completed else None

    if item_in.content is not None:
        hw.content = item_in.content

    db.commit()
    db.refresh(hw)
    return hw


@router.delete("/{homework_id}")
def delete_homework(homework_id: int, db: Session = Depends(get_db)):
    hw = db.query(HomeworkItem).filter(HomeworkItem.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="未找到该作业条目")
    db.delete(hw)
    db.commit()
    return {"status": "ok", "message": "删除成功"}


@router.post("/{homework_id}/to-mistake", response_model=MistakeRecordOut)
def convert_to_mistake(homework_id: int, db: Session = Depends(get_db)):
    """一键转错题：从作业条目继承学科与来源说明，自动创建错题本草稿"""
    hw = db.query(HomeworkItem).filter(HomeworkItem.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="未找到该作业条目")

    subject_name = hw.subject.name if hw.subject else "学科"
    source_ref = f"{hw.date.strftime('%m月%d日')} {subject_name}作业：{hw.content[:40]}"

    mistake = MistakeRecord(
        student_id=hw.student_id,
        subject_id=hw.subject_id,
        source_type="homework",
        source_reference=source_ref,
        original_image_path=hw.source_image_path,
        thumbnail_path=hw.source_image_path,
        extracted_text=hw.content,
        mastery_status="未掌握",
        next_review_date=date.today() + timedelta(days=1),
    )
    db.add(mistake)
    db.commit()
    db.refresh(mistake)
    return mistake
