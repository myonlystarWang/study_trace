"""数学文本规范化 —— 自动化测试。

背景：云端视觉模型（glm-4v-flash 等）会用 `$…$`、`\\(…\\)` 等定界符包裹公式，
前端 MathText 不认这些定界符，于是「$」「\\」会作为可见字符残留在题干里
（用户实测反馈）。这里锁定 normalize_math_text 的清洗行为，以及
OCR 任务链路与错题入库链路确实调用了它。
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.utils.ocr_service import OcrLine, OcrResult
from backend.app.utils.math_text import normalize_math_text


# ---------------------------------------------------------------------------
# 1) 纯函数行为
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw, expected",
    [
        # 用户实测抓到的真实输出：\( \) 定界符 + 裸 LaTeX
        (
            r"1) \(|-\frac{5}{2}| - (-2.5) + 1 - |1 - \frac{5}{2}|\)",
            r"1) |-\frac{5}{2}| - (-2.5) + 1 - |1 - \frac{5}{2}|",
        ),
        # $…$ 定界符
        (
            r"Solve: $\frac{2}{x} + \frac{3}{(x+1)} = 1$",
            r"Solve: \frac{2}{x} + \frac{3}{(x+1)} = 1",
        ),
        # 中文里的行内 $…$
        ("一个数的相反数是 $-3$，则这个数是____。", "一个数的相反数是 -3，则这个数是____。"),
        # \[ \] 块级定界符 + 换行收敛
        ("\\[\nx = \\frac{-b}{2a}\n\\]", "x = \\frac{-b}{2a}"),
        # \left \right 这类纯排版命令去掉，竖线保留
        (r"\left| -2 \right| \times \dfrac{3}{4}", r"| -2 | \times \dfrac{3}{4}"),
        # \text{} 只留正文
        (r"\text{求} \ x \ \text{的值}", "求 x 的值"),
        # 幂等
        ("$\\frac{1}{2}$ 与 \\(\\frac{3}{4}\\) 比大小", None),
    ],
)
def test_normalize_strips_delimiters(raw, expected):
    out = normalize_math_text(raw)
    assert "$" not in out
    assert "\\(" not in out and "\\)" not in out
    assert "\\[" not in out and "\\]" not in out
    if expected is not None:
        assert out == expected


def test_normalize_is_idempotent():
    raw = r"Solve: $\frac{2}{x}$ 与 \(\sqrt{2}\) 比较"
    once = normalize_math_text(raw)
    assert normalize_math_text(once) == once


def test_normalize_preserves_renderable_commands():
    """可渲染命令必须原样保留，别把数学式子洗坏。"""
    raw = r"\frac{5}{4} + [-\frac{7}{3} - (\frac{7}{4} - \frac{5}{3})]"
    assert normalize_math_text(raw) == raw
    raw2 = r"|-2\frac{1}{2}| - (-2.5)+1-|1-2\frac{1}{2}|"
    assert normalize_math_text(raw2) == raw2


def test_normalize_drops_backslash_of_unknown_commands():
    """无法渲染的命令只丢反斜杠，命令名留作普通文字——绝不留裸露的「\\」。"""
    out = normalize_math_text(r"\unknowncmd{1} + \frac{1}{2}")
    assert "\\unknowncmd" not in out
    assert "unknowncmd{1}" in out
    assert r"\frac{1}{2}" in out


def test_normalize_empty_and_none():
    assert normalize_math_text(None) == ""
    assert normalize_math_text("") == ""


# ---------------------------------------------------------------------------
# 2) OCR 任务链路：识别结果入库前已被清洗
# ---------------------------------------------------------------------------
class _DelimiterStubEngine:
    """模拟云端视觉模型：返回带 \\( \\) 与 $ 定界符的 LaTeX。"""

    name = "StubVLM"

    def available(self) -> bool:
        return True

    def recognize(self, image):
        text = r"1) \(|-\frac{5}{2}|\) 且 $\frac{2}{x} = 1$"
        return OcrResult(
            lines=[OcrLine(text=text, confidence=1.0)],
            text=text,
            confidence=1.0,
            engine=self.name,
            cost_ms=1,
        )


def _poll(client: TestClient, tid: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/ocr/tasks/{tid}").json()
        if body["status"] in ("succeeded", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("OCR 任务未在超时内结束")


def test_ocr_task_output_is_cleaned(monkeypatch, tmp_path):
    from backend.app.utils import ocr_service

    monkeypatch.setattr(ocr_service, "get_ocr_engine", lambda mode="auto": _DelimiterStubEngine())

    png = tmp_path / "math.png"
    Image.new("RGB", (32, 32), "white").save(png)

    client = TestClient(app)
    r = client.post(
        "/api/ocr/tasks",
        files={"file": ("math.png", png.read_bytes(), "image/png")},
        data={"mode": "auto"},
    )
    assert r.status_code == 202
    body = _poll(client, r.json()["task_id"])
    assert body["status"] == "succeeded", body
    text = body["result"]["text"]
    assert "$" not in text
    assert "\\(" not in text and "\\)" not in text
    assert r"\frac{5}{2}" in text and r"\frac{2}{x}" in text


# ---------------------------------------------------------------------------
# 3) 错题入库链路：写入即清洗（含编辑保存）
# ---------------------------------------------------------------------------
def test_mistake_create_and_update_normalize_text():
    client = TestClient(app)
    subjects = client.get("/api/settings/subjects").json()
    subject_id = subjects[0]["id"] if subjects else 1

    created = client.post(
        "/api/mistakes",
        json={
            "subject_id": subject_id,
            "error_type": "计算错误",
            "extracted_text": r"计算 $\frac{5}{4} + (-\frac{7}{3})$ 的值",
            "answer": r"\(-\frac{1}{12}\)",
        },
    )
    assert created.status_code == 200, created.text
    rec = created.json()
    assert "$" not in rec["extracted_text"]
    assert rec["extracted_text"] == r"计算 \frac{5}{4} + (-\frac{7}{3}) 的值"
    assert rec["answer"] == r"-\frac{1}{12}"

    updated = client.put(
        f"/api/mistakes/{rec['id']}",
        json={"extracted_text": r"$\frac{1}{2}$ 与 \(\frac{3}{4}\) 比大小"},
    )
    assert updated.status_code == 200
    assert updated.json()["extracted_text"] == r"\frac{1}{2} 与 \frac{3}{4} 比大小"

    client.delete(f"/api/mistakes/{rec['id']}")


def test_mistake_create_keeps_none_answer():
    """answer 不填仍是 None，不能因为清洗被写成空串。"""
    client = TestClient(app)
    subjects = client.get("/api/settings/subjects").json()
    subject_id = subjects[0]["id"] if subjects else 1
    created = client.post(
        "/api/mistakes",
        json={"subject_id": subject_id, "extracted_text": "1+1=2"},
    )
    assert created.status_code == 200
    rec = created.json()
    assert rec["answer"] is None
    client.delete(f"/api/mistakes/{rec['id']}")
