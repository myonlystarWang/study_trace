"""M2 OCR 识别接入 —— 自动化测试。

覆盖：RapidOCR 直接识别准确度、异步任务全链路轮询、引擎不可用时的优雅降级、缺失任务 404。
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.utils.ocr_service import RapidOCREngine, get_ocr_engine
from tests.samples.generate_test_samples import make_samples


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    d = tmp_path_factory.mktemp("ocr_samples")
    paths = make_samples(d)
    return {p.stem: p for p in paths}


# ---------------------------------------------------------------------------
def test_rapid_ocr_direct(samples):
    """RapidOCR 直接识别：中文印刷体应高召回。"""
    eng = RapidOCREngine()
    res = eng.recognize(samples["sample_math"])
    assert res.engine == "RapidOCR"
    assert res.text.strip()
    # 数学样本关键语义应被保真提取（忽略空格/上标/同形字 x↔× 等排版差异）
    assert "解方程" in res.text
    # 字母 x 与乘号 × 同形，OCR 可能混淆——二者任一出现即视为识别成功
    assert ("x" in res.text) or ("×" in res.text)
    # 关键数字应被提取
    assert "13" in res.text and "15" in res.text
    # 整图字符平均置信度应较高
    assert res.confidence >= 0.80
    # 速度基线（单图 ≤ 2s，宽松上限 5s 防首跑抖动）
    assert res.cost_ms < 5000


def test_ocr_async_pipeline(samples):
    """POST /api/ocr/tasks -> 轮询 GET 直至 succeeded。"""
    client = TestClient(app)
    data = samples["sample_chinese"].read_bytes()
    r = client.post(
        "/api/ocr/tasks",
        files={"file": ("sample_chinese.png", data, "image/png")},
    )
    assert r.status_code == 202
    tid = r.json()["task_id"]

    final = None
    for _ in range(30):
        r = client.get(f"/api/ocr/tasks/{tid}")
        assert r.status_code == 200
        j = r.json()
        if j["status"] in ("succeeded", "failed"):
            final = j
            break
        time.sleep(0.3)

    assert final is not None, "轮询超时，任务未结束"
    assert final["status"] == "succeeded"
    assert final["engine"] == "RapidOCR"
    assert final["result"]["text"].strip()
    assert "孩子们" in final["result"]["text"] or "公园" in final["result"]["text"]


def test_ocr_engine_fallback():
    """不可用引擎应安全降级，不崩进程。"""
    # 1) 显式请求未安装的 PaddleOCR -> 抛错（工厂感知）
    with pytest.raises(RuntimeError):
        get_ocr_engine("paddle")

    # 2) 通过 API 以 paddle 模式提交 -> 任务优雅失败（非 500 崩溃）
    client = TestClient(app)
    # 构造一张极小合法 PNG 作为占位（引擎会在初始化阶段即失败）
    img = Image.new("RGB", (60, 20), "white")
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = client.post(
        "/api/ocr/tasks",
        files={"file": ("x.png", buf.getvalue(), "image/png")},
        data={"mode": "paddle"},
    )
    assert r.status_code == 202
    tid = r.json()["task_id"]
    final = None
    for _ in range(20):
        r = client.get(f"/api/ocr/tasks/{tid}")
        j = r.json()
        if j["status"] in ("succeeded", "failed"):
            final = j
            break
        time.sleep(0.2)
    assert final is not None
    assert final["status"] == "failed"
    assert final["error"]  # 错误信息存在，前端据此引导手动输入


def test_task_missing():
    """查询不存在的任务 ID -> 404。"""
    client = TestClient(app)
    r = client.get("/api/ocr/tasks/does-not-exist")
    assert r.status_code == 404


def test_engines_status():
    """引擎状态接口应正确反映可用情况。"""
    client = TestClient(app)
    r = client.get("/api/ocr/engines")
    assert r.status_code == 200
    j = r.json()
    assert j["default"] == "RapidOCR"
    assert j["detail"]["RapidOCR"] == "available"
