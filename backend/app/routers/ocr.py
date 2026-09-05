"""OCR 异步任务 API。

设计要点：
- 图片上传即返回 task_id（202），线程池异步推理，前端轮询进度，避免大图阻塞移动端。
- 进程内 TASK_CACHE 字典，带 1 小时过期清理（单机家庭部署足够）。
- 引擎通过 ocr_service.get_ocr_engine 自动降级，单图失败不影响整体。
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.config import UPLOADS_DIR
from backend.app.schemas import OcrEnginesOut, OcrResultOut, OcrTaskOut
from backend.app.utils import ocr_service
from backend.app.utils.ocr_service import OcrResult

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

# 最大并发 2，保护宿主机 CPU 占用
_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_TASK_LOCK = threading.Lock()
TASK_CACHE: dict[str, dict] = {}
_TASK_TTL = 3600  # 1 小时过期

OCR_IN_DIR = UPLOADS_DIR / "ocr_in"
OCR_IN_DIR.mkdir(parents=True, exist_ok=True)


def _purge_expired() -> None:
    now = time.time()
    expired = [tid for tid, t in TASK_CACHE.items() if now - t["created_at"] > _TASK_TTL]
    for tid in expired:
        TASK_CACHE.pop(tid, None)


def _result_to_out(res: OcrResult) -> OcrResultOut:
    return OcrResultOut(
        lines=[{"text": l.text, "confidence": l.confidence, "box": l.box} for l in res.lines],
        text=res.text,
        confidence=res.confidence,
        engine=res.engine,
        cost_ms=res.cost_ms,
    )


def _run_task(task_id: str, image_path: str, mode: str) -> None:
    task = TASK_CACHE.get(task_id)
    if task is None:
        return
    task["status"] = "processing"
    task["progress"] = 10
    try:
        engine = ocr_service.get_ocr_engine(mode)
        task["engine"] = engine.name
        task["progress"] = 50
        result = engine.recognize(image_path)
        task["result"] = result
        task["cost_ms"] = result.cost_ms
        task["status"] = "succeeded"
        task["progress"] = 100
    except Exception as e:  # 引擎不可用 / 识别异常 → 标记失败，由前端引导手动输入
        task["status"] = "failed"
        task["error"] = str(e)
        task["progress"] = 100


class OcrSubmitByPath(BaseModel):
    image_path: str
    mode: str = "auto"


@router.post("/tasks", response_model=OcrTaskOut, status_code=202)
def create_task(
    file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
    mode: str = Form("auto"),
):
    """提交 OCR 任务：上传图片（Form File）或传入已存在图片路径。"""
    _purge_expired()

    if file is not None:
        # 保存上传图片到 ocr_in 目录（data/ 已 gitignore）
        ext = Path(file.filename or "upload.png").suffix or ".png"
        dest = OCR_IN_DIR / f"{uuid.uuid4().hex}{ext}"
        dest.write_bytes(file.file.read())
        src = str(dest)
    elif image_path:
        src = image_path
        if not Path(src).exists():
            raise HTTPException(status_code=400, detail="image_path 不存在")
    else:
        raise HTTPException(status_code=400, detail="需提供 file 或 image_path")

    task_id = uuid.uuid4().hex
    with _TASK_LOCK:
        TASK_CACHE[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "engine": None,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "cost_ms": None,
        }
    _EXECUTOR.submit(_run_task, task_id, src, mode)
    return OcrTaskOut(**TASK_CACHE[task_id])


@router.get("/tasks/{task_id}", response_model=OcrTaskOut)
def get_task(task_id: str):
    """轮询任务状态；完成后返回结构化识别文本与耗时。"""
    _purge_expired()
    task = TASK_CACHE.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    out = dict(task)
    if isinstance(out.get("result"), OcrResult):
        out["result"] = _result_to_out(out["result"])
    return OcrTaskOut(**out)


@router.get("/engines", response_model=OcrEnginesOut)
def get_engines():
    """返回各引擎可用状态与当前默认引擎。"""
    return OcrEnginesOut(**ocr_service.list_engines())
