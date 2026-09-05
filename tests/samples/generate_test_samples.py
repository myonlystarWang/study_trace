"""生成 M2 OCR 基准测试样本（初中印刷体题干）。

3 类典型样本：
  1. 语文/英语：纯文本印刷体题干
  2. 数学：一元一次方程、整式运算题干
  3. 综合：含题号、小题与填空下划线的标准题目

用法：
    python tests/samples/generate_test_samples.py [输出目录]
默认输出到本脚本同目录（tests/samples/）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SAMPLES = [
    ("sample_chinese.png", "在公园里，孩子们快乐地玩耍。", (700, 160)),
    (
        "sample_math.png",
        "解方程：2x + 5 = 13，求 x 的值。\n若 a = 3，则 a² + 2a = 15。",
        (700, 220),
    ),
    (
        "sample_comprehensive.png",
        "1. 计算：3 + 4 = ____\n2. 填空：5 × 6 = ____\n3. 选择：下列属于奇数的是（ ）。",
        (700, 280),
    ),
]


def _font(size: int = 30):
    for path in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_samples(dest_dir: Path) -> list[Path]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    font = _font(30)
    paths: list[Path] = []
    for name, text, size in SAMPLES:
        img = Image.new("RGB", size, "white")
        d = ImageDraw.Draw(img)
        y = 30
        for line in text.split("\n"):
            d.text((20, y), line, fill="black", font=font)
            y += 60
        p = dest_dir / name
        img.save(p, format="PNG")
        paths.append(p)
    return paths


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    made = make_samples(out)
    for p in made:
        print(f"generated: {p} ({p.stat().st_size} bytes)")
