import re
import time
import hashlib
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple
import xml.etree.ElementTree as ET

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import HomeworkItem, Subject, Student, MistakeRecord
from backend.app.routers.homework import calculate_streak
from backend.app.utils.notifier import parse_wechat_open_ids, send_wechat_sandbox

logger = logging.getLogger("wechat_intent")

# 最近处理过的 MsgId 缓存 (过期时间 15 秒，防微信 5 秒超时重复重发)
_MSG_ID_CACHE: Dict[str, float] = {}


def verify_wechat_signature(signature: str, timestamp: str, nonce: str, token: str) -> bool:
    """验证微信服务器发送的 GET 请求签名"""
    if not signature or not timestamp or not nonce or not token:
        return False
    try:
        tmp_list = sorted([str(token), str(timestamp), str(nonce)])
        tmp_str = "".join(tmp_list).encode("utf-8")
        hashcode = hashlib.sha1(tmp_str).hexdigest()
        return hashcode == signature
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def is_duplicate_msg(msg_id: str) -> bool:
    """基于 MsgId 判断是否是微信重复推送的消息"""
    if not msg_id:
        return False
    now = time.time()
    # 清理 15 秒前过期的缓存
    expired = [k for k, v in _MSG_ID_CACHE.items() if now - v > 15.0]
    for k in expired:
        _MSG_ID_CACHE.pop(k, None)

    if msg_id in _MSG_ID_CACHE:
        return True
    _MSG_ID_CACHE[msg_id] = now
    return False


def parse_wechat_xml(raw_xml: str) -> Dict[str, str]:
    """解析微信 POST 上行的 XML 消息报文"""
    res: Dict[str, str] = {}
    if not raw_xml or not raw_xml.strip():
        return res
    try:
        root = ET.fromstring(raw_xml.strip())
        for child in root:
            res[child.tag] = child.text.strip() if child.text else ""
    except Exception as e:
        logger.error(f"Failed to parse WeChat XML: {e}")
    return res


