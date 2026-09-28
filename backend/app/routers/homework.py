import calendar
from datetime import date, datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from backend.app.database import get_db
from backend.app.auth import require_parent_pin
from backend.app.models import HomeworkItem, MistakeRecord, Subject
from backend.app.schemas import (
    HomeworkItemCreate, HomeworkItemUpdate, HomeworkItemOut, MistakeRecordOut,
    MonthlyCalendarOut, CalendarDayStatus
)
from backend.app.utils.holidays import get_break_span, get_holiday_context, is_workday

router = APIRouter(prefix="/api/homework", tags=["作业打卡"])


def calculate_streak(student_id: int, db: Session) -> int:
    """
    实时聚合计算连续满打卡天数（Streak）：
    - 工作日（含法定调休上班日）：当日所有作业完成计入 streak；
    - 休息日（普通周末或国家法定长假）：引入连休宽限期闭环。
      放假前最后一个工作日布置的大作业持续顺延至整个假期的最后一日晚；
      若当前正值假期期间且放假前大作业存在，处于宽限期不中断 streak；
      在假期结束前大作业全部清零后，假期各天统一计为连续满卡。
    """
    today = date.today()

    # 辅助函数：判断指定日期的作业是否全部完成
    def is_date_fully_completed(check_date: date) -> bool:
        # 1. 检查该日期自身的独立作业
        items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == check_date
        ).all()

        # 2. 连休（周末或国家法定节假日长假）宽限期处理
        break_span = get_break_span(check_date)
        if break_span:
            last_workday = break_span["last_workday"]
            span_end = break_span["span_end"]
            origin_items = db.query(HomeworkItem).filter(
                HomeworkItem.student_id == student_id,
                HomeworkItem.date == last_workday
            ).all()

            # 该日与放假前最后一个工作日均无任何作业 —— 属于完全空白的休息日。
            # 宽限期的本意是「放假前大作业顺延到假期完成」，若本身没有作业，
            # 这个休息日就不存在可闭环的任务，不能作为满卡日计入 streak，
            # 否则连续打卡天数会在空白假期凭空增加。
            if not items and not origin_items:
                return False

            own_completed = all(it.is_completed for it in items) if items else True
            origin_completed = bool(origin_items and all(it.is_completed for it in origin_items))

            is_active_break = (today >= last_workday and today <= span_end)

            if is_active_break:
                # 处于当前正在进行的假期宽限期内：
                # 若今天尚未到达假期的最后一天，当天自身任务完成即可继续保持打卡状态，放假前大作业允许持续推进
                if check_date < span_end:
                    return own_completed
                else:
                    # 假期的最后一天：看放假前大作业和该日任务是否全数闭环
                    return (origin_completed or not origin_items) and own_completed
            else:
                # 历史过往假期：放假前大作业和假期自身任务必须全部完成
                return (origin_completed or not origin_items) and own_completed

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


@router.get("/holiday-info")
def get_holiday_info_endpoint(
    target_date: Optional[date] = Query(default=None, alias="date")
):
    """查询指定日期相关的节假日连休/长假信息（如国庆假、中秋假、周末连休）"""
    d = target_date or date.today()
    info = get_holiday_context(d)
    return {
        "date": str(info["date"]),
        "is_workday": info["is_workday"],
        "current_break": {
            "span_start": str(info["current_break"]["span_start"]),
            "span_end": str(info["current_break"]["span_end"]),
            "last_workday": str(info["current_break"]["last_workday"]),
            "holiday_name": info["current_break"]["holiday_name"],
            "display_name": info["current_break"]["display_name"],
            "days": info["current_break"]["days"],
            "is_statutory": info["current_break"]["is_statutory"],
        } if info["current_break"] else None,
        "upcoming_break": {
            "span_start": str(info["upcoming_break"]["span_start"]),
            "span_end": str(info["upcoming_break"]["span_end"]),
            "last_workday": str(info["upcoming_break"]["last_workday"]),
            "holiday_name": info["upcoming_break"]["holiday_name"],
            "display_name": info["upcoming_break"]["display_name"],
            "days": info["upcoming_break"]["days"],
            "is_statutory": info["upcoming_break"]["is_statutory"],
        } if info["upcoming_break"] else None,
    }


