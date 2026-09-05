"""可插拔三引擎 OCR 抽象层。

默认 RapidOCR（本地离线、CPU、零联网），备选 PaddleOCR（用户指定退路），
兜底 CloudVLM（智谱 glm-4v-flash 等免费视觉模型，需 Key）。
通过 ``get_ocr_engine(mode="auto")`` 按可用顺序自动降级探测。
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from PIL import Image

# 图片输入：路径字符串 / Path / 已打开的 PIL 图像
ImageInput = Union[str, Path, Image.Image]

# CloudVLM 默认配置（智谱 GLM-4V-Flash，永久免费档）
_CLOUD_DEFAULT_BASE = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
_CLOUD_DEFAULT_MODEL = "glm-4v-flash"

# 云端 Key 存放位置（绝不进 Git / 绝不下发前端）
_ENV_PATH = Path(__file__).resolve().parents[3] / "data" / ".env"


def _read_env_file() -> dict:
    """极简解析 data/.env（KEY=VALUE，忽略 # 注释与空白行）。"""
    if not _ENV_PATH.exists():
        return {}
    out: dict = {}
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


@dataclass
class OcrLine:
    text: str
    confidence: float
    box: List[List[int]] = field(default_factory=list)


@dataclass
class OcrResult:
    lines: List[OcrLine]
    text: str
    confidence: float
    engine: str
    cost_ms: int = 0

    @classmethod
    def from_rapid(cls, raw: Optional[list], engine_name: str = "RapidOCR") -> "OcrResult":
        """将 RapidOCR 原始输出 [ [box, text, conf], ... ] 转标准结构。"""
        lines: List[OcrLine] = []
        confs: List[float] = []
        for item in raw or []:
            box_raw, text, conf = item[0], item[1], item[2]
            box = [[int(p[0]), int(p[1])] for p in box_raw]
            conf_f = float(conf)
            lines.append(OcrLine(text=str(text), confidence=conf_f, box=box))
            confs.append(conf_f)
        full = "\n".join(l.text for l in lines)
        avg = round(sum(confs) / len(confs), 4) if confs else 0.0
        return cls(lines=lines, text=full, confidence=avg, engine=engine_name, cost_ms=0)

    @classmethod
    def from_paddle(cls, raw: Optional[list], engine_name: str = "PaddleOCR") -> "OcrResult":
        """PaddleOCR 2.x ocr() 返回 [[ [box], ("text", conf) ], ...]。"""
        lines: List[OcrLine] = []
        confs: List[float] = []
        for block in raw or []:
            if not block:
                continue
            box_raw, (text, conf) = block[0], block[1]
            box = [[int(p[0]), int(p[1])] for p in box_raw]
            conf_f = float(conf)
            lines.append(OcrLine(text=str(text), confidence=conf_f, box=box))
            confs.append(conf_f)
        full = "\n".join(l.text for l in lines)
        avg = round(sum(confs) / len(confs), 4) if confs else 0.0
        return cls(lines=lines, text=full, confidence=avg, engine=engine_name, cost_ms=0)


class BaseOCREngine(ABC):
    name: str = "base"

    @abstractmethod
    def recognize(self, image: ImageInput) -> OcrResult:
        ...

    @staticmethod
    def _load_image(image: ImageInput) -> Image.Image:
        if isinstance(image, Image.Image):
            return image.convert("RGB")
        return Image.open(image).convert("RGB")

    def available(self) -> bool:
        """引擎当前是否可用（子类可覆盖做前置探测）。"""
        return True


