import hashlib
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageOps
import io
from backend.app.config import ORIGINALS_DIR, THUMBNAILS_DIR


def save_image_bytes(image_bytes: bytes, filename: str = "image.jpg") -> Tuple[str, str, str]:
    """
    保存图片二进制数据，按 sha256[:2] 分目录落盘，同名/同内容去重。
    返回: (sha256_hash, relative_original_path, relative_thumbnail_path)
    例如: ("a1b2...", "/uploads/originals/a1/a1b2....jpg", "/uploads/thumbnails/a1/a1b2....jpg")
    """
    # 1. 计算 sha256 哈希
    sha256_hash = hashlib.sha256(image_bytes).hexdigest()
    sub_dir = sha256_hash[:2]

    # 确定文件后缀（默认 jpg）
    ext = Path(filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"
    
    file_name = f"{sha256_hash}{ext}"
    
    # 2. 目标路径
    orig_dir = ORIGINALS_DIR / sub_dir
    thumb_dir = THUMBNAILS_DIR / sub_dir
    orig_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    
    orig_file = orig_dir / file_name
    thumb_file = thumb_dir / file_name
    
    rel_orig_url = f"/uploads/originals/{sub_dir}/{file_name}"
    rel_thumb_url = f"/uploads/thumbnails/{sub_dir}/{file_name}"

    # 3. 若原图已存在（内容完全一致），直接复用，实现秒传和去重
    if orig_file.exists() and thumb_file.exists():
        return sha256_hash, rel_orig_url, rel_thumb_url

    # 4. 打开图片并自动按 EXIF 旋转矫正
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # 5. 保存原图（长边控制在 <= 1600px，压缩质量 85%）
    orig_image = image.copy()
    orig_image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    orig_image.save(orig_file, format="JPEG", quality=85, optimize=True)

    # 6. 生成并保存缩略图（长边 <= 320px，用于移动端极速列表展示）
    thumb_image = image.copy()
    thumb_image.thumbnail((320, 320), Image.Resampling.LANCZOS)
    thumb_image.save(thumb_file, format="JPEG", quality=75, optimize=True)

    return sha256_hash, rel_orig_url, rel_thumb_url