@router.get("")
def get_homework_list(
    target_date: Optional[date] = Query(default=None, alias="date"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    scope: Optional[str] = Query(default=None, description="all | history | None"),
    student_id: int = 1,
    db: Session = Depends(get_db)
):
    streak = calculate_streak(student_id, db)

    # 1. 多天区间合并查询（供长假期/多日作业合并打印与统计）
    if start_date and end_date:
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        items = db.query(HomeworkItem).outerjoin(
            Subject, HomeworkItem.subject_id == Subject.id
        ).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date >= start_date,
            HomeworkItem.date <= end_date
        ).order_by(
            HomeworkItem.date.asc(),
            Subject.sort_order.asc(),
            HomeworkItem.id.asc()
        ).all()

        # 检查 start_date 是否处于连休假期，若放假前最后一个工作日早于 start_date，自动将顺延大作业归入列表
        rollover_items = []
        break_span = get_break_span(start_date)
        if break_span and break_span["last_workday"] < start_date:
            last_workday = break_span["last_workday"]
            rw_items = db.query(HomeworkItem).outerjoin(
                Subject, HomeworkItem.subject_id == Subject.id
            ).filter(
                HomeworkItem.student_id == student_id,
                HomeworkItem.date == last_workday
            ).order_by(
                Subject.sort_order.asc(),
                HomeworkItem.id.asc()
            ).all()
            for it in rw_items:
                rollover_items.append({
                    "id": it.id,
                    "student_id": it.student_id,
                    "subject_id": it.subject_id,
                    "subject_name": it.subject.name if it.subject else "",
                    "date": str(it.date),
                    "content": it.content,
                    "is_completed": it.is_completed,
                    "completed_at": it.completed_at.isoformat() if it.completed_at else None,
                    "source_image_path": it.source_image_path,
                    "created_at": it.created_at,
                    "is_weekend_rollover": True,
                    "rollover_label": f"{break_span['display_name']}顺延",
                })

        items_out = []
        for item in items:
            items_out.append({
                "id": item.id,
                "student_id": item.student_id,
                "subject_id": item.subject_id,
                "subject_name": item.subject.name if item.subject else "",
                "date": str(item.date),
                "content": item.content,
                "is_completed": item.is_completed,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "source_image_path": item.source_image_path,
                "created_at": item.created_at,
                "is_weekend_rollover": False,
                "rollover_label": None,
            })

        total_items = rollover_items + items_out
        total_count = len(total_items)
        completed_count = sum(1 for it in total_items if it["is_completed"])
        rate = int((completed_count / total_count) * 100) if total_count > 0 else 0

        break_info = None
        if break_span:
            break_info = {
                "holiday_name": break_span["holiday_name"],
                "display_name": break_span["display_name"],
                "span_start": str(break_span["span_start"]),
                "span_end": str(break_span["span_end"]),
                "days": break_span["days"],
                "is_statutory": break_span["is_statutory"],
            }

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "is_multi_day": True,
            "total": total_count,
            "completed": completed_count,
            "rate": rate,
            "streak": streak,
            "items": items_out,
            "rollover_items": rollover_items,
            "break_info": break_info
        }

    if scope == "all":
        # 获取全部未完成/待办作业（跨日期，按日期倒序与学科顺序排列）
        items = db.query(HomeworkItem).outerjoin(
            Subject, HomeworkItem.subject_id == Subject.id
        ).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.is_completed == False
        ).order_by(
            HomeworkItem.date.desc(),
            Subject.sort_order.asc(),
            HomeworkItem.id.asc()
        ).all()

        items_out = []
        for item in items:
            items_out.append({
                "id": item.id,
                "student_id": item.student_id,
                "subject_id": item.subject_id,
                "subject_name": item.subject.name if item.subject else "",
                "date": str(item.date),
                "content": item.content,
                "is_completed": item.is_completed,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "source_image_path": item.source_image_path,
                "created_at": item.created_at,
                "is_weekend_rollover": False,
                "rollover_label": None,
            })
        return {
            "date": date.today(),
            "total": len(items_out),
            "completed": 0,
            "rate": 0,
            "streak": streak,
            "items": items_out,
            "today_total": len(items_out),
            "today_completed": 0,
            "weekend_rollover": None
        }

    if scope == "history":
        # 获取历史已打卡完成记录（按完成时间与日期倒序排列，最新完成在前）
        items = db.query(HomeworkItem).outerjoin(
            Subject, HomeworkItem.subject_id == Subject.id
        ).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.is_completed == True
        ).order_by(
            HomeworkItem.date.desc(),
            HomeworkItem.completed_at.desc(),
            HomeworkItem.id.desc()
        ).limit(100).all()

        items_out = []
        for item in items:
            items_out.append({
                "id": item.id,
                "student_id": item.student_id,
                "subject_id": item.subject_id,
                "subject_name": item.subject.name if item.subject else "",
                "date": str(item.date),
                "content": item.content,
                "is_completed": item.is_completed,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "source_image_path": item.source_image_path,
                "created_at": item.created_at,
                "is_weekend_rollover": False,
                "rollover_label": None,
            })
        return {
            "date": date.today(),
            "total": len(items_out),
            "completed": len(items_out),
            "rate": 100,
            "streak": streak,
            "items": items_out,
            "today_total": len(items_out),
            "today_completed": len(items_out),
            "weekend_rollover": None
        }

    query_date = target_date or date.today()
    items = db.query(HomeworkItem).outerjoin(
        Subject, HomeworkItem.subject_id == Subject.id
    ).filter(
        HomeworkItem.student_id == student_id,
        HomeworkItem.date == query_date
    ).order_by(
        Subject.sort_order.asc(),
        HomeworkItem.id.asc()
    ).all()

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
            "date": str(item.date),
            "content": item.content,
            "is_completed": item.is_completed,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "source_image_path": item.source_image_path,
            "created_at": item.created_at,
            "is_weekend_rollover": False,
            "rollover_label": None,
        }
        items_out.append(item_dict)

    # 跨天连休大作业顺延透视：周末或国家法定节假日长假期间，自动透视放假前最后一个工作日的大作业
    weekend_rollover = None
    break_span = get_break_span(query_date)
    if break_span and break_span["last_workday"] < query_date:
        origin_date = break_span["last_workday"]
        origin_items = db.query(HomeworkItem).outerjoin(
            Subject, HomeworkItem.subject_id == Subject.id
        ).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == origin_date
        ).order_by(
            Subject.sort_order.asc(),
            HomeworkItem.id.asc()
        ).all()

        if origin_items:
            orig_completed = sum(1 for it in origin_items if it.is_completed)
            orig_total = len(origin_items)
            orig_rate = int((orig_completed / orig_total) * 100) if orig_total > 0 else 0
            orig_items_out = []
            for it in origin_items:
                orig_items_out.append({
                    "id": it.id,
                    "student_id": it.student_id,
                    "subject_id": it.subject_id,
                    "subject_name": it.subject.name if it.subject else "",
                    "date": str(it.date),
                    "content": it.content,
                    "is_completed": it.is_completed,
                    "completed_at": it.completed_at.isoformat() if it.completed_at else None,
                    "source_image_path": it.source_image_path,
                    "created_at": it.created_at,
                    "is_weekend_rollover": True,
                    "rollover_label": f"{break_span['display_name']}顺延",
                })

            weekend_rollover = {
                "source_date": str(origin_date),
                "total": orig_total,
                "completed": orig_completed,
                "rate": orig_rate,
                "items": orig_items_out,
                "break_info": {
                    "holiday_name": break_span["holiday_name"],
                    "display_name": break_span["display_name"],
                    "span_start": str(break_span["span_start"]),
                    "span_end": str(break_span["span_end"]),
                    "days": break_span["days"],
                    "is_statutory": break_span["is_statutory"],
                }
            }

    # 如果存在顺延作业，则综合计算全局总数与完成率
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
        "weekend_rollover": weekend_rollover,
        "break_info": {
            "holiday_name": break_span["holiday_name"],
            "display_name": break_span["display_name"],
            "span_start": str(break_span["span_start"]),
            "span_end": str(break_span["span_end"]),
            "days": break_span["days"],
            "is_statutory": break_span["is_statutory"],
        } if break_span else None
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
def delete_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_parent_pin),
):
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
