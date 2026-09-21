"""StudyTrace local MCP server (stdio).

Lets an AI agent (WorkBuddy / Doubao desktop / Antigravity) record homework
and mistakes directly into the running StudyTrace FastAPI backend
(http://127.0.0.1:28000) WITHOUT manual text escaping or image cropping.

Design notes (verified against backend code 2026-09-17):
- Agent pre-recognizes images; tools accept TEXT only. No OCR latency.
- subject_id is a NOT NULL FK, so every write tool resolves a subject NAME
  to its id via get_meta() first.
- MistakeRecord has NO "question type" (题型) field; error_type means the
  REASON for the mistake (概念模糊/粗心大意/思路卡壳/计算错误), not 题型.
- Backend auto-runs normalize_math_text on extracted_text/answer at insert,
  but it does NOT strip markdown ``` fences, so we strip them here too.
- Homework date is required; default to Asia/Shanghai "today".
- Local single-user: no auth needed (backend has no global PIN gate).
"""

import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from fastmcp import FastMCP

API_BASE = os.environ.get("STUDYTRACE_API_BASE", "http://127.0.0.1:28000").rstrip("/")
SH_TZ = ZoneInfo("Asia/Shanghai")

ERROR_TYPES = ["概念模糊", "粗心大意", "思路卡壳", "计算错误"]
SOURCE_TYPES = ["homework", "exam", "exercise"]
MASTERY_STATUSES = ["未掌握", "待复习", "已掌握"]

mcp = FastMCP("study_trace")

_subject_cache = None


def _today_sh() -> date:
    return datetime.now(SH_TZ).date()


def _get(path: str, params: dict | None = None):
    r = httpx.get(f"{API_BASE}{path}", params=params, timeout=20, trust_env=False)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict):
    r = httpx.post(f"{API_BASE}{path}", json=body, timeout=30, trust_env=False)
    r.raise_for_status()
    return r.json()


def _strip_fence(text: str | None) -> str | None:
    if not text:
        return text
    text = text.strip()
    m = re.match(r"^```(?:[a-zA-Z]+)?\n(.*)\n```$", text, re.S)
    if m:
        text = m.group(1).strip()
    return text


def _load_subjects():
    global _subject_cache
    if _subject_cache is None:
        _subject_cache = _get("/api/settings/subjects")
    return _subject_cache


def _resolve_subject(name: str):
    """Resolve a subject name (free text from the agent) to (id, display_name)."""
    subjects = _load_subjects()
    norm = name.replace("课", "").strip()

    # exact match
    for s in subjects:
        if s["name"] == name:
            return s["id"], s["name"]
    # match ignoring the suffix "课"
    for s in subjects:
        if s["name"].replace("课", "").strip() == norm:
            return s["id"], s["name"]
    # substring match (unique)
    hits = [
        s for s in subjects
        if norm in s["name"].replace("课", "").strip()
        or s["name"].replace("课", "").strip() in norm
    ]
    if len(hits) == 1:
        return hits[0]["id"], hits[0]["name"]

    available = ", ".join(s["name"] for s in subjects) or "(科目表为空)"
    raise ValueError(
        f"未找到学科「{name}」。请先用 get_meta() 查看可用科目，当前有：{available}"
    )


@mcp.tool()
def get_meta() -> str:
    """列出录入前必须参考的元信息：科目表（含 id）与所有枚举选项。

    每次录入作业/错题前，agent 必须先调用本工具确认科目名称与枚举取值，
    避免 subject 名称写错或 error_type 取值非法导致入库失败。
    """
    subjects = _load_subjects()
    lines = ["# 科目表（subject 用名称，工具内部解析为 id）"]
    for s in subjects:
        lines.append(f"- {s['name']} (id={s['id']})")
    lines.append("")
    lines.append("# 枚举选项")
    lines.append(f"error_type（错误原因，不是题型）: {ERROR_TYPES}")
    lines.append(f"source_type: {SOURCE_TYPES}")
    lines.append(f"mastery_status: {MASTERY_STATUSES}")
    return "\n".join(lines)


