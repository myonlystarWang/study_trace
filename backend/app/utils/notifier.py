import re
import uuid
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple, Optional
import httpx

logger = logging.getLogger("notifier")

TIMEOUT = 5.0
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def generate_dedup_id() -> str:
    """生成防重序列号，防止 PushPlus 等第三方通道静默丢弃相同内容"""
    now = datetime.now(SHANGHAI_TZ)
    return f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

_wechat_token_cache: Dict[str, Tuple[str, float]] = {}


async def get_wechat_access_token(app_id: str, app_secret: str) -> Optional[str]:
    """获取微信测试号 access_token (2小时有效期，提前 5 分钟自动换新)"""
    import time
    now = time.time()
    cached = _wechat_token_cache.get(app_id)
    if cached and cached[1] > now + 300:
        return cached[0]

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": app_id.strip(),
        "secret": app_secret.strip()
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)
            if token:
                _wechat_token_cache[app_id] = (token, now + expires_in)
                return token
            else:
                logger.error(f"WeChat get token error: {data}")
                return None
    except Exception as e:
        logger.error(f"WeChat token request failed: {e}")
        return None


async def send_wechat_sandbox(
    app_id: str,
    app_secret: str,
    template_id: str,
    open_ids: str,
    title: str,
    content: str,
    url: str = "https://study.raddishlab.tech"
) -> Tuple[bool, str]:
    """
    微信公众平台接口测试号 (Sandbox 官方直推通道)
    - 0 元免费、直连腾讯微信、无第三方抽佣
    - 官方模板消息原生弹窗 + 声音，单日 10 万次额度
    - 支持全家多 OpenID 广播 (逗号/换行分隔)
    """
    if not app_id or not app_secret or not template_id:
        return False, "微信测试号 AppID, AppSecret 或 TemplateID 不能为空"

    ids = [i.strip() for i in re.split(r"[,;\n\s]+", open_ids) if i.strip()]
    if not ids:
        return False, "请至少指定一个微信用户的 OpenID"

    access_token = await get_wechat_access_token(app_id, app_secret)
    if not access_token:
        return False, "获取微信 AccessToken 失败，请检查 AppID 与 AppSecret"

    send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith(">")]
    summary_text = "；".join(lines[:3]) if lines else "今日作业打卡提醒"
    if len(summary_text) > 80:
        summary_text = summary_text[:77] + "..."

    async def _send_to_user(openid: str) -> Tuple[bool, str]:
        payload = {
            "touser": openid,
            "template_id": template_id.strip(),
            "url": url,
            "data": {
                "first": {
                    "value": title,
                    "color": "#173177"
                },
                "keyword1": {
                    "value": summary_text,
                    "color": "#333333"
                },
                "keyword2": {
                    "value": "打卡进行中 / 提醒",
                    "color": "#ff9900" if "催办" in title else "#07c160"
                },
                "remark": {
                    "value": "点击进入学迹系统查看详情或完成打卡",
                    "color": "#666666"
                }
            }
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(send_url, json=payload)
                data = resp.json()
                errcode = data.get("errcode", -1)
                errmsg = data.get("errmsg", "")
                if errcode == 0:
                    return True, "成功"
                elif errcode == 40001:
                    _wechat_token_cache.pop(app_id, None)
                    return False, f"Token 已失效: {errmsg}"
                else:
                    return False, f"微信返回错误 [{errcode}]: {errmsg}"
        except Exception as e:
            return False, f"网络请求失败: {str(e)}"

    tasks = [_send_to_user(oid) for oid in ids]
    results = await asyncio.gather(*tasks)

    success_cnt = sum(1 for r in results if r[0])
    total_cnt = len(ids)

    if success_cnt == total_cnt:
        return True, f"微信测试号发送成功 (已广播 {total_cnt} 位家庭成员)"
    elif success_cnt > 0:
        return True, f"微信测试号部分成功 ({success_cnt}/{total_cnt} 送达)"
    else:
        err_detail = "; ".join([r[1] for r in results])
        return False, f"微信测试号发送失败: {err_detail}"


async def send_wxpusher(
    app_token: str,
    topic_id: str,
    title: str,
    content: str,
    uids: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """
    WxPusher 微信服务号消息推送 (推荐首选)
    - 完全免费 (每天 1000 条免费额度，0 认证费，全家可关注主题)
    - contentType: 3 (Markdown 渲染)
    """
    if not app_token or not app_token.strip():
        return False, "WxPusher AppToken 不能为空"

    url = "https://wxpusher.zjiecode.com/api/send/message"

    # 解析 topicIds
    topic_ids = []
    if topic_id:
        for tid in str(topic_id).replace("，", ",").split(","):
            tid_s = tid.strip()
            if tid_s.isdigit():
                topic_ids.append(int(tid_s))

    target_uids = uids or []
    if not topic_ids and not target_uids:
        return False, "WxPusher 必须指定 TopicId 或 UID 至少一项"

    summary = title[:90] if title else "学迹通知"
    full_content = f"## {title}\n\n{content}"

    payload = {
        "appToken": app_token.strip(),
        "content": full_content,
        "summary": summary,
        "contentType": 3,
        "topicIds": topic_ids,
        "uids": target_uids
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            code = data.get("code")
            msg = data.get("msg", "")
            success = data.get("success", False)

            if code == 1000 and success:
                # 检查 data 数组明细中是否有未订阅应用或发送失败等具体原因
                data_list = data.get("data") or []
                errors = []
                for item in data_list:
                    item_code = item.get("code")
                    if item_code is not None and item_code != 1000:
                        status_msg = item.get("status") or f"错误码 {item_code}"
                        errors.append(status_msg)

                if errors:
                    return False, f"WxPusher 未能送达微信: {'; '.join(errors)}"
                return True, f"发送成功 (WxPusher: {msg})"
            else:
                return False, f"WxPusher 错误 [{code}]: {msg}"
    except httpx.TimeoutException:
        return False, "WxPusher 请求超时 (5s)"
    except Exception as e:
        logger.error(f"WxPusher send error: {e}")
        return False, f"网络请求失败: {str(e)}"


async def send_pushplus(token: str, title: str, content: str) -> Tuple[bool, str]:
    """
    PushPlus 微信服务号中转推送 (首选)
    必须实名认证（免费 200 条/天），末尾添加防重序号
    """
    if not token or not token.strip():
        return False, "PushPlus Token 不能为空"

    url = "https://www.pushplus.plus/send"
    dedup_id = generate_dedup_id()
    content_with_id = f"{content}\n\n> 🔖 记录 ID: {dedup_id}"

    payload = {
        "token": token.strip(),
        "title": title,
        "content": content_with_id,
        "template": "markdown"
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            code = data.get("code")
            msg = data.get("msg", "")

            if code == 200:
                return True, f"发送成功 (消息编号: {data.get('data', 'ok')})"
            elif code == 905:
                return False, "PushPlus 提示未完成手机实名认证，请先微信扫码关注服务号绑定手机后再使用"
            elif code == 900:
                return False, f"PushPlus 额度耗尽或限制: {msg}"
            else:
                return False, f"PushPlus 错误 [{code}]: {msg}"
    except httpx.TimeoutException:
        return False, "PushPlus 请求超时 (5s)"
    except Exception as e:
        logger.error(f"PushPlus send error: {e}")
        return False, f"网络请求失败: {str(e)}"


async def send_serverchan(key: str, title: str, content: str) -> Tuple[bool, str]:
    """Server酱 (Turbo版) 推送 (备选，免费 5 条/天)"""
    if not key or not key.strip():
        return False, "Server酱 SendKey 不能为空"

    url = f"https://sctapi.ftqq.com/{key.strip()}.send"
    dedup_id = generate_dedup_id()
    content_with_id = f"{content}\n\n> 🔖 记录 ID: {dedup_id}"
    payload = {"title": title, "desp": content_with_id}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, data=payload)
            data = resp.json()
            if data.get("code") == 0:
                return True, "发送成功"
            else:
                return False, f"Server酱错误: {data.get('message', '未知错误')}"
    except httpx.TimeoutException:
        return False, "Server酱请求超时 (5s)"
    except Exception as e:
        logger.error(f"Server酱 send error: {e}")
        return False, f"网络请求失败: {str(e)}"


async def send_bark(key: str, title: str, content: str) -> Tuple[bool, str]:
    """iOS Bark 推送 (支持逗号、换行分隔多个 Key 进行全家群发)"""
    if not key or not key.strip():
        return False, "Bark Key 不能为空"

    raw_keys = [k.strip() for k in re.split(r"[,;\n\s]+", key) if k.strip()]
    if not raw_keys:
        return False, "未解析到有效的 Bark Key"

    async def _send_one(clean_k: str) -> Tuple[bool, str]:
        clean_key = clean_k.rstrip("/")
        if clean_key.startswith("http://") or clean_key.startswith("https://"):
            base_url = clean_key
        else:
            base_url = f"https://api.day.app/{clean_key}"

        payload = {
            "title": title,
            "body": content,
            "group": "学迹",
            "icon": "https://cdn-icons-png.flaticon.com/512/2997/2997295.png"
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(base_url, json=payload)
                data = resp.json()
                code = data.get("code")
                if resp.status_code == 200 and (code is None or code == 200):
                    return True, "成功"
                else:
                    return False, data.get("message") or resp.text
        except Exception as e:
            return False, str(e)

    tasks = [_send_one(k) for k in raw_keys]
    results = await asyncio.gather(*tasks)
    success_cnt = sum(1 for r in results if r[0])
    if success_cnt == len(raw_keys):
        return True, f"Bark 推送成功 (已送达 {success_cnt} 台设备)"
    elif success_cnt > 0:
        return True, f"Bark 部分成功 ({success_cnt}/{len(raw_keys)})"
    else:
        return False, f"Bark 发送失败: {results[0][1]}"


async def send_webhook(url: str, title: str, content: str) -> Tuple[bool, str]:
    """群机器人 Webhook (自动适配企微、钉钉、飞书)"""
    if not url or not url.strip():
        return False, "Webhook URL 不能为空"

    url_str = url.strip()
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return False, "Webhook URL 格式不正确，必须以 http:// 或 https:// 开头"

    # 智能识别平台
    if "qyapi.weixin.qq.com" in url_str:
        # 企业微信机器人
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {title}\n{content}"
            }
        }
    elif "oapi.dingtalk.com" in url_str:
        # 钉钉机器人
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{content}"
            }
        }
    elif "open.feishu.cn" in url_str:
        # 飞书机器人
        payload = {
            "msg_type": "text",
            "content": {
                "text": f"{title}\n\n{content}"
            }
        }
    else:
        # 通用兼容 Markdown
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{content}"
            }
        }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url_str, json=payload)
            if resp.status_code in (200, 201):
                try:
                    res_data = resp.json()
                    # 检查钉钉或企微的 errcode
                    errcode = res_data.get("errcode") or res_data.get("code")
                    if errcode is not None and errcode != 0:
                        errmsg = res_data.get("errmsg") or res_data.get("msg", "未知错误")
                        return False, f"Webhook 机器人返回错误 [{errcode}]: {errmsg}"
                except Exception:
                    pass
                return True, "Webhook 发送成功"
            else:
                return False, f"Webhook 返回 HTTP {resp.status_code}: {resp.text[:100]}"
    except httpx.TimeoutException:
        return False, "Webhook 请求超时 (5s)"
    except Exception as e:
        logger.error(f"Webhook send error: {e}")
        return False, f"网络请求失败: {str(e)}"