def generate_wechat_reply_xml(to_user: str, from_user: str, reply_text: str) -> str:
    """组装微信合规的被动回复文本 XML 报文"""
    create_time = int(time.time())
    # 替换敏感 XML 字符，转义并包装在 CDATA 内
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_text}]]></Content>
</xml>"""


KNOWN_SUBJECT_NAMES = {
    "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "道法", "政治", "道德与法治",
    "科学", "信息", "信息技术", "体育", "音乐", "美术", "综合", "劳技"
}


def normalize_text(text: str) -> str:
    """规范化特殊文本字符：全角空格、不间断空格和特殊连字符"""
    t = re.sub(r"[\u00a0\u3000\t]+", " ", text or "")
    t = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", t)
    return t


def clean_item_content(content: str) -> str:
    """剥离前缀条目序号 (如 1. / 1、 / (1) / 1) / ① / - / • / *)"""
    return re.sub(r"^(?:[①-⑩\d]+[\.、\)]|\([①-⑩\d]+\)|[•\-\*])\s*", "", content).strip()


def parse_batch_homework_text(raw_content: str, db_subjects: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """
    解析微信群/微信老师发布的批量多科目作业通知。
    支持班级群常见格式：
    语文：
    1. 预习第三课
    2. 生字词语1+1
    数学：
    1. 打印的习题
    英语：
    1. 听写单词
    """
    subject_set = set(KNOWN_SUBJECT_NAMES)
    if db_subjects:
        subject_set.update(db_subjects)

    norm_content = normalize_text(raw_content or "")
    lines = [line.strip() for line in norm_content.splitlines()]

    results: List[Tuple[str, str]] = []
    current_subject: Optional[str] = None

    skip_pattern = re.compile(
        r"^(?:今日作业|今天作业|各科作业|作业通知|各位家长|请各位家长|请家长|作业如下|温馨提示|大家晚上好|收到请回复|各位同学|【今日作业】|【作业通知】)"
    )

    subj_header_re = re.compile(
        r"^(?:[一二三四五六七八九十\d]+[\.、\s\)])?\s*(?:【|\[)?([\u4e00-\u9fa5]{2,6})(?:】|\])?\s*[:：]\s*(.*)$"
    )
    subj_single_line_re = re.compile(
        r"^(?:[一二三四五六七八九十\d]+[\.、\s\)])?\s*(?:【|\[)?([\u4e00-\u9fa5]{2,6})(?:】|\])?$"
    )

    for line in lines:
        if not line:
            continue
        if skip_pattern.search(line) and not subj_header_re.match(line):
            continue

        mA = subj_header_re.match(line)
        if mA:
            potential_subj = mA.group(1).strip()
            matched_subj = None
            if potential_subj in subject_set:
                matched_subj = potential_subj
            else:
                for s in subject_set:
                    if s in potential_subj or potential_subj in s:
                        matched_subj = s
                        break
            if matched_subj:
                current_subject = matched_subj
                rest = mA.group(2).strip()
                if rest:
                    clean_rest = clean_item_content(rest)
                    if clean_rest:
                        results.append((current_subject, clean_rest))
                continue

        mB = subj_single_line_re.match(line)
        if mB:
            potential_subj = mB.group(1).strip()
            matched_subj = None
            if potential_subj in subject_set:
                matched_subj = potential_subj
            else:
                for s in subject_set:
                    if s in potential_subj or potential_subj in s:
                        matched_subj = s
                        break
            if matched_subj:
                current_subject = matched_subj
                continue

        if current_subject:
            clean_item = clean_item_content(line)
            if clean_item:
                results.append((current_subject, clean_item))

    return results


async def handle_wechat_inbound_message(
    from_openid: str,
    content: str,
    db: Session,
    student_id: int = 1
) -> str:
    """
    处理已关注微信用户发来的文本指令 (双模交互核心引擎)
    - 检查 OpenID 白名单鉴权
    - 意图提取：打卡/完成、新增作业、查询今日作业、查询进度、帮助
    - 满卡全家异步广播联动
    """
    raw_content = (content or "").strip()
    if not raw_content:
        return "收到空消息，请输入【帮助】查看使用指南。"

    # 1. 白名单鉴权：检查 from_openid 是否在已配置的家庭成员中
    configured_members = parse_wechat_open_ids(settings.WECHAT_OPEN_IDS)
    allowed_openids = [oid for _, oid in configured_members]
    
    sender_name = "家长"
    is_authorized = False
    for name, oid in configured_members:
        if oid == from_openid:
            is_authorized = True
            if name and name not in ("家庭成员", "成员1", "成员2"):
                sender_name = name
            break

    # 若未配置任何 OpenID，则默认允许当前首个操作人并提示
    if allowed_openids and not is_authorized:
        logger.warning(f"Unauthorized WeChat OpenID attempted command: {from_openid}")
        return (
            "⚠️ 身份提示：当前微信号尚未在智学迹系统授权绑定。\n"
            "为了保障孩子学情数据安全，请在电脑或手机端【家长管理 ➔ 微信设置】中添加您的 OpenID 后再试。\n"
            f"您的当前 OpenID 为：\n{from_openid}"
        )

    # 获取学生信息
    student = db.query(Student).filter(Student.id == student_id).first()
    student_name = student.name if student else "王昱轩同学"
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    # 2. 意图：帮助指南
    if re.match(r"^(帮助|help|\?|？|功能|怎么用)$", raw_content, re.IGNORECASE):
        return (
            f"📖【智学迹 · 微信快捷指令指南】\n"
            f"亲爱的{sender_name}，您可以直接在聊天框发送以下内容：\n\n"
            f"1️⃣ 快速打卡完成：\n"
            f"· 发送：数学 完成\n"
            f"· 发送：打卡 物理\n"
            f"· 发送：数学 做完了\n\n"
            f"2️⃣ 快捷录入作业：\n"
            f"· 单项录入：新增作业 英语 默写第三单元单词\n"
            f"· 批量录入：直接复制微信群老师发的多科作业粘贴发送，自动分科入库！\n\n"
            f"3️⃣ 查看今日作业：\n"
            f"· 发送：今日作业 或 作业清单\n\n"
            f"4️⃣ 查看打卡天数与学情：\n"
            f"· 发送：进度 或 连续打卡"
        )

    # 3. 意图：查询今日作业清单
    if re.match(r"^(今日作业|作业清单|还有什么作业|查作业|今日待办|作业)$", raw_content):
        items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == today
        ).all()
        
        if not items:
            return f"📅 {student_name} 今日 ({today_str}) 暂未录入任何作业项。\n💡 您可以直接发送：新增作业 [学科] [内容] 快速录入！"

        total = len(items)
        completed = sum(1 for it in items if it.is_completed)
        percent = int(completed / total * 100) if total > 0 else 0
        icon = "🟢" if completed == total else "🟡"

        lines = [f"📅 {student_name} 今日作业清单 ({today_str})：\n"]
        for it in items:
            sname = it.subject.name if it.subject else "综合"
            status_icon = "✅" if it.is_completed else "⏳"
            lines.append(f"{status_icon} 【{sname}】{it.content}")

        lines.append(f"\n当前进度：{completed}/{total} 项 ({percent}%) {icon}")
        if completed == total:
            lines.append("🎉 今日作业全部满卡达成，太棒了！")
        else:
            lines.append("💪 督促孩子完成后，直接回复【学科 完成】即可秒级打卡。")
        return "\n".join(lines)

    # 4. 意图：查询打卡进度 / 连续打卡 Streak
    if re.match(r"^(进度|连续打卡|打卡天数|streak|学情|打卡)$", raw_content, re.IGNORECASE):
        streak_days = calculate_streak(student_id, db)
        items = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == today
        ).all()
        total = len(items)
        completed = sum(1 for it in items if it.is_completed)
        percent = int(completed / total * 100) if total > 0 else 0

        # 查错题数
        mastered_cnt = db.query(MistakeRecord).filter(
            MistakeRecord.student_id == student_id,
            MistakeRecord.mastery_status == "已掌握"
        ).count()

        return (
            f"🔥【{student_name} · 学习追踪动态】\n"
            f"· 🔥 连续打卡：已达成第 {streak_days} 天\n"
            f"· 📋 今日作业：已完成 {completed}/{total} 项 ({percent}%)\n"
            f"· 🧠 错题巩固：已完全掌握 {mastered_cnt} 道错题\n\n"
            f"保持良好学习习惯，每一天的积累都在创造飞跃！"
        )

    # 5. 意图：新增作业 (例如: "新增作业 英语 默写单词" 或 "添加作业 语文 背诵古诗")
    add_match = re.match(
        r"^(?:新增作业|添加作业|留作业|布置作业|记作业)\s*[:：]?\s*([\u4e00-\u9fa5]{2,4})\s+(.+)$",
        raw_content
    )
    if not add_match:
        # 兼容格式: "语文 作业 背诵古诗"
        add_match = re.match(
            r"^([\u4e00-\u9fa5]{2,4})\s+(?:作业)\s+(.+)$",
            raw_content
        )

    if add_match:
        subj_name = add_match.group(1).strip()
        homework_desc = add_match.group(2).strip()

        # 查找或匹配学科
        subject = db.query(Subject).filter(Subject.name == subj_name).first()
        if not subject:
            # 模糊匹配 (例如 "英" 匹配 "英语")
            subject = db.query(Subject).filter(Subject.name.like(f"%{subj_name}%")).first()
        if not subject:
            # 默认归入第一个学科或综合
            subject = db.query(Subject).first()

        new_item = HomeworkItem(
            student_id=student_id,
            subject_id=subject.id if subject else 1,
            date=today,
            content=homework_desc,
            is_completed=False
        )
        db.add(new_item)
        db.commit()

        # 统计今日总数
        total_now = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == today
        ).count()

        return (
            f"📝 录入成功！\n"
            f"已为今日添加：【{subject.name if subject else subj_name}】{homework_desc}\n"
            f"今日作业清单已增至 {total_now} 项。完成作业后回复【{subject.name if subject else subj_name} 完成】即可快速打卡。"
        )

    # 6. 意图：作业打卡完成 (例如: "数学 完成", "打卡 物理", "数学 做完了", "英语 搞定")
    # 提取学科关键词
    subjects = db.query(Subject).all()
    subject_names = [s.name for s in subjects]
    if not subject_names:
        subject_names = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "道法"]

    subj_pattern = "|".join([re.escape(name) for name in subject_names])
    action_pattern = r"(完成|打卡|搞定|做完|做完了|写完|写完了|已完成|已做完|已写完|过了)"

    # 形式 1: "数学 完成" / "数学做完了"
    checkin_m1 = re.search(rf"({subj_pattern})\s*{action_pattern}", raw_content)
    # 形式 2: "打卡 数学" / "完成 英语"
    checkin_m2 = re.search(rf"{action_pattern}\s*({subj_pattern})", raw_content)

    matched_subj = None
    if checkin_m1:
        matched_subj = checkin_m1.group(1).strip()
    elif checkin_m2:
        matched_subj = checkin_m2.group(2).strip()

    if matched_subj:
        subject = db.query(Subject).filter(Subject.name == matched_subj).first()
        if not subject:
            subject = db.query(Subject).filter(Subject.name.like(f"%{matched_subj}%")).first()

        if subject:
            # 查找今日该学科的作业
            items = db.query(HomeworkItem).filter(
                HomeworkItem.student_id == student_id,
                HomeworkItem.subject_id == subject.id,
                HomeworkItem.date == today
            ).all()

            if not items:
                return f"💡 提示：{student_name} 今日暂未录入【{matched_subj}】作业项。\n您可直接发送：新增作业 {matched_subj} [作业内容] 进行创建。"

            uncompleted_subj_items = [it for it in items if not it.is_completed]
            if not uncompleted_subj_items:
                return f"💡 提示：今日【{matched_subj}】作业此前已是打卡完成状态，无需重复打卡！"

            # 标记该学科所有未完成项为已完成
            now_dt = datetime.now()
            for it in uncompleted_subj_items:
                it.is_completed = True
                it.completed_at = now_dt
            db.commit()

            # 统计今日全盘作业
            all_today = db.query(HomeworkItem).filter(
                HomeworkItem.student_id == student_id,
                HomeworkItem.date == today
            ).all()
            total_cnt = len(all_today)
            completed_cnt = sum(1 for it in all_today if it.is_completed)
            percent = int(completed_cnt / total_cnt * 100) if total_cnt > 0 else 0
            is_full = (completed_cnt == total_cnt and total_cnt > 0)

            reply_msg = (
                f"✅ 收到！已为您将【{matched_subj}】标记为已完成。\n"
                f"今日进度：{completed_cnt}/{total_cnt} 项 ({percent}%) {'🟢' if is_full else '🟡'}"
            )

            # 联动触发满卡喜报广播！
            if is_full:
                reply_msg += "\n\n🎉 太棒了！今日全部学科作业已 100% 满卡达成！系统已同步记录连续打卡天数！"
                # 异步向家庭所有绑定成员广播满卡战报
                try:
                    streak = calculate_streak(student_id, db)
                    summary_title = f"🎉【智学迹今日战报】{student_name} 今日作业满卡完成！({today_str})"
                    summary_content = (
                        f"🌟 **太棒了！今日所有作业均已完成满卡！**\n"
                        f"🔥 **连续打卡**：第 {streak} 天 ｜ 完成度：**100%** 🟢\n"
                        f"由 {sender_name} 在微信聊天框一键打卡收官！\n"
                        f"🌈 孩子今天表现非常自律专注，请及时给予鼓励！"
                    )
                    import asyncio
                    asyncio.create_task(
                        send_wechat_sandbox(
                            app_id=settings.WECHAT_APP_ID,
                            app_secret=settings.WECHAT_APP_SECRET,
                            template_id=settings.WECHAT_TEMPLATE_ID,
                            open_ids=settings.WECHAT_OPEN_IDS,
                            title=summary_title,
                            content=summary_content
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to async broadcast full-completion report: {e}")

            return reply_msg

    # 7. 意图：多科目批量录入作业 (如班级微信群复制粘贴的多科作业通知)
    batch_items = parse_batch_homework_text(raw_content, [s.name for s in subjects])
    if batch_items:
        added_count = 0
        skipped_count = 0
        added_by_subject: Dict[str, List[str]] = {}

        for subj_name, item_content in batch_items:
            # 查找或创建对应学科
            subject = db.query(Subject).filter(Subject.name == subj_name).first()
            if not subject:
                subject = db.query(Subject).filter(Subject.name.like(f"%{subj_name}%")).first()
            if not subject:
                subject = Subject(name=subj_name)
                db.add(subject)
                db.flush()

            # 查重：避免同一天录入完全重复的作业
            existing = db.query(HomeworkItem).filter(
                HomeworkItem.student_id == student_id,
                HomeworkItem.subject_id == subject.id,
                HomeworkItem.date == today,
                HomeworkItem.content == item_content
            ).first()

            if existing:
                skipped_count += 1
                continue

            new_item = HomeworkItem(
                student_id=student_id,
                subject_id=subject.id,
                date=today,
                content=item_content,
                is_completed=False
            )
            db.add(new_item)
            added_count += 1
            added_by_subject.setdefault(subject.name, []).append(item_content)

        db.commit()

        # 统计今日全盘作业总数
        total_now = db.query(HomeworkItem).filter(
            HomeworkItem.student_id == student_id,
            HomeworkItem.date == today
        ).count()

        if added_count == 0 and skipped_count > 0:
            return (
                f"💡 提示：检测到这批作业（共 {skipped_count} 项）今日此前已全部录入，无需重复添加！\n"
                f"回复【今日作业】可查阅当前清单，回复【学科 完成】可快速打卡。"
            )

        reply_lines = [f"📝 批量作业录入成功！本次新增 {added_count} 项作业：\n"]
        for sname, items_list in added_by_subject.items():
            reply_lines.append(f"【{sname}】({len(items_list)}项)")
            for idx, c in enumerate(items_list, 1):
                reply_lines.append(f"{idx}. {c}")
            reply_lines.append("")

        if skipped_count > 0:
            reply_lines.append(f"（注：另有 {skipped_count} 项作业今日已在清单中，已自动去重跳过）\n")

        reply_lines.append(f"📅 今日作业清单已更新（共 {total_now} 项）。")
        reply_lines.append("💪 孩子完成后，直接回复【学科 完成】即可快速打卡。")

        return "\n".join(reply_lines).strip()

    # 8. 未能识别指令时的友好容错反馈
    return (
        f"🤖 收到来自{sender_name}的消息：\n“{raw_content}”\n\n"
        f"未能准确识别指令。建议您：\n"
        f"· 回复【今日作业】查看清单与打卡状态\n"
        f"· 回复【数学 完成】完成对应学科打卡\n"
        f"· 回复【帮助】查看完整快捷指令指南"
    )
