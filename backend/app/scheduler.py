import os
import sys
import logging
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.app.database import SessionLocal
from backend.app.models import HomeworkItem, MistakeRecord, NotificationLog, Student
from backend.app.routers.homework import calculate_streak
from backend.app.routers.notifications import load_notification_config
from backend.app.utils.notifier import (
    build_reminder_message, build_summary_message, dispatch_notification
)

logger = logging.getLogger("scheduler")
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

scheduler = AsyncIOScheduler(timezone=SHANGHAI_TZ)
_lock_file = None


def acquire_scheduler_lock(lock_path_override: Optional[Path] = None) -> bool:
    """
    Windows 原生文件锁防重 (保护 uvicorn --reload 下仅单实例运行调度器)
    使用 msvcrt.locking(..., LK_NBLCK, 1)
    """
    global _lock_file
    if _lock_file is not None:
        return False

    lock_dir = Path("data/temp")
    try:
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_path_override or (lock_dir / "scheduler.lock")
        
        _lock_file = open(lock_path, "a+")
        
        if sys.platform == "win32":
            import msvcrt
            # 尝试非阻塞锁定 1 字节
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except (OSError, IOError, Exception) as e:
        logger.info(f"Another process already holds scheduler lock or locked: {e}")
        if _lock_file:
            try:
                _lock_file.close()
            except Exception:
                pass
            _lock_file = None
        return False


def release_scheduler_lock() -> None:
    """释放调度器文件锁 (使用 LK_UNLCK)"""
    global _lock_file
    if _lock_file:
        try:
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            _lock_file.close()
        except Exception:
            pass
        _lock_file = None


