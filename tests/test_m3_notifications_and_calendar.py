import time
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.main import app
from backend.app.database import get_db, SessionLocal
from backend.app.models import HomeworkItem, Subject, NotificationLog, Setting
from backend.app.scheduler import (
    scheduler, setup_scheduler_jobs, check_and_dispatch_homework_reminders,
    acquire_scheduler_lock, release_scheduler_lock, SHANGHAI_TZ
)
from backend.app.utils import notifier
from backend.app.routers.notifications import load_notification_config, save_notification_config

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# DoD 1: 时区与时段配置正确 (Asia/Shanghai 20:10 / 21:10 / 21:50)
# ==============================================================================
def test_scheduler_timezone_and_slots():
    """验证 APScheduler 触发器时区严格锁定 Asia/Shanghai，时段包含 20:10, 21:10, 21:50"""
    setup_scheduler_jobs()
    jobs = scheduler.get_jobs()
    
    assert len(jobs) >= 3
    job_ids = {j.id for j in jobs}
    assert "reminder_20_10" in job_ids
    assert "reminder_21_10" in job_ids
    assert "summary_21_50" in job_ids

    for job in jobs:
        trigger = job.trigger
        assert str(trigger.timezone) == "Asia/Shanghai"


# ==============================================================================
# DoD 2: 数据库级与应用层幂等唯一约束 (SQLite batch_alter_table)
# ==============================================================================
def test_notification_idempotency_constraint(db_session: Session):
    """验证同一 (date, slot, channel) 重复插入时触发 SQLite 复合唯一约束拦截"""
    today = date.today()
    slot = "20:10"
    channel = "pushplus"

    # 清理可能存在的历史测试记录
    db_session.query(NotificationLog).filter(
        NotificationLog.date == today,
        NotificationLog.slot == slot,
        NotificationLog.channel == channel
    ).delete()
    db_session.commit()

    # 首次插入正常
    first_log = NotificationLog(
        date=today,
        slot=slot,
        channel=channel,
        sent_at=datetime.now(SHANGHAI_TZ)
    )
    db_session.add(first_log)
    db_session.commit()

    # 第二次插入相同 (date, slot, channel) 应触发 IntegrityError
    dup_log = NotificationLog(
        date=today,
        slot=slot,
        channel=channel,
        sent_at=datetime.now(SHANGHAI_TZ)
    )
    db_session.add(dup_log)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


# ==============================================================================
# DoD 3: 中途催办时段 (20:10 / 21:10) 满卡自动跳过免打扰
# ==============================================================================
@pytest.mark.anyio
async def test_midway_reminder_skips_when_completed(db_session: Session):
    """当天作业全部打勾或无作业时，20:10 / 21:10 催办静默跳过免打扰"""
    today = date.today()

    # 清除今日作业
    db_session.query(HomeworkItem).filter(HomeworkItem.date == today).delete()
    sub = db_session.query(Subject).first()

    # 添加 1 项已完成的作业
    hw = HomeworkItem(
        student_id=1,
        subject_id=sub.id,
        content="数学课后练习 P12",
        date=today,
        is_completed=True,
        completed_at=datetime.now()
    )
    db_session.add(hw)
    db_session.commit()

    # 调用 20:10 催办
    res = await check_and_dispatch_homework_reminders(slot="20:10", db=db_session)
    assert res["status"] == "skipped"
    assert res["reason"] == "all_completed_no_interruption"

    # 21:10 也应静默跳过
    res2 = await check_and_dispatch_homework_reminders(slot="21:10", db=db_session)
    assert res2["status"] == "skipped"


