import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Setting, HomeworkItem, MistakeRecord, NotificationLog
from backend.app.schemas import (
    NotificationConfig, NotificationResultOut, NotificationSendOut
)
from backend.app.utils.notifier import (
    send_wechat_sandbox, send_pushplus, send_serverchan, send_bark, send_webhook, send_webpush,
    dispatch_notification, build_summary_message
)
from backend.app.routers.homework import calculate_streak

from backend.app.auth import require_parent_pin

logger = logging.getLogger("notifications_router")
router = APIRouter(
    prefix="/api/notifications",
    tags=["通知推送与晚报"],
    dependencies=[Depends(require_parent_pin)]
)
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

# 敏感凭据（app_id/app_secret/template_id/open_ids）只存 data/.env，
# 不在代码里留字面量；DB 行加载后由 load_notification_config 从 settings 自动回填。
DEFAULT_CONFIG = {
    "enabled_channels": ["wechat_sandbox"],
    "wechat_app_id": getattr(settings, "WECHAT_APP_ID", "") or "",
    "wechat_app_secret": getattr(settings, "WECHAT_APP_SECRET", "") or "",
    "wechat_template_id": getattr(settings, "WECHAT_TEMPLATE_ID", "") or "",
    "wechat_open_ids": getattr(settings, "WECHAT_OPEN_IDS", "") or "",
    "pushplus_token": "",
    "serverchan_key": "",
    "bark_key": "",
    "webhook_url": "",
    "reminder_slots": ["20:10", "21:10", "21:50"]
}

# 持久化到 DB 时剥离的敏感字段（读取时从 env 回填，DB 快照不入 git 泄露面）
SENSITIVE_CONFIG_KEYS = {"wechat_app_id", "wechat_app_secret", "wechat_template_id", "wechat_open_ids"}


def load_notification_config(db: Session) -> dict:
    """从 Settings 表读取通知配置，若不存在则初始化默认值"""
    setting = db.query(Setting).filter(Setting.key == "notification_config").first()
    if not setting:
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(setting.value)
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        # 清理已下线渠道的历史残留字段
        for k in [k for k in merged if k.startswith("wxpusher")]:
            merged.pop(k, None)
        # 自动补全敏感凭据（来自 data/.env）
        for k in ["wechat_app_id", "wechat_app_secret", "wechat_template_id", "wechat_open_ids"]:
            if not merged.get(k) and DEFAULT_CONFIG.get(k):
                merged[k] = DEFAULT_CONFIG[k]
        return merged
    except Exception as e:
        logger.error(f"Failed to parse notification_config: {e}")
        return DEFAULT_CONFIG.copy()


def save_notification_config(config_data: dict, db: Session) -> None:
    """持久化通知配置到 Settings 表（敏感凭据不入库，读取时由 env 回填）"""
    persist_data = {k: v for k, v in config_data.items() if k not in SENSITIVE_CONFIG_KEYS}
    setting = db.query(Setting).filter(Setting.key == "notification_config").first()
    json_val = json.dumps(persist_data, ensure_ascii=False)
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
    payload: Optional[dict] = Body(default=None),
    db: Session = Depends(get_db)
):
    """
    单渠道联通性测试接口：
    可传入临时 target（Token/Key/URL）及可选 topic_id 进行即时验证，若未传则使用已保存配置。
    """
    cfg = load_notification_config(db)
    title = "🔔【智学迹】微信推送通道测试"
    content = "恭喜！智学迹通知服务微信通道连通成功！\n\n- 服务名称：智学迹 StudyTrace\n- 运行状态：服务连接正常\n- 推送渠道：微信测试号模板消息\n- 每日作业提醒与晚间复习汇总将准时送达。"

    target = None
    topic_id = None
    if isinstance(payload, dict):
        target = payload.get("target")
        topic_id = payload.get("topic_id")

    ch = channel.lower().strip()

    if ch == "wechat_sandbox":
        app_id = payload.get("app_id") if isinstance(payload, dict) and payload.get("app_id") else cfg.get("wechat_app_id", "")
        app_secret = payload.get("app_secret") if isinstance(payload, dict) and payload.get("app_secret") else cfg.get("wechat_app_secret", "")
        template_id = payload.get("template_id") if isinstance(payload, dict) and payload.get("template_id") else cfg.get("wechat_template_id", "")
        open_ids = target if (target and target.strip()) else cfg.get("wechat_open_ids", "")
        success, msg = await send_wechat_sandbox(app_id, app_secret, template_id, open_ids, title, content)
    elif ch == "pushplus":
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
    db: Session = Depends(get_db)
):
    """
    立即生成并全渠道发送今日作业与复习汇总日报 (force_summary)
    直接复用调度引擎核心链路，防逻辑漂移
    """
    from backend.app.scheduler import check_and_dispatch_homework_reminders

    res = await check_and_dispatch_homework_reminders(
        slot="manual",
        force_summary=True,
        db=db,
        student_id=student_id
    )

    if res.get("status") == "rate_limited":
        return NotificationSendOut(
            success=False,
            details={},
            message=res.get("reason", "刚刚已推送过今日汇总，请稍候再试")
        )

    details = res.get("details", {})
    has_success = any(v.get("success") for v in details.values())
    formatted_details = {
        k: NotificationResultOut(channel=k, success=v.get("success", False), message=v.get("message", ""))
        for k, v in details.items()
    }

    return NotificationSendOut(
        success=has_success,
        details=formatted_details,
        message=res.get("reason") if not has_success else None
    )