async def check_and_dispatch_homework_reminders(
    slot: str,
    force_summary: bool = False,
    db: Optional[Session] = None,
    student_id: int = 1
) -> Dict[str, Any]:
    """
    核心调度与分级分发业务：
    - 20:10 / 21:10：中途催办（100% 完成时自动跳过免打扰；有未完成时发送催办清单）
    - 21:50 或 force_summary：晚间日报（100% 完成发送满卡喜报；有未完成发送收官快报）
    - 数据库级与应用级幂等防重
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        today = datetime.now(SHANGHAI_TZ).date()
        today_str = today.strftime("%Y-%m-%d")

        # 1. 统计今日作业条目
        homework_items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == today
        ).all()

        total_count = len(homework_items)
        uncompleted_items = [
            {
                "subject_name": item.subject.name if item.subject else "综合",
                "title": item.content
            }
            for item in homework_items if not item.is_completed
        ]
        completed_count = total_count - len(uncompleted_items)
        all_completed = (total_count > 0 and len(uncompleted_items) == 0)

        # 2. 中途催办免打扰逻辑 (20:10 / 21:10)
        if slot in ("20:10", "21:10") and not force_summary:
            if all_completed or total_count == 0:
                logger.info(f"[{slot}] 今日作业已全部完成或无作业，中途催办自动静默跳过免打扰。")
                return {
                    "status": "skipped",
                    "slot": slot,
                    "reason": "all_completed_no_interruption",
                    "details": {}
                }

        # 3. 构造推送内容 (查询真实学生姓名，避免硬编码)
        student = db.query(Student).filter(Student.id == student_id).first()
        student_name = student.name if student else "初一同学"

        # 频控保护：手动立即发送 30 秒内防连击刷爆第三方额度
        if slot == "manual" and force_summary:
            recent_manual = db.query(NotificationLog).filter(
                NotificationLog.date == today,
                NotificationLog.slot == "manual"
            ).order_by(NotificationLog.sent_at.desc()).first()
            if recent_manual and recent_manual.sent_at:
                sent_time = recent_manual.sent_at if recent_manual.sent_at.tzinfo else recent_manual.sent_at.replace(tzinfo=SHANGHAI_TZ)
                delta_sec = (datetime.now(SHANGHAI_TZ) - sent_time).total_seconds()
                if delta_sec < 30:
                    logger.warning(f"Manual summary rate limited ({delta_sec:.1f}s < 30s)")
                    return {
                        "status": "rate_limited",
                        "slot": slot,
                        "reason": f"刚刚已推送过今日汇总，请等待 {int(30 - delta_sec)} 秒后再试",
                        "details": {}
                    }

        if slot in ("20:10", "21:10") and not force_summary:
            title, content = build_reminder_message(
                student_name=student_name,
                today_str=today_str,
                uncompleted_items=uncompleted_items,
                total=total_count,
                completed=completed_count
            )
        else:
            # 21:50 晚间总结或 force_summary
            streak_days = calculate_streak(student_id, db)
            ebbinghaus_count = db.query(MistakeRecord).filter(
                MistakeRecord.student_id == student_id,
                MistakeRecord.next_review_date <= today,
                MistakeRecord.mastery_status != "已掌握"
            ).count()

            items_data = [
                {
                    "subject_name": i.subject.name if i.subject else "综合",
                    "title": i.content,
                    "is_completed": i.is_completed,
                    "completed_at": i.completed_at.strftime("%Y-%m-%d %H:%M:%S") if i.completed_at else None
                }
                for i in homework_items
            ]
            title, content = build_summary_message(
                student_name=student_name,
                today_str=today_str,
                items=items_data,
                streak_days=streak_days,
                ebbinghaus_count=ebbinghaus_count,
                force=force_summary
            )

        # 4. 读取渠道配置并进行幂等过滤
        cfg = load_notification_config(db)
        configured_channels = cfg.get("enabled_channels", ["pushplus"])

        channels_to_send = []
        for ch in configured_channels:
            # 幂等检查：当天、此时段、该渠道是否已成功发送
            existing_log = db.query(NotificationLog).filter(
                NotificationLog.date == today,
                NotificationLog.slot == slot,
                NotificationLog.channel == ch
            ).first()
            if existing_log and not force_summary:
                logger.info(f"[{slot}] 渠道 {ch} 今日已发送过，跳过重复推送 (幂等命中)")
            else:
                channels_to_send.append(ch)

        if not channels_to_send:
            return {
                "status": "idempotent_skipped",
                "slot": slot,
                "reason": "already_sent_all_channels",
                "details": {}
            }

        # 5. 调用分发器
        results = await dispatch_notification(
            title=title,
            content=content,
            channels=channels_to_send,
            config=cfg
        )

        # 6. 成功落库 (幂等硬约束保护)
        now_shanghai = datetime.now(SHANGHAI_TZ)
        for ch, res in results.items():
            if res.get("success"):
                try:
                    log_record = NotificationLog(
                        date=today,
                        slot=slot,
                        channel=ch,
                        sent_at=now_shanghai
                    )
                    db.add(log_record)
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"NotificationLog unique constraint caught duplicate for {slot} {ch}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to record NotificationLog: {e}")

        return {
            "status": "dispatched",
            "slot": slot,
            "title": title,
            "details": results
        }

    finally:
        if close_db:
            db.close()


def setup_scheduler_jobs() -> None:
    """初始化 APScheduler 定时任务 (Asia/Shanghai)"""
    scheduler.remove_all_jobs()

    # 1. 20:10 中途催办
    scheduler.add_job(
        check_and_dispatch_homework_reminders,
        trigger=CronTrigger(hour=20, minute=10, timezone=SHANGHAI_TZ),
        kwargs={"slot": "20:10"},
        id="reminder_20_10",
        name="20:10 作业催办提醒",
        replace_existing=True
    )

    # 2. 21:10 中途催办
    scheduler.add_job(
        check_and_dispatch_homework_reminders,
        trigger=CronTrigger(hour=21, minute=10, timezone=SHANGHAI_TZ),
        kwargs={"slot": "21:10"},
        id="reminder_21_10",
        name="21:10 作业催办提醒",
        replace_existing=True
    )

    # 3. 21:50 晚间总结日报
    scheduler.add_job(
        check_and_dispatch_homework_reminders,
        trigger=CronTrigger(hour=21, minute=50, timezone=SHANGHAI_TZ),
        kwargs={"slot": "21:50"},
        id="summary_21_50",
        name="21:50 晚间作业总结日报",
        replace_existing=True
    )


def start_scheduler() -> bool:
    """启动调度器 (仅在成功获取文件锁的主进程中启动)"""
    if not acquire_scheduler_lock():
        logger.info("Scheduler skipped: file lock not acquired (probably worker process in dev reload).")
        return False

    setup_scheduler_jobs()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started successfully with Asia/Shanghai timezone.")
    return True


def stop_scheduler() -> None:
    """优雅停止调度器并释放文件锁"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
    release_scheduler_lock()