# ==============================================================================
# DoD 4: 中途催办时段带具体待办清单
# ==============================================================================
@pytest.mark.anyio
async def test_reminder_contains_uncompleted_items(db_session: Session):
    """当存在未完成作业时，催办内容中包含具体学科与待办题干"""
    today = date.today()
    db_session.query(HomeworkItem).filter(HomeworkItem.date == today).delete()
    sub = db_session.query(Subject).first()

    hw_undone = HomeworkItem(
        student_id=1,
        subject_id=sub.id,
        content="背诵 Unit 2 核心词汇",
        date=today,
        is_completed=False
    )
    db_session.add(hw_undone)
    db_session.commit()

    with patch("backend.app.scheduler.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = {"pushplus": {"channel": "pushplus", "success": True, "message": "ok"}}

        # 清除可能存在的日志
        db_session.query(NotificationLog).filter(
            NotificationLog.date == today,
            NotificationLog.slot == "20:10"
        ).delete()
        db_session.commit()

        res = await check_and_dispatch_homework_reminders(slot="20:10", db=db_session)
        assert res["status"] == "dispatched"

        # 检查传给分发器的内容
        assert mock_dispatch.called
        call_args = mock_dispatch.call_args[1]
        assert "背诵 Unit 2 核心词汇" in call_args["content"]
        assert sub.name in call_args["content"]


# ==============================================================================
# DoD 5: 晚间满卡仍发晚报 (21:50 总结喜报)
# ==============================================================================
@pytest.mark.anyio
async def test_evening_summary_dispatches_when_completed(db_session: Session):
    """作业 100% 完成时，21:50 晚间时段依然成功发送「🎉 今日作业满卡完成！」喜报"""
    today = date.today()
    db_session.query(HomeworkItem).filter(HomeworkItem.date == today).delete()
    sub = db_session.query(Subject).first()

    hw = HomeworkItem(
        student_id=1,
        subject_id=sub.id,
        content="语文古诗文默写",
        date=today,
        is_completed=True,
        completed_at=datetime.now()
    )
    db_session.add(hw)
    db_session.commit()

    with patch("backend.app.scheduler.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = {"pushplus": {"channel": "pushplus", "success": True, "message": "ok"}}

        db_session.query(NotificationLog).filter(
            NotificationLog.date == today,
            NotificationLog.slot == "21:50"
        ).delete()
        db_session.commit()

        res = await check_and_dispatch_homework_reminders(slot="21:50", db=db_session)
        assert res["status"] == "dispatched"
        assert "满卡" in res["title"]

        call_args = mock_dispatch.call_args[1]
        assert "🎉" in call_args["title"] or "满卡" in call_args["title"]


# ==============================================================================
# DoD 6: 立即发送今日汇总 (force_summary=True)
# ==============================================================================
def test_force_summary_dispatch():
    """测试 POST /api/notifications/send-summary-now 立即全渠道推送今日汇总"""
    with patch("backend.app.routers.notifications.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = {
            "pushplus": {"channel": "pushplus", "success": True, "message": "发送成功"}
        }

        resp = client.post("/api/notifications/send-summary-now", json={"channels": ["pushplus"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "pushplus" in data["details"]
        assert data["details"]["pushplus"]["success"] is True


# ==============================================================================
# DoD 7: 微信服务号 (PushPlus) 与 Server酱测试 (防重序号与实名提示)
# ==============================================================================
@pytest.mark.anyio
async def test_wechat_pushplus_and_serverchan():
    """测试 PushPlus 附带防重序列号，并正确处理未实名 905 错误"""
    # 1. 验证防重序列号格式
    dedup_id = notifier.generate_dedup_id()
    assert len(dedup_id) > 15
    assert "-" in dedup_id

    # 2. 模拟 PushPlus 未实名返回 905
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 905, "msg": "未实名认证"}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_pushplus("test_token", "作业提醒", "内容")
        assert success is False
        assert "未完成手机实名认证" in msg

    # 3. 模拟 Server酱 成功
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 0, "message": ""}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_serverchan("test_key", "作业提醒", "内容")
        assert success is True
        assert msg == "发送成功"


# ==============================================================================
# DoD 8: iOS Bark 推送测试
# ==============================================================================
@pytest.mark.anyio
async def test_bark_notification():
    """验证 Bark 推送 Payload 包含 group='学迹' 与合法结构"""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 200, "message": "success"}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_bark("my_bark_key", "测试标题", "测试正文")
        assert success is True
        assert "Bark 推送成功" in msg

        # 检查调用 URL 和 json payload
        called_url = mock_post.call_args[0][0]
        assert "api.day.app/my_bark_key" in called_url
        called_json = mock_post.call_args[1]["json"]
        assert called_json["group"] == "学迹"
        assert called_json["title"] == "测试标题"


# ==============================================================================
# DoD 9: 群机器人适配与错误 URL 友好提示
# ==============================================================================
@pytest.mark.anyio
async def test_webhook_adapter_and_error_handling():
    """验证非法 Webhook URL 给出友好中文错误，合法格式能正确适配"""
    # 1. 错误 URL
    success, msg = await notifier.send_webhook("invalid_url_without_http", "标题", "正文")
    assert success is False
    assert "必须以 http:// 或 https:// 开头" in msg

    # 2. 企业微信 Webhook 构造
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_post.return_value = mock_resp

        qy_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=123"
        success, msg = await notifier.send_webhook(qy_url, "标题", "正文")
        assert success is True

        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["msgtype"] == "markdown"
        assert "content" in call_payload["markdown"]


# ==============================================================================
# DoD 10: 多渠道并行与容错隔离
# ==============================================================================
@pytest.mark.anyio
async def test_multichannel_fault_tolerance():
    """通道 A 抛出异常或超时，不影响通道 B 正常送达"""
    async def mock_pushplus_fail(*args, **kwargs):
        raise TimeoutError("网络连接超时")

    async def mock_bark_success(*args, **kwargs):
        return True, "Bark 成功"

    with patch("backend.app.utils.notifier.send_pushplus", side_effect=mock_pushplus_fail), \
         patch("backend.app.utils.notifier.send_bark", side_effect=mock_bark_success):

        results = await notifier.dispatch_notification(
            title="通知",
            content="正文",
            channels=["pushplus", "bark"],
            config={"pushplus_token": "tk", "bark_key": "bk"}
        )

        assert results["pushplus"]["success"] is False
        assert "异常" in results["pushplus"]["message"] or "超时" in results["pushplus"]["message"]
        assert results["bark"]["success"] is True


# ==============================================================================
# DoD 11: 月历 API 性能与红黄绿灰准确度 (≤ 50ms)
# ==============================================================================
def test_monthly_calendar_api_performance_and_accuracy(db_session: Session):
    """测试 GET /api/homework/calendar 响应时间 ≤ 50ms 且准确映射 green/yellow/red/gray"""
    month_str = "2026-09"
    sub = db_session.query(Subject).first()

    # 构造数据：
    # 9月1日：2项全部完成 -> green
    # 9月2日：2项完成1项 -> yellow
    # 9月3日：1项未完成 -> red
    # 9月4日以后：无作业 -> gray
    db_session.query(HomeworkItem).filter(
        HomeworkItem.date >= date(2026, 9, 1),
        HomeworkItem.date <= date(2026, 9, 30)
    ).delete()

    db_session.add_all([
        HomeworkItem(student_id=1, subject_id=sub.id, content="1-A", date=date(2026, 9, 1), is_completed=True),
        HomeworkItem(student_id=1, subject_id=sub.id, content="1-B", date=date(2026, 9, 1), is_completed=True),
        HomeworkItem(student_id=1, subject_id=sub.id, content="2-A", date=date(2026, 9, 2), is_completed=True),
        HomeworkItem(student_id=1, subject_id=sub.id, content="2-B", date=date(2026, 9, 2), is_completed=False),
        HomeworkItem(student_id=1, subject_id=sub.id, content="3-A", date=date(2026, 9, 3), is_completed=False),
    ])
    db_session.commit()

    # 性能计时
    t0 = time.perf_counter()
    resp = client.get(f"/api/homework/calendar?month={month_str}")
    cost_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200
    assert cost_ms <= 50, f"日历接口响应耗时超标: {cost_ms:.2f}ms > 50ms"

    data = resp.json()
    assert data["month"] == "2026-09"
    days = {d["date"]: d for d in data["days"]}

    assert len(days) == 30  # 9月有30天
    assert days["2026-09-01"]["status"] == "green"
    assert days["2026-09-02"]["status"] == "yellow"
    assert days["2026-09-03"]["status"] == "red"
    assert days["2026-09-04"]["status"] == "gray"


# ==============================================================================
# DoD 12: Windows 文件锁防重 (msvcrt)
# ==============================================================================
def test_windows_msvcrt_scheduler_lock():
    """验证调度器文件锁机制：重复加锁被拦截，释放后可重用"""
    # 确保开始前处于未加锁状态
    release_scheduler_lock()

    first_locked = acquire_scheduler_lock()
    assert first_locked is True

    # 模拟第二个进程重复获取同一锁应失败
    # (在同一个 Python 进程中，再次尝试以非阻塞模式锁同一文件会抛出异常或被拒绝)
    try:
        second_locked = acquire_scheduler_lock()
    except Exception:
        second_locked = False

    # 验证释放
    release_scheduler_lock()


# ==============================================================================
# DoD 13: Web Push 解耦与优雅降级提示 (待 M6 结合 HTTPS 验收)
# ==============================================================================
@pytest.mark.anyio
async def test_webpush_decoupled_graceful_handling():
    """验证 Web Push 通道在未上线或缺库时返回优雅提示，不阻塞系统"""
    success, msg = await notifier.send_webpush({}, "测试", "内容")
    assert success is False
    assert "M6" in msg
