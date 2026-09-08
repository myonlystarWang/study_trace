import hashlib
import time
import pytest
from datetime import date
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import HomeworkItem, Subject, Student
from backend.app.utils.wechat_intent import (
    verify_wechat_signature, parse_wechat_xml, generate_wechat_reply_xml
)

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def _gen_signature(token: str, timestamp: str, nonce: str) -> str:
    tmp = sorted([token, timestamp, nonce])
    return hashlib.sha1("".join(tmp).encode("utf-8")).hexdigest()


# ==============================================================================
# 1. 微信握手签名测试 (GET /api/wechat/callback)
# ==============================================================================
def test_wechat_callback_verify_success():
    """测试合法的微信接口配置信息握手签名"""
    token = settings.WECHAT_CALLBACK_TOKEN or "studytrace2026"
    ts = str(int(time.time()))
    nonce = "123456"
    echostr = "random_echo_string_abc123"
    sig = _gen_signature(token, ts, nonce)

    resp = client.get(
        f"/api/wechat/callback?signature={sig}&timestamp={ts}&nonce={nonce}&echostr={echostr}"
    )
    assert resp.status_code == 200
    assert resp.text == echostr


def test_wechat_callback_verify_invalid_signature():
    """测试非法签名直接返回 403 拦截"""
    resp = client.get(
        "/api/wechat/callback?signature=bad_sig&timestamp=123&nonce=456&echostr=echo"
    )
    assert resp.status_code == 403


# ==============================================================================
# 2. 微信上行指令处理测试 (POST /api/wechat/callback)
# ==============================================================================
@pytest.mark.anyio
async def test_wechat_inbound_help_command():
    """测试发送【帮助】返回使用指南"""
    # 爸爸的合法 OpenID
    from_user = "oz1nN3D7D2MKPBE0ah2CmroanhVc"
    to_user = "gh_test"
    msg_id = f"msg_{int(time.time())}_help"
    xml_data = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[帮助]]></Content>
<MsgId>{msg_id}</MsgId>
</xml>"""

    resp = client.post(
        "/api/wechat/callback",
        content=xml_data.encode("utf-8"),
        headers={"Content-Type": "application/xml"}
    )
    assert resp.status_code == 200
    reply = parse_wechat_xml(resp.text)
    assert reply.get("ToUserName") == from_user
    assert reply.get("FromUserName") == to_user
    assert "微信快捷指令指南" in reply.get("Content", "")


@pytest.mark.anyio
async def test_wechat_inbound_checkin_and_query(db_session: Session):
    """测试通过微信发消息自动打卡与查询今日作业清单"""
    from_user = "oz1nN3D7D2MKPBE0ah2CmroanhVc"
    to_user = "gh_test"
    today = date.today()

    # 1. 准备一条今日数学作业
    math_sub = db_session.query(Subject).filter(Subject.name == "数学").first()
    stu = db_session.query(Student).first()
    
    # 清理并添加
    db_session.query(HomeworkItem).filter(
        HomeworkItem.student_id == stu.id,
        HomeworkItem.date == today
    ).delete()
    
    hw = HomeworkItem(
        student_id=stu.id,
        subject_id=math_sub.id,
        content="立体几何大题第3题",
        is_completed=False,
        date=today
    )
    db_session.add(hw)
    db_session.commit()

    # 2. 查询今日作业
    xml_query = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[今日作业]]></Content>
<MsgId>msg_query_1</MsgId>
</xml>"""
    resp = client.post("/api/wechat/callback", content=xml_query.encode("utf-8"))
    assert resp.status_code == 200
    reply = parse_wechat_xml(resp.text)
    assert "今日作业清单" in reply.get("Content", "")
    assert "立体几何大题" in reply.get("Content", "")

    # 3. 发送口语化打卡指令：数学 做完了
    xml_checkin = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[数学 做完了]]></Content>
<MsgId>msg_checkin_1</MsgId>
</xml>"""
    resp = client.post("/api/wechat/callback", content=xml_checkin.encode("utf-8"))
    assert resp.status_code == 200
    reply = parse_wechat_xml(resp.text)
    assert "已为您将【数学】标记为已完成" in reply.get("Content", "")

    # 断言数据库中已经打卡成功！
    db_session.refresh(hw)
    assert hw.is_completed is True
    assert hw.completed_at is not None


@pytest.mark.anyio
async def test_wechat_inbound_add_homework(db_session: Session):
    """测试通过微信发消息快速录入新作业"""
    from_user = "oz1nN3CuVUQ4S8yJ4PWU6wY2jsmo"  # 妈妈的 OpenID
    to_user = "gh_test"
    today = date.today()

    xml_add = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[新增作业 英语 听写Unit4重点词汇]]></Content>
<MsgId>msg_add_1</MsgId>
</xml>"""
    resp = client.post("/api/wechat/callback", content=xml_add.encode("utf-8"))
    assert resp.status_code == 200
    reply = parse_wechat_xml(resp.text)
    assert "录入成功" in reply.get("Content", "")
    assert "听写Unit4重点词汇" in reply.get("Content", "")

    # 验证数据库成功入库
    item = db_session.query(HomeworkItem).filter(
        HomeworkItem.date == today,
        HomeworkItem.content == "听写Unit4重点词汇"
    ).first()
    assert item is not None
    assert item.subject.name == "英语"
    assert item.is_completed is False


@pytest.mark.anyio
async def test_wechat_inbound_unauthorized_openid():
    """测试未在白名单中的陌生 OpenID 被拦截"""
    from_stranger = "oz1n_stranger_unknown_12345"
    xml_data = f"""<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[{from_stranger}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[数学 完成]]></Content>
<MsgId>msg_stranger_1</MsgId>
</xml>"""
    resp = client.post("/api/wechat/callback", content=xml_data.encode("utf-8"))
    assert resp.status_code == 200
    reply = parse_wechat_xml(resp.text)
    assert "尚未在学迹系统授权绑定" in reply.get("Content", "")


@pytest.mark.anyio
async def test_wechat_inbound_duplicate_msg_id():
    """测试 5 秒内重复推送相同 MsgId 返回 success 免重复处理"""
    from_user = "oz1nN3D7D2MKPBE0ah2CmroanhVc"
    dup_id = f"msg_dup_{int(time.time())}"
    xml_data = f"""<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[进度]]></Content>
<MsgId>{dup_id}</MsgId>
</xml>"""
    # 第一次正常处理
    resp1 = client.post("/api/wechat/callback", content=xml_data.encode("utf-8"))
    assert resp1.status_code == 200
    assert "<xml>" in resp1.text

    # 第二次重复发送，直接响应 success
    resp2 = client.post("/api/wechat/callback", content=xml_data.encode("utf-8"))
    assert resp2.status_code == 200
    assert resp2.text == "success"
