import time
import asyncio
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import HomeworkItem, Subject, NotificationLog, Setting, Student
from backend.app.scheduler import (
    scheduler, setup_scheduler_jobs, check_and_dispatch_homework_reminders,
    acquire_scheduler_lock, release_scheduler_lock, SHANGHAI_TZ
)
from backend.app.utils import notifier
from backend.app.routers.notifications import load_notification_config, save_notification_config

client = TestClient(app)
PARENT_PIN_HEADER = {"X-Parent-PIN": "888888"}


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# P0-1 安全专项: 通知路由家长门禁拦截与凭据保护验证
# ==============================================================================
def test_notification_endpoints_security_guard():
    """验证未提供家长口令时，通知相关接口一律返回 401 Unauthorized，防止凭据泄露与随意触发"""
    # 1. 未提供 X-Parent-PIN 访问配置 -> 401
    resp_get = client.get("/api/notifications/config")
    assert resp_get.status_code == 401
    assert "需要家长管理口令" in resp_get.json()["detail"]

    # 2. 错误 PIN 访问配置 -> 400
    resp_bad = client.get("/api/notifications/config", headers={"X-Parent-PIN": "000000"})
    assert resp_bad.status_code == 400

    # 3. 未提供 PIN 触发测试 -> 401
    resp_test = client.post("/api/notifications/test/bark")
    assert resp_test.status_code == 401

    # 4. 未提供 PIN 触发即时汇总 -> 401
    resp_send = client.post("/api/notifications/send-summary-now")
    assert resp_send.status_code == 401

    # 5. 正确 PIN 访问配置 -> 200 成功
    resp_ok = client.get("/api/notifications/config", headers=PARENT_PIN_HEADER)
    assert resp_ok.status_code == 200
    assert "enabled_channels" in resp_ok.json()


# ==============================================================================
# P0-2 性能与规范: dispatch_notification 真正并行并发执行验证 (DoD #7)
# ==============================================================================
@pytest.mark.anyio
async def test_dispatch_notification_is_truly_parallel():
    """
    验证 dispatch_notification 使用 asyncio.gather 真正并发触发：
    两个渠道各模拟延迟 0.15s，并发总耗时应 ≈0.15s (< 0.25s)；若为串行则需 ≥0.3s
    """
    async def mock_channel_delay(*args, **kwargs):
        await asyncio.sleep(0.15)
        return True, "成功"

    with patch("backend.app.utils.notifier.send_pushplus", side_effect=mock_channel_delay), \
         patch("backend.app.utils.notifier.send_bark", side_effect=mock_channel_delay):

        t0 = time.perf_counter()
        results = await notifier.dispatch_notification(
            title="并发测试",
            content="内容",
            channels=["pushplus", "bark"],
            config={"pushplus_token": "tk", "bark_key": "bk"}
        )
        cost_sec = time.perf_counter() - t0

        assert results["pushplus"]["success"] is True
        assert results["bark"]["success"] is True
        assert cost_sec < 0.25, f"未达到并发要求，总耗时 {cost_sec:.3f}s >= 0.25s (串行特征)"


# ==============================================================================
# P0-4 真实性断言: Windows 文件锁防重二次加锁必须被拒绝 (无假性通过)
# ==============================================================================
def test_windows_msvcrt_scheduler_lock_real_assertion():
    """验证调度器文件锁机制：重复加锁必须返回 False，释放后可重新获得"""
    release_scheduler_lock()

    first_locked = acquire_scheduler_lock()
    assert first_locked is True, "首次加锁必须成功"

    # 重复/第二进程获取必须返回 False
    second_locked = acquire_scheduler_lock()
    assert second_locked is False, "第二进程/重复获取锁必须被拦截并返回 False (杜绝假性通过)"

    # 释放后第三次获取必须成功
    release_scheduler_lock()
    third_locked = acquire_scheduler_lock()
    assert third_locked is True, "锁释放后重新获取必须成功"
    release_scheduler_lock()


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
    today = datetime.now(SHANGHAI_TZ).date()
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
    today = datetime.now(SHANGHAI_TZ).date()

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
# DoD 4: 中途催办时段带具体待办清单与学生姓名
# ==============================================================================
@pytest.mark.anyio
async def test_reminder_contains_uncompleted_items(db_session: Session):
    """当存在未完成作业时，催办内容中包含具体学科与待办题干，且标题带日期"""
    today = datetime.now(SHANGHAI_TZ).date()
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

        db_session.query(NotificationLog).filter(
            NotificationLog.date == today,
            NotificationLog.slot == "20:10"
        ).delete()
        db_session.commit()

        res = await check_and_dispatch_homework_reminders(slot="20:10", db=db_session)
        assert res["status"] == "dispatched"

        assert mock_dispatch.called
        call_args = mock_dispatch.call_args[1]
        assert "背诵 Unit 2 核心词汇" in call_args["content"]
        assert sub.name in call_args["content"]
        assert today.strftime("%Y-%m-%d") in call_args["title"]


