import calendar
from datetime import date, datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from backend.app.database import get_db
from backend.app.models import HomeworkItem, MistakeRecord, Subject
from backend.app.schemas import (
    HomeworkItemCreate, HomeworkItemUpdate, HomeworkItemOut, MistakeRecordOut,
    MonthlyCalendarOut, CalendarDayStatus
)

router = APIRouter(prefix="/api/homework", tags=["作业打卡"])


def calculate_streak(student_id: int, db: Session) -> int:
    """
    实时聚合计算连续满打卡天数（Streak）：
    - 平日（周一至周四）：当日所有作业完成计入 streak；
    - 周末（周五至周日）：引入周末宽限期闭环。周五大作业持续顺延至周日晚；
      若当前正值周六且周五作业存在，处于宽限期不中断 streak；
      在周日晚前周五作业全部清零后，周五、周六、周日三天统一计为连续满卡。
    """
    today = date.today()

    # 辅助函数：判断指定日期的作业是否全部完成
    def is_date_fully_completed(check_date: date) -> bool:
        # 1. 检查该日期自身的独立作业
        items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == check_date
        ).all()

        # 2. 周末宽限期处理
        if check_date.weekday() in [5, 6]:  # 周六 (5) 或周日 (6)
            days_to_fri = 1 if check_date.weekday() == 5 else 2
            friday_date = check_date - timedelta(days=days_to_fri)
            fri_items = db.query(HomeworkItem).filter(
                HomeworkItem.student_id == student_id,
                HomeworkItem.date == friday_date
            ).all()

            own_completed = all(it.is_completed for it in items) if items else True
            fri_completed = bool(fri_items and all(it.is_completed for it in fri_items))

            is_active_weekend = (today >= friday_date and today <= friday_date + timedelta(days=2))

            if is_active_weekend:
                # 今天是周六：宽限期生效，只要周六自身任务完成，周五大作业允许继续推进
                if check_date.weekday() == 5:
                    return own_completed
                # 今天是周日：看周五大作业和周日任务是否全数完成
                elif check_date.weekday() == 6:
                    return (fri_completed or not fri_items) and own_completed
            else:
                # 历史过往周末：周五大作业和周末自身任务必须最终全部完成
                return (fri_completed or not fri_items) and own_completed

        if not items:
            return False
        return all(item.is_completed for item in items)

    streak = 0
    current_check = today

    # 1. 检查今日是否已完成
    if is_date_fully_completed(today):
        streak += 1
        current_check = today - timedelta(days=1)
    else:
        # 今日还未全完成，检查昨日
        yesterday = today - timedelta(days=1)
        if is_date_fully_completed(yesterday):
            current_check = yesterday
        else:
            return 0

    # 2. 依次往前追溯前一天
    while True:
        if is_date_fully_completed(current_check):
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
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "source_image_path": item.source_image_path,
            "created_at": item.created_at,
            "is_weekend_rollover": False,
        }
        items_out.append(item_dict)

    # 周末跨天顺延透视：周六 (5) 或周日 (6) 自动透视对应周五的作业
    weekend_rollover = None
    if query_date.weekday() in [5, 6]:
        days_to_fri = 1 if query_date.weekday() == 5 else 2
        friday_date = query_date - timedelta(days=days_to_fri)
        friday_items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == friday_date
        ).order_by(HomeworkItem.id.asc()).all()

        if friday_items:
            fri_completed = sum(1 for it in friday_items if it.is_completed)
            fri_total = len(friday_items)
            fri_rate = int((fri_completed / fri_total) * 100) if fri_total > 0 else 0
            fri_items_out = []
            for it in friday_items:
                fri_items_out.append({
                    "id": it.id,
                    "student_id": it.student_id,
                    "subject_id": it.subject_id,
                    "subject_name": it.subject.name if it.subject else "",
                    "date": it.date,
                    "content": it.content,
                    "is_completed": it.is_completed,
                    "completed_at": it.completed_at.isoformat() if it.completed_at else None,
                    "source_image_path": it.source_image_path,
                    "created_at": it.created_at,
                    "is_weekend_rollover": True,
                })

            weekend_rollover = {
                "source_date": str(friday_date),
                "total": fri_total,
                "completed": fri_completed,
                "rate": fri_rate,
                "items": fri_items_out
            }

    # 如果存在周末顺延作业，则综合计算周末全局总数与完成率
    effective_total = total
    effective_completed = completed
    effective_rate = rate
    if weekend_rollover:
        effective_total += weekend_rollover["total"]
        effective_completed += weekend_rollover["completed"]
        effective_rate = int((effective_completed / effective_total) * 100) if effective_total > 0 else 0

    return {
        "date": query_date,
        "total": effective_total,
        "completed": effective_completed,
        "rate": effective_rate,
        "streak": streak,
        "items": items_out,
        "today_total": total,
        "today_completed": completed,
        "weekend_rollover": weekend_rollover
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


@router.get("/calendar", response_model=MonthlyCalendarOut)
def get_monthly_calendar(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="月份格式 YYYY-MM"),
    student_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    月度作业打卡日历接口：
    高效 SQL 聚合返回当月每日 total、completed 与状态 (green/yellow/red/gray)
    响应耗时 ≤ 50ms
    """
    try:
        year_str, month_str = month.split("-")
        year, m = int(year_str), int(month_str)
        if not (1 <= m <= 12):
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="月份格式非法，必须为 YYYY-MM")

    _, last_day = calendar.monthrange(year, m)
    start_date = date(year, m, 1)
    end_date = date(year, m, last_day)

    # 单条 SQL GROUP BY 聚合当月各天记录
    records = db.query(
        HomeworkItem.date,
        func.count(HomeworkItem.id).label("total"),
        func.sum(case((HomeworkItem.is_completed == True, 1), else_=0)).label("completed")
    ).filter(
        HomeworkItem.student_id == student_id,
        HomeworkItem.date >= start_date,
        HomeworkItem.date <= end_date
    ).group_by(HomeworkItem.date).all()

    stats_map = {
        r.date.strftime("%Y-%m-%d"): {
            "total": int(r.total or 0),
            "completed": int(r.completed or 0)
        }
        for r in records
    }

    days_list = []
    for day in range(1, last_day + 1):
        cur_date_str = f"{year:04d}-{m:02d}-{day:02d}"
        if cur_date_str in stats_map:
            tot = stats_map[cur_date_str]["total"]
            comp = stats_map[cur_date_str]["completed"]
            if tot == 0:
                status = "gray"
            elif comp == tot:
                status = "green"
            elif comp == 0:
                status = "red"
            else:
                status = "yellow"
            days_list.append(CalendarDayStatus(
                date=cur_date_str,
                total=tot,
                completed=comp,
                status=status
            ))
        else:
            days_list.append(CalendarDayStatus(
                date=cur_date_str,
                total=0,
                completed=0,
                status="gray"
            ))

    return MonthlyCalendarOut(month=month, days=days_list)
