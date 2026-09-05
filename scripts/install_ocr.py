"""M2 OCR 环境自检与可选引擎检测。

用法：
    python scripts/install_ocr.py

退出码：
    0  —— RapidOCR 可用（满足 M2 最低要求）
    1  —— 所有引擎均不可用（需排查 RapidOCR 安装或改用云端 Key）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# data/.env 路径（云端 Key 存放处，绝不进 Git）
_ENV_PATH = Path(__file__).resolve().parents[1] / "data" / ".env"


def _check_rapid() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
        import onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _check_paddle() -> bool:
    try:
        import paddleocr  # noqa: F401
        return True
    except Exception:
        return False


def _check_cloud_key() -> bool:
    if os.getenv("OCR_CLOUD_API_KEY"):
        return True
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("OCR_CLOUD_API_KEY") and "=" in line:
                return bool(line.split("=", 1)[1].strip())
    return False


def main() -> int:
    # 尝试将标准输出重置为 UTF-8，若环境不支持则优雅回退
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    rapid = _check_rapid()
    paddle = _check_paddle()
    cloud = _check_cloud_key()

    print("=== 学迹 StudyTrace · OCR 环境自检 ===")
    print(f"  RapidOCR (默认/本地离线) : {'[OK] 可用' if rapid else '[MISSING] 未安装'}")
    print(f"  PaddleOCR (可选退路)     : {'[OK] 已安装' if paddle else '[-] 未安装（可选）'}")
    print(f"  CloudVLM  (云端兜底)     : {'[OK] 已配置 Key' if cloud else '[-] 未配置 Key（可选）'}")
    print()

    if rapid:
        print("结论：默认引擎 RapidOCR 就绪，无需联网即可识别。")
        return 0
    if cloud:
        print("结论：本地 RapidOCR 缺失，但云端 Key 已配置，可走 CloudVLM 兜底（需联网）。")
        return 0
    print("结论：所有 OCR 引擎均不可用。请执行 `uv pip install rapidocr-onnxruntime` 或配置云端 Key。")
    print("       应用仍可运行，识别功能将引导用户手动输入。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
