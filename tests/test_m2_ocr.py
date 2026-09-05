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


def test_ocr_path_traversal_prevention():
    """安全防护：严禁任意本地路径穿越读取，越界路径必须返回 400。"""
    client = TestClient(app)

    # 1) 尝试读取系统敏感路径
    r1 = client.post("/api/ocr/tasks", data={"image_path": "C:/Windows/System32/drivers/etc/hosts"})
    assert r1.status_code == 400
    assert "非法或不存在" in r1.json()["detail"]

    # 2) 尝试相对路径穿越读取项目敏感配置
    r2 = client.post("/api/ocr/tasks", data={"image_path": "../../data/.env"})
    assert r2.status_code == 400

    # 3) 不存在的图片路径
    r3 = client.post("/api/ocr/tasks", data={"image_path": "originals/not_exist_file.png"})
    assert r3.status_code == 400


def test_ocr_storage_key_reuse_and_temp_cleanup(samples):
    """验证错题图 storage_key 路径复用与临时文件自动清理、全站备份防污染。"""
    client = TestClient(app)
    # 隔离本用例对 OCR_TEMP_DIR 的污染：其他用例（如 test_ocr_async_pipeline）
    # 上传文件会产生临时文件，且只在轮询到 succeeded 即结束，未必等 finally 删完。
    from backend.app.config import OCR_TEMP_DIR
    for f in OCR_TEMP_DIR.glob("*"):
        try:
            f.unlink()
        except Exception:
            pass
    data = samples["sample_chinese"].read_bytes()

    # 1. 错题图上传接口应返回 storage_key
    up_res = client.post(
        "/api/mistakes/upload",
        files={"file": ("chinese.png", data, "image/png")}
    )
    assert up_res.status_code == 200
    up_json = up_res.json()
    assert "storage_key" in up_json
    storage_key = up_json["storage_key"]
    assert storage_key.startswith("originals/")

    # 2. 通过 storage_key 发起 OCR 任务，无需二次上传
    task_res = client.post("/api/ocr/tasks", data={"image_path": storage_key})
    assert task_res.status_code == 202
    tid = task_res.json()["task_id"]

    final = None
    for _ in range(30):
        r = client.get(f"/api/ocr/tasks/{tid}")
        assert r.status_code == 200
        j = r.json()
        if j["status"] in ("succeeded", "failed"):
            final = j
            break
        time.sleep(0.2)

    assert final is not None
    assert final["status"] == "succeeded"
    assert "公园" in final["result"]["text"] or "孩子们" in final["result"]["text"]

    # 3. 验证临时文件自动删除：直接上传临时文件做 OCR
    from backend.app.config import OCR_TEMP_DIR
    temp_res = client.post(
        "/api/ocr/tasks",
        files={"file": ("temp_test.png", data, "image/png")}
    )
    assert temp_res.status_code == 202
    temp_tid = temp_res.json()["task_id"]

    for _ in range(30):
        r = client.get(f"/api/ocr/tasks/{temp_tid}")
        if r.json()["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.2)

    # 任务完成后，OCR_TEMP_DIR 中该任务的临时文件应已被删除
    time.sleep(0.2)  # 等待 finally 兜底清理（如有）落盘
    temp_files = list(OCR_TEMP_DIR.glob("*"))
    assert len(temp_files) == 0, f"临时文件未被清理: {temp_files}"

    # 4. 验证备份导出 Zip 中 100% 不包含 ocr_in 或 temp 临时目录
    import zipfile
    import io
    bk_res = client.get("/api/backup/export")
    assert bk_res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bk_res.content), "r") as zf:
        all_names = zf.namelist()
        for name in all_names:
            assert "ocr_in" not in name, f"备份中泄漏了 OCR 临时目录: {name}"
            assert "temp" not in name, f"备份中泄漏了 temp 目录: {name}"
        # 且正常的业务原图存在于备份中
        assert any(name.startswith("uploads/originals/") for name in all_names)


def test_mistake_consecutive_image_then_text_no_thumbnail_leak():
    """验证错题连续录入场景：第一条带图、第二条纯文本时，第二条记录绝不泄漏第一条的缩略图。"""
    client = TestClient(app)
    # 1. 录入带图错题
    r1 = client.post("/api/mistakes", json={
        "subject_id": 1,
        "source_reference": "周练 1",
        "error_type": "概念模糊",
        "extracted_text": "带图错题 1",
        "original_image_path": "/uploads/originals/test.jpg",
        "thumbnail_path": "/uploads/thumbnails/test.jpg"
    })
    assert r1.status_code == 200
    m1 = r1.json()
    assert m1["thumbnail_path"] == "/uploads/thumbnails/test.jpg"

    # 2. 紧接着录入纯文字错题（对应前端 resetModalState 之后的情况）
    r2 = client.post("/api/mistakes", json={
        "subject_id": 1,
        "source_reference": "周练 2",
        "error_type": "粗心大意",
        "extracted_text": "纯文字错题 2",
        "original_image_path": None,
        "thumbnail_path": None
    })
    assert r2.status_code == 200
    m2 = r2.json()
    assert m2["thumbnail_path"] is None
    assert m2["original_image_path"] is None