async def send_webpush(subscription: dict, title: str, content: str) -> Tuple[bool, str]:
    """Web Push (预留通道，待 M6 结合 HTTPS 域名端到端激活)"""
    try:
        import pywebpush  # noqa: F401
    except ImportError:
        return False, "iOS Web Push 依赖 pywebpush 签名库与 HTTPS 域名，将在 M6 部署后激活"

    return False, "Web Push 待 M6 HTTPS 域名上线后验证"


async def dispatch_notification(
    title: str,
    content: str,
    channels: Optional[List[str]] = None,
    config: Optional[dict] = None
) -> Dict[str, dict]:
    """
    多渠道并行分发器 (asyncio.gather 真正的并行并发触发，容错隔离)
    单个渠道异常不影响其他渠道
    """
    if config is None:
        config = {}

    target_channels = channels or config.get("enabled_channels", ["wechat_sandbox"])

    async def _send_single(ch: str) -> Tuple[str, dict]:
        try:
            if ch == "wechat_sandbox":
                app_id = config.get("wechat_app_id", "")
                app_secret = config.get("wechat_app_secret", "")
                template_id = config.get("wechat_template_id", "")
                open_ids = config.get("wechat_open_ids", "")
                success, msg = await send_wechat_sandbox(app_id, app_secret, template_id, open_ids, title, content)
            elif ch == "wxpusher":
                app_token = config.get("wxpusher_app_token", "")
                topic_id = config.get("wxpusher_topic_id", "")
                success, msg = await send_wxpusher(app_token, topic_id, title, content)
            elif ch == "pushplus":
                token = config.get("pushplus_token", "")
                success, msg = await send_pushplus(token, title, content)
            elif ch == "serverchan":
                key = config.get("serverchan_key", "")
                success, msg = await send_serverchan(key, title, content)
            elif ch == "bark":
                key = config.get("bark_key", "")
                success, msg = await send_bark(key, title, content)
            elif ch == "webhook":
                url = config.get("webhook_url", "")
                success, msg = await send_webhook(url, title, content)
            elif ch == "webpush":
                success, msg = await send_webpush({}, title, content)
            else:
                success, msg = False, f"未知的推送渠道: {ch}"

            return ch, {
                "channel": ch,
                "success": success,
                "message": msg
            }
        except Exception as e:
            logger.error(f"Channel {ch} unhandled error: {e}")
            return ch, {
                "channel": ch,
                "success": False,
                "message": f"渠道处理异常: {str(e)}"
            }

    tasks = [_send_single(ch) for ch in target_channels]
    results_list = await asyncio.gather(*tasks)
    return dict(results_list)


