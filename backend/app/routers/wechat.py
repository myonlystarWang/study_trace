import logging
from fastapi import APIRouter, Request, Query, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.utils.wechat_intent import (
    verify_wechat_signature,
    parse_wechat_xml,
    generate_wechat_reply_xml,
    is_duplicate_msg,
    handle_wechat_inbound_message
)

logger = logging.getLogger("wechat_router")

router = APIRouter(prefix="/api/wechat", tags=["WeChat"])


@router.get("/callback", summary="微信公众平台接口配置信息握手校验")
def wechat_callback_verify(
    signature: str = Query(..., description="微信加密签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="随机字符串")
):
    """
    当在微信公众平台接口测试号后台点击「接口配置信息 ➔ 提交」时，
    微信服务器会自动以 GET 方式向此接口发起握手请求。
    验证通过后必须原样返回 echostr 内容，微信后台才会提示“配置成功”。
    """
    token = settings.WECHAT_CALLBACK_TOKEN or "studytrace2026"
    if verify_wechat_signature(signature, timestamp, nonce, token):
        logger.info(f"WeChat callback verify passed: echostr={echostr[:10]}...")
        return Response(content=echostr, media_type="text/plain")
    else:
        logger.warning(f"WeChat callback verify failed: sig={signature} ts={timestamp} nonce={nonce}")
        raise HTTPException(status_code=403, detail="Invalid WeChat signature")


@router.post("/callback", summary="微信上行消息与事件接收入口")
async def wechat_callback_receive(
    request: Request,
    signature: str = Query("", description="微信加密签名"),
    timestamp: str = Query("", description="时间戳"),
    nonce: str = Query("", description="随机数"),
    db: Session = Depends(get_db)
):
    """
    接收用户在关注的测试号聊天框中发送的文字消息，
    支持快速打卡、录入作业、查询今日清单、查询进度与帮助指令。
    """
    # 1. 签名安全初验（若提供了签名则比对，宽容处理测试调用）
    token = settings.WECHAT_CALLBACK_TOKEN or "studytrace2026"
    if signature and not verify_wechat_signature(signature, timestamp, nonce, token):
        logger.warning("WeChat POST message signature verification failed.")
        raise HTTPException(status_code=403, detail="Invalid WeChat signature")

    raw_body_bytes = await request.body()
    raw_body = raw_body_bytes.decode("utf-8", errors="ignore")

    msg_data = parse_wechat_xml(raw_body)
    if not msg_data:
        logger.warning("Received empty or unparsable XML from WeChat")
        return Response(content="success", media_type="text/plain")

    msg_type = msg_data.get("MsgType", "").lower()
    from_user = msg_data.get("FromUserName", "")  # 发送者 OpenID
    to_user = msg_data.get("ToUserName", "")      # 测试号原始 ID
    msg_id = msg_data.get("MsgId", "")
    content = msg_data.get("Content", "")

    # 2. 5 秒防重幂等校验 (防止微信网络波动自动重试 3 次导致重复录入或打卡)
    if msg_id and is_duplicate_msg(msg_id):
        logger.info(f"Ignored duplicate WeChat message: MsgId={msg_id}")
        return Response(content="success", media_type="text/plain")

    # 3. 消息分类处理
    if msg_type == "text":
        logger.info(f"WeChat inbound text from {from_user[:8]}...: {content}")
        reply_text = await handle_wechat_inbound_message(
            from_openid=from_user,
            content=content,
            db=db
        )
    elif msg_type == "event":
        event = msg_data.get("Event", "").lower()
        if event == "subscribe":
            reply_text = (
                "👋 欢迎关注智学迹 (StudyTrace) 家长督学伴侣！\n\n"
                "您可以通过本号实时接收孩子的课业催办与每日打卡喜报。\n"
                "也可以直接在聊天框发送文字完成作业打卡与录入！\n\n"
                "💡 发送【帮助】可查看完整快捷操作指令。"
            )
        elif event == "unsubscribe":
            logger.info(f"User unsubscribed: {from_user}")
            return Response(content="success", media_type="text/plain")
        else:
            return Response(content="success", media_type="text/plain")
    else:
        reply_text = "💡 收到消息！目前智学迹支持文字快捷指令交互，您可以回复【帮助】查看使用说明。"

    # 4. 组装合规 XML 被动回复消息
    reply_xml = generate_wechat_reply_xml(
        to_user=from_user,
        from_user=to_user,
        reply_text=reply_text
    )
    return Response(content=reply_xml, media_type="application/xml; charset=utf-8")
