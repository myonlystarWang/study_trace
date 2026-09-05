import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Setting, HomeworkItem, MistakeRecord, NotificationLog
from backend.app.schemas import (
    NotificationConfig, NotificationResultOut, NotificationSendOut
)
from backend.app.utils.notifier import (
    send_pushplus, send_serverchan, send_bark, send_webhook, send_webpush,
    dispatch_notification, build_summary_message
)
from backend.app.routers.homework import calculate_streak

logger = logging.getLogger("notifications_router")
router = APIRouter(prefix="/api/notifications", tags=["通知推送与晚报"])
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

DEFAULT_CONFIG = {
    "enabled_channels": ["pushplus"],
    "pushplus_token": "",
    "serverchan_key": "",
    "bark_key": "",
    "webhook_url": "",
    "reminder_slots": ["20:10", "21:10", "21:50"]
}


def load_notification_config(db: Session) -> dict:
    """从 Settings 表读取通知配置，若不存在则初始化默认值"""
    setting = db.query(Setting).filter(Setting.key == "notification_config").first()
    if not setting:
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(setting.value)
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception as e:
        logger.error(f"Failed to parse notification_config: {e}")
        return DEFAULT_CONFIG.copy()


def save_notification_config(config_data: dict, db: Session) -> None:
    """持久化通知配置到 Settings 表"""
    setting = db.query(Setting).filter(Setting.key == "notification_config").first()
    json_val = json.dumps(config_data, ensure_ascii=False)
    if setting:
        setting.value = json_val
    else:
        setting = Setting(key="notification_config", value=json_val)
        db.add(setting)
    db.commit()


@router.get("/config", response_model=NotificationConfig)
def get_config(db: Session = Depends(get_db)):
    """获取当前系统通知配置"""
    cfg = load_notification_config(db)
    return NotificationConfig(**cfg)


@router.put("/config", response_model=NotificationConfig)
def update_config(config_in: NotificationConfig, db: Session = Depends(get_db)):
    """更新并保存通知配置"""
    cfg_data = config_in.model_dump()
    save_notification_config(cfg_data, db)
    return NotificationConfig(**cfg_data)


@router.post("/test/{channel}", response_model=NotificationResultOut)
async def test_notification_channel(
    channel: str,
    target: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    单渠道联通性测试接口：
    可传入临时 target（Token/Key/URL）进行即时验证，若未传则使用已保存配置。
    """
    cfg = load_notification_config(db)
    title = "🔔【学迹】通道连通性测试"
    content = "恭喜！学迹通知服务通道配置成功，这是一条测试消息。\n\n- 服务名称：学迹 StudyTrace\n- 当前状态：联通正常"

    ch = channel.lower().strip()

    if ch == "pushplus":
        token = target if (target and target.strip()) else cfg.get("pushplus_token", "")
        success, msg = await send_pushplus(token, title, content)
    elif ch == "serverchan":
        key = target if (target and target.strip()) else cfg.get("serverchan_key", "")
        success, msg = await send_serverchan(key, title, content)
    elif ch == "bark":
        key = target if (target and target.strip()) else cfg.get("bark_key", "")
        success, msg = await send_bark(key, title, content)
    elif ch == "webhook":
        url = target if (target and target.strip()) else cfg.get("webhook_url", "")
        success, msg = await send_webhook(url, title, content)
    elif ch == "webpush":
        success, msg = await send_webpush({}, title, content)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的渠道: {channel}")

    return NotificationResultOut(channel=ch, success=success, message=msg)


@router.post("/send-summary-now", response_model=NotificationSendOut)
async def send_summary_now(
    student_id: int = 1,
    channels: Optional[list[str]] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    立即生成并全渠道发送今日作业与复习汇总日报 (force_summary)
    绕过中途跳过逻辑，随时全景快报
    """
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    # 1. 统计今日作业
    homework_items = db.query(HomeworkItem).filter(
        HomeworkItem.student_id == student_id,
        HomeworkItem.date == today
    ).all()

    items_data = []
    for item in homework_items:
        items_data.append({
            "subject_name": item.subject.name if item.subject else "综合",
            "title": item.content,
            "is_completed": item.is_completed,
            "completed_at": item.completed_at.strftime("%Y-%m-%d %H:%M:%S") if item.completed_at else None
        })

    # 2. 统计连续打卡与艾宾浩斯待复习
    streak_days = calculate_streak(student_id, db)
    ebbinghaus_count = db.query(MistakeRecord).filter(
        MistakeRecord.student_id == student_id,
        MistakeRecord.next_review_date <= today,
        MistakeRecord.mastery_status != "已掌握"
    ).count()

    # 3. 构造模板
    student_name = "初一同学"
    title, content = build_summary_message(
        student_name=student_name,
        today_str=today_str,
        items=items_data,
        streak_days=streak_days,
        ebbinghaus_count=ebbinghaus_count,
        force=True
    )

    # 4. 查配置并分发
    cfg = load_notification_config(db)
    target_channels = channels or cfg.get("enabled_channels", ["pushplus"])

    results = await dispatch_notification(
        title=title,
        content=content,
        channels=target_channels,
        config=cfg
    )

    # 5. 记录日志 (slot="manual")
    for ch, res in results.items():
        if res.get("success"):
            try:
                # 检查是否已存在当天 manual 记录
                exist = db.query(NotificationLog).filter(
                    NotificationLog.date == today,
                    NotificationLog.slot == "manual",
                    NotificationLog.channel == ch
                ).first()
                if not exist:
                    log = NotificationLog(
                        date=today,
                        slot="manual",
                        channel=ch,
                        sent_at=datetime.now(SHANGHAI_TZ)
                    )
                    db.add(log)
                    db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"Failed to record NotificationLog for {ch}: {e}")

    has_success = any(res.get("success") for res in results.values())
    formatted_details = {
        k: NotificationResultOut(channel=k, success=v["success"], message=v["message"])
        for k, v in results.items()
    }

    return NotificationSendOut(success=has_success, details=formatted_details)