def build_reminder_message(
    student_name: str,
    today_str: str,
    uncompleted_items: List[dict],
    total: int,
    completed: int
) -> Tuple[str, str]:
    """构建中途催办提醒模板 (20:10 / 21:10)"""
    percent = int((completed / total * 100)) if total > 0 else 0
    title = f"⏰【学迹作业提醒】{student_name} 今日作业待完成 ({today_str})"

    lines = [
        f"**亲爱的家长**：",
        f"{student_name} 今日作业进度：**{completed}/{total}** 项 ({percent}%) 🟡",
        "",
        "📋 **未完成作业待办清单**："
    ]

    for item in uncompleted_items:
        subj = item.get("subject_name", "综合")
        title_item = item.get("title", "")
        lines.append(f"- **[{subj}]** {title_item}")

    lines.append("")
    lines.append("💪 请提醒孩子专注高效，尽早完成并休息！")

    return title, "\n".join(lines)


def build_summary_message(
    student_name: str,
    today_str: str,
    items: List[dict],
    streak_days: int,
    ebbinghaus_count: int,
    force: bool = False
) -> Tuple[str, str]:
    """构建晚间总结或即时今日汇总日报 (21:50 或 force_summary)"""
    total = len(items)
    completed_items = [i for i in items if i.get("is_completed")]
    completed = len(completed_items)
    is_all_done = (total > 0 and completed == total)

    if force:
        title = f"🚀【学迹即时战报】{student_name} 今日作业与复习快报 ({today_str})"
        status_banner = f"⚡ **即时同步快报** ｜ 连续打卡：第 **{streak_days}** 天 ｜ 完成度：**{completed}/{total}**"
    elif is_all_done:
        title = f"🎉【学迹今日战报】{student_name} 今日作业满卡完成！({today_str})"
        status_banner = f"🌟 **太棒了！今日全部作业均已完成满卡！**\n🔥 **连续打卡**：第 **{streak_days}** 天 ｜ 完成度：**100%** 🟢"
    else:
        title = f"📊【学迹今日汇总】{student_name} 今日作业与复习快报 ({today_str})"
        status_banner = f"🔥 **连续打卡**：第 **{streak_days}** 天 ｜ 完成度：**{completed}/{total}** 🟡"

    lines = [
        status_banner,
        "",
        "📝 **今日各科作业明细**："
    ]

    if not items:
        lines.append("- 今日暂无录入作业")
    else:
        for item in items:
            subj = item.get("subject_name", "综合")
            title_item = item.get("title", "")
            done = item.get("is_completed", False)
            done_icon = "✅" if done else "⏳"
            time_str = ""
            if done and item.get("completed_at"):
                time_str = f" ({item['completed_at'][:16]})"
            lines.append(f"- {done_icon} **[{subj}]** {title_item}{time_str}")

    lines.append("")
    lines.append(f"🧠 **艾宾浩斯复习**：今日待复习错题 **{ebbinghaus_count}** 道")

    if is_all_done:
        lines.append("\n🌈 孩子今天表现非常自律，请及时给予肯定与鼓励！")
    else:
        lines.append("\n💪 仍有部分作业待确认，请结合实际情况安排收尾。")

    return title, "\n".join(lines)