@mcp.tool()
def add_homework(subject: str, content: str, date: str = None,
                 is_completed: bool = False) -> str:
    """录入一条作业打卡。

    Args:
        subject: 学科名称（如「数学」「英语」），工具解析为库内 id。
        content: 作业内容纯文本（agent 已识别图片，无需传图）。
        date: 日期 YYYY-MM-DD，默认今天（Asia/Shanghai）。
        is_completed: 是否标记已完成，默认 False。
    """
    sid, sname = _resolve_subject(subject)
    d = date or str(_today_sh())
    body = {
        "subject_id": sid,
        "date": d,
        "content": content,
        "is_completed": is_completed,
    }
    out = _post("/api/homework", body)
    mark = "已完成" if out.get("is_completed") else "未完成"
    return f"已添加作业 #{out['id']}（{sname} {d} {mark}）：{content}"


@mcp.tool()
def add_mistake(subject: str, extracted_text: str, answer: str = None,
                error_type: str = None, source_type: str = "homework",
                source_reference: str = None) -> str:
    """录入一条错题（纯文本，图片已在前端识别）。

    Args:
        subject: 学科名称，工具解析为库内 id。
        extracted_text: 题干/错题内容纯文本（去掉 ``` 围栏与 LaTeX 定界符）。
        answer: 正确答案纯文本，可选。
        error_type: 错误原因（不是题型），可选值见 get_meta。
        source_type: 来源，默认 homework；可选 homework/exam/exercise。
        source_reference: 来源定位（如「七下 P23 第5题」），可选。
    """
    sid, sname = _resolve_subject(subject)
    if error_type and error_type not in ERROR_TYPES:
        return f"error_type 非法：{error_type}。可选：{ERROR_TYPES}"
    if source_type not in SOURCE_TYPES:
        return f"source_type 非法：{source_type}。可选：{SOURCE_TYPES}"

    body = {
        "subject_id": sid,
        "extracted_text": _strip_fence(extracted_text),
        "answer": _strip_fence(answer),
        "error_type": error_type,
        "source_type": source_type,
        "source_reference": source_reference,
    }
    body = {k: v for k, v in body.items() if v is not None}
    out = _post("/api/mistakes", body)
    return (
        f"已添加错题 #{out['id']}（{sname} | error_type={out.get('error_type')} "
        f"| mastery={out.get('mastery_status')} | 下次复习 {out.get('next_review_date')}）"
    )


@mcp.tool()
def get_today_homework(date: str = None) -> str:
    """查询某天（默认今天）的作业清单与完成率、连续打卡天数。

    Args:
        date: 日期 YYYY-MM-DD，默认今天（Asia/Shanghai）。
    """
    d = date or str(_today_sh())
    data = _get("/api/homework", params={"date": d})
    items = data.get("items", [])
    lines = [
        f"# {d} 作业：共{data.get('total')} 完成{data.get('completed')} "
        f"完成率{data.get('rate')}% 连续打卡{data.get('streak')}天"
    ]
    for it in items:
        mark = "✅" if it.get("is_completed") else "⬜"
        lines.append(f"{mark} [{it.get('subject_name')}] {it.get('content')}")
    return "\n".join(lines)


@mcp.tool()
def get_recent_mistakes(limit: int = 20, subject: str = None,
                        search: str = None) -> str:
    """查询最近错题，用于去重核对或复习回顾。

    Args:
        limit: 返回条数上限，默认 20。
        subject: 按学科名称过滤（可选）。
        search: 按题干关键词模糊搜索（可选）。
    """
    params = {}
    if subject:
        sid, _ = _resolve_subject(subject)
        params["subject_id"] = sid
    if search:
        params["search"] = search
    data = _get("/api/mistakes", params=params)
    data = data[:limit]
    lines = [f"# 最近错题（显示 {len(data)} 条）"]
    for r in data:
        snippet = (r.get("extracted_text") or "").replace("\n", " ")[:50]
        lines.append(
            f"- #{r['id']} [{r.get('subject_name')}] "
            f"{r.get('error_type') or '-'} | {r.get('mastery_status')} | {snippet}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # stdio transport
