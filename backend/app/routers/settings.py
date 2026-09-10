from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models import Subject
from backend.app.schemas import SubjectOut, SubjectCreate, SubjectUpdate
from backend.app.auth import verify_pin, change_pin, check_is_default_pin

router = APIRouter(prefix="/api/settings", tags=["系统设置与门禁"])


class PinVerifyIn(BaseModel):
    pin: str


class PinChangeIn(BaseModel):
    old_pin: str
    new_pin: str


@router.get("/subjects", response_model=List[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    """获取所有学科列表"""
    return db.query(Subject).order_by(Subject.sort_order.asc()).all()


@router.post("/subjects", response_model=SubjectOut)
def create_subject(sub_in: SubjectCreate, db: Session = Depends(get_db)):
    """新增或更新学科"""
    existing = db.query(Subject).filter(Subject.name == sub_in.name).first()
    if existing:
        existing.full_score = sub_in.full_score
        existing.sort_order = sub_in.sort_order
        db.commit()
        db.refresh(existing)
        return existing

    sub = Subject(
        name=sub_in.name,
        full_score=sub_in.full_score,
        sort_order=sub_in.sort_order,
        is_default=sub_in.is_default
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: int, sub_in: SubjectUpdate, db: Session = Depends(get_db)):
    """更新学科信息（支持修改满分分值与自定义学科名称）"""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="未找到该学科")
    if sub_in.full_score is not None:
        sub.full_score = sub_in.full_score
    if sub_in.name is not None and not sub.is_default:
        sub.name = sub_in.name
    if sub_in.sort_order is not None:
        sub.sort_order = sub_in.sort_order
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    """删除自定义学科（系统预置核心学科禁止删除）"""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="未找到该学科")
    if sub.is_default:
        raise HTTPException(status_code=400, detail="预置系统核心学科不可删除")
    db.delete(sub)
    db.commit()
    return {"status": "ok", "message": "学科已删除"}


@router.get("/pin-status")
def api_pin_status(db: Session = Depends(get_db)):
    """获取当前 PIN 是否为系统初始默认口令 (888888)"""
    return {"is_default_pin": check_is_default_pin(db)}


@router.post("/verify-pin")
def api_verify_pin(body: PinVerifyIn, db: Session = Depends(get_db)):
    """校验家长端进入 PIN 口令，并返回是否为默认口令"""
    verify_pin(body.pin, db)
    return {
        "status": "ok",
        "message": "口令校验成功",
        "is_default_pin": check_is_default_pin(db)
    }


@router.put("/pin")
def api_change_pin(body: PinChangeIn, db: Session = Depends(get_db)):
    """修改家长端进入 PIN 口令"""
    change_pin(body.old_pin, body.new_pin, db)
    return {"status": "ok", "message": "口令已成功修改"}


class OcrConfigIn(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


@router.get("/ocr-config")
def get_ocr_config():
    """获取当前生效的 OCR 引擎状态与云端视觉模型配置"""
    import os
    from backend.app.utils.ocr_service import _read_env_file, list_engines
    env = _read_env_file()
    key = os.getenv("OCR_CLOUD_API_KEY") or env.get("OCR_CLOUD_API_KEY", "")
    base_url = os.getenv("OCR_CLOUD_BASE_URL") or env.get(
        "OCR_CLOUD_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    )
    model = os.getenv("OCR_CLOUD_MODEL") or env.get("OCR_CLOUD_MODEL", "glm-4v-flash")

    masked = f"{key[:4]}...{key[-4:]}" if len(key) >= 10 else ("已配置" if key else "")
    engines_info = list_engines()
    return {
        "active_engine": engines_info["default"],
        "engines_detail": engines_info["detail"],
        "has_cloud_key": bool(key),
        "cloud_key_masked": masked,
        "cloud_base_url": base_url,
        "cloud_model": model,
    }


@router.put("/ocr-config")
def update_ocr_config(cfg: OcrConfigIn):
    """保存云端视觉模型配置到 data/.env 并实时热更新"""
    import os
    from pathlib import Path
    env_path = Path(__file__).resolve().parents[3] / "data" / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    new_lines = []
    for l in lines:
        s = l.strip()
        if s.startswith("OCR_CLOUD_API_KEY=") or s.startswith("OCR_CLOUD_BASE_URL=") or s.startswith("OCR_CLOUD_MODEL="):
            continue
        new_lines.append(l)

    if cfg.api_key is not None:
        new_key = cfg.api_key.strip()
        if new_key:
            new_lines.append(f"OCR_CLOUD_API_KEY={new_key}")
            os.environ["OCR_CLOUD_API_KEY"] = new_key
        else:
            os.environ.pop("OCR_CLOUD_API_KEY", None)

    if cfg.base_url:
        new_lines.append(f"OCR_CLOUD_BASE_URL={cfg.base_url.strip()}")
        os.environ["OCR_CLOUD_BASE_URL"] = cfg.base_url.strip()

    if cfg.model:
        new_lines.append(f"OCR_CLOUD_MODEL={cfg.model.strip()}")
        os.environ["OCR_CLOUD_MODEL"] = cfg.model.strip()

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"status": "ok", "message": "OCR配置已更新"}


