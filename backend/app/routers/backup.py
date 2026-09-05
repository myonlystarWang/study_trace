import zipfile
import hashlib
import json
import io
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from backend.app.config import DATA_DIR, UPLOADS_DIR, BACKUPS_DIR

router = APIRouter(prefix="/api/backup", tags=["数据备份与恢复"])

DB_FILE = DATA_DIR / "study_trace.db"


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_backup_archive() -> Path:
    """打包数据库与全部上传文件，附带 sha256 清单"""
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUPS_DIR / f"study_trace_backup_{now_str}.zip"

    manifest = {
        "created_at": datetime.now().isoformat(),
        "version": "0.1.0",
        "files": {}
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. 打包 SQLite 数据库文件
        if DB_FILE.exists():
            arc_name = "study_trace.db"
            zipf.write(DB_FILE, arcname=arc_name)
            manifest["files"][arc_name] = compute_sha256(DB_FILE)

        # 2. 打包 uploads 目录全部文件
        if UPLOADS_DIR.exists():
            for file_path in UPLOADS_DIR.rglob("*"):
                if file_path.is_file():
                    arc_name = f"uploads/{file_path.relative_to(UPLOADS_DIR).as_posix()}"
                    zipf.write(file_path, arcname=arc_name)
                    manifest["files"][arc_name] = compute_sha256(file_path)

        # 3. 写入清单 manifest.json
        zipf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return zip_path


@router.get("/export")
def export_backup():
    """导出全站数据 Zip 包（包含 SQLite 与上传原图/缩略图）"""
    zip_path = create_backup_archive()
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_path.name
    )


@router.post("/import")
async def import_backup(file: UploadFile = File(...)):
    """从备份 Zip 包还原数据（还原前自动创建恢复前快照）"""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持导入 .zip 格式的备份包")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="备份文件内容为空")

    # 1. 恢复前自动创建快照
    snapshot_path = create_backup_archive()

    # 2. 检查并解压备份包
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zipf:
            file_names = zipf.namelist()
            if "study_trace.db" not in file_names:
                raise HTTPException(status_code=400, detail="无效的备份文件：缺失 study_trace.db")

            # 3. 释放数据库
            zipf.extract("study_trace.db", path=str(DATA_DIR))

            # 4. 释放 uploads 文件
            for name in file_names:
                if name.startswith("uploads/") and not name.endswith("/"):
                    rel_path = name[len("uploads/"):]
                    target_file = UPLOADS_DIR / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with zipf.open(name) as src, open(target_file, "wb") as dst:
                        shutil.copyfileobj(src, dst)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="解压失败：损坏的 zip 文件")

    return {
        "status": "ok",
        "message": "数据已成功导入并还原",
        "pre_restore_snapshot": snapshot_path.name
    }