# ==============================================================================
# DoD 5: 晚间满卡仍发晚报 (21:50 总结喜报)
# ==============================================================================
@pytest.mark.anyio
async def test_evening_summary_dispatches_when_completed(db_session: Session):
    """作业 100% 完成时，21:50 晚间时段依然成功发送「🎉 今日作业满卡完成！」喜报"""
    today = datetime.now(SHANGHAI_TZ).date()
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
# DoD 6: 立即发送今日汇总 (force_summary=True) 与频控验证 (P1-4)
# ==============================================================================
def test_force_summary_dispatch_and_rate_limit(db_session: Session):
    """测试 POST /api/notifications/send-summary-now 即时推送快照与 30 秒防刷频控"""
    today = datetime.now(SHANGHAI_TZ).date()
    # 清理今日已有 manual 记录
    db_session.query(NotificationLog).filter(
        NotificationLog.date == today,
        NotificationLog.slot == "manual"
    ).delete()
    db_session.commit()

    with patch("backend.app.scheduler.dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = {
            "pushplus": {"channel": "pushplus", "success": True, "message": "发送成功"}
        }

        # 1. 首次触发成功
        resp = client.post("/api/notifications/send-summary-now", headers=PARENT_PIN_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        # 2. 紧接着立即二次触发，触发 30 秒频控保护
        resp_fast = client.post("/api/notifications/send-summary-now", headers=PARENT_PIN_HEADER)
        assert resp_fast.status_code == 200
        assert resp_fast.json()["success"] is False


# ==============================================================================
# DoD 7: 微信服务号 (PushPlus) 与 Server酱测试 (防重序号与实名提示)
# ==============================================================================
@pytest.mark.anyio
async def test_wechat_pushplus_and_serverchan():
    """测试 PushPlus 附带防重序列号，并正确处理未实名 905 错误"""
    dedup_id = notifier.generate_dedup_id()
    assert len(dedup_id) > 15
    assert "-" in dedup_id

    # 模拟 PushPlus 未实名返回 905
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 905, "msg": "未实名认证"}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_pushplus("test_token", "作业提醒", "内容")
        assert success is False
        assert "未完成手机实名认证" in msg

    # 模拟 Server酱 成功
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 0, "message": ""}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_serverchan("test_key", "作业提醒", "内容")
        assert success is True
        assert msg == "发送成功"


# ==============================================================================
# DoD 8: iOS Bark 推送测试 (P1-6: 纠正 HTTP 200 但 code!=200 判定)
# ==============================================================================
@pytest.mark.anyio
async def test_bark_notification():
    """验证 Bark 推送 Payload 包含 group='学迹' 与合法结构，且正确处理 code 错误"""
    # 1. 正常成功
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 200, "message": "success"}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_bark("my_bark_key", "测试标题", "测试正文")
        assert success is True
        assert "Bark 推送成功" in msg

        called_url = mock_post.call_args[0][0]
        assert "api.day.app/my_bark_key" in called_url
        called_json = mock_post.call_args[1]["json"]
        assert called_json["group"] == "学迹"
        assert called_json["title"] == "测试标题"

    # 2. HTTP 200 但 Bark 业务返回 400 失败
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 400, "message": "device token not found"}
        mock_post.return_value = mock_resp

        success, msg = await notifier.send_bark("bad_key", "测试标题", "测试正文")
        assert success is False, "Bark code!=200 时绝不可误判为成功"
        assert "device token not found" in msg


# ==============================================================================
# DoD 9: 群机器人适配与错误 URL 友好提示
# ==============================================================================
@pytest.mark.anyio
async def test_webhook_adapter_and_error_handling():
    """验证非法 Webhook URL 给出友好中文错误，合法格式能正确适配"""
    success, msg = await notifier.send_webhook("invalid_url_without_http", "标题", "正文")
    assert success is False
    assert "必须以 http:// 或 https:// 开头" in msg

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

    t0 = time.perf_counter()
    resp = client.get(f"/api/homework/calendar?month={month_str}")
    cost_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200
    assert cost_ms <= 50, f"日历接口响应耗时超标: {cost_ms:.2f}ms > 50ms"

    data = resp.json()
    assert data["month"] == "2026-09"
    days = {d["date"]: d for d in data["days"]}

    assert len(days) == 30
    assert days["2026-09-01"]["status"] == "green"
    assert days["2026-09-02"]["status"] == "yellow"
    assert days["2026-09-03"]["status"] == "red"
    assert days["2026-09-04"]["status"] == "gray"


# ==============================================================================
# DoD 13: Web Push 解耦与优雅降级提示 (待 M6 结合 HTTPS 验收)
# ==============================================================================
@pytest.mark.anyio
async def test_webpush_decoupled_graceful_handling():
    """验证 Web Push 通道在未上线或缺库时返回优雅提示，不阻塞系统"""
    success, msg = await notifier.send_webpush({}, "测试", "内容")
    assert success is False
    assert "M6" in msg