# ---------------------------------------------------------------------------
# 1) RapidOCR —— 默认引擎（本地离线、纯 CPU）
# ---------------------------------------------------------------------------
class RapidOCREngine(BaseOCREngine):
    name = "RapidOCR"
    _singleton = None  # 惰性单例，避免重复加载 ~180MB 模型

    def __init__(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as e:  # 包未安装时平滑失败
            raise RuntimeError("RapidOCR 未安装") from e
        if RapidOCREngine._singleton is None:
            RapidOCREngine._singleton = RapidOCR()
        self._engine = RapidOCREngine._singleton

    def recognize(self, image: ImageInput) -> OcrResult:
        t0 = time.time()
        img = self._load_image(image)
        raw, _ = self._engine(img)
        cost = int((time.time() - t0) * 1000)
        res = OcrResult.from_rapid(raw, self.name)
        res.cost_ms = cost
        return res


# ---------------------------------------------------------------------------
# 2) PaddleOCR —— 用户指定可选退路（动态导入，不污染主依赖）
# ---------------------------------------------------------------------------
class PaddleOCREngine(BaseOCREngine):
    name = "PaddleOCR"

    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR  # noqa: F401
        except ImportError as e:
            raise RuntimeError("PaddleOCR 未安装") from e
        self._cls = PaddleOCR
        self._engine = None

    def recognize(self, image: ImageInput) -> OcrResult:
        if self._engine is None:
            self._engine = self._cls(use_angle_cls=True, lang="ch", show_log=False)
        t0 = time.time()
        if isinstance(image, (str, Path)):
            raw = self._engine.ocr(str(image), cls=True)
        else:
            raw = self._engine.ocr(self._load_image(image), cls=True)
        cost = int((time.time() - t0) * 1000)
        # PaddleOCR 多图返回 list[per_image]，单图取 [0]
        data = raw[0] if raw and isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
        res = OcrResult.from_paddle(data, self.name)
        res.cost_ms = cost
        return res


# ---------------------------------------------------------------------------
# 3) CloudVLM —— 云端大模型视觉兜底（需 Key，联网）
# ---------------------------------------------------------------------------
class CloudVLMEngine(BaseOCREngine):
    name = "CloudVLM"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        env = _read_env_file()
        self.api_key = api_key or os.getenv("OCR_CLOUD_API_KEY") or env.get("OCR_CLOUD_API_KEY")
        self.base_url = base_url or os.getenv("OCR_CLOUD_BASE_URL") or env.get(
            "OCR_CLOUD_BASE_URL", _CLOUD_DEFAULT_BASE
        )
        self.model = model or os.getenv("OCR_CLOUD_MODEL") or env.get(
            "OCR_CLOUD_MODEL", _CLOUD_DEFAULT_MODEL
        )

    def available(self) -> bool:
        return bool(self.api_key)

    def recognize(self, image: ImageInput) -> OcrResult:
        if not self.available():
            raise RuntimeError("未配置云端 OCR Key（OCR_CLOUD_API_KEY）")
        t0 = time.time()
        img = self._load_image(image)
        import io

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_uri = f"data:image/png;base64,{b64}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请仅提取图片中的题目/文字内容，按原换行输出纯文本，不要解释、不要翻译、不要补充答案。",
                        },
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        }
        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = body["choices"][0]["message"]["content"].strip()
        except Exception as e:  # 网络/接口异常 → 抛出让上层降级
            raise RuntimeError(f"CloudVLM 调用失败: {e}") from e

        cost = int((time.time() - t0) * 1000)
        line = OcrLine(text=text, confidence=1.0)
        return OcrResult(lines=[line], text=text, confidence=1.0, engine=self.name, cost_ms=cost)


# ---------------------------------------------------------------------------
# 降级工厂
# ---------------------------------------------------------------------------
def _try_build(cls, *args):
    try:
        eng = cls(*args)
        if eng.available():
            return eng
    except Exception:
        return None
    return None


def get_ocr_engine(mode: str = "auto") -> BaseOCREngine:
    """按模式返回 OCR 引擎，auto 下自动探测降级。

    降级顺序：RapidOCR -> PaddleOCR -> CloudVLM(若已配 Key) -> 抛错(需手动输入)
    """
    if mode == "rapid":
        e = _try_build(RapidOCREngine)
        if e:
            return e
        raise RuntimeError("RapidOCR 不可用")
    if mode == "paddle":
        e = _try_build(PaddleOCREngine)
        if e:
            return e
        raise RuntimeError("PaddleOCR 不可用")
    if mode == "cloud":
        e = _try_build(CloudVLMEngine)
        if e:
            return e
        raise RuntimeError("CloudVLM 未配置 Key")
    # auto
    for cls in (RapidOCREngine, PaddleOCREngine, CloudVLMEngine):
        e = _try_build(cls)
        if e:
            return e
    raise RuntimeError("所有 OCR 引擎均不可用，请使用手动输入")


def list_engines() -> dict:
    """返回各引擎可用状态，供 /api/ocr/engines 使用。"""
    out = {}
    for cls in (RapidOCREngine, PaddleOCREngine, CloudVLMEngine):
        try:
            eng = cls()
            out[eng.name] = "available" if eng.available() else "no_key"
        except Exception:
            out[cls.name] = "not_installed"
    # 推断默认引擎
    default = "ManualFallback"
    for cls in (RapidOCREngine, PaddleOCREngine, CloudVLMEngine):
        e = _try_build(cls)
        if e:
            default = e.name
            break
    return {"default": default, "detail": out}
