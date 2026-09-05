from datetime import datetime, timedelta
import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import Setting
from backend.app.config import settings

# 内存级临时防爆破记录（进程内）
_auth_state = {
    "failed_attempts": 0,
    "locked_until": None
}


def verify_pin(pin: str, db: Session) -> bool:
    """校验家长门禁 PIN，连续 5 次错误锁定 5 分钟"""
    now = datetime.now()
    
    # 1. 检查是否处于锁定状态
    if _auth_state["locked_until"] and now < _auth_state["locked_until"]:
        remaining = int((_auth_state["locked_until"] - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"门禁已连续输错锁定中，请在 {remaining} 秒后再试"
        )
    
    # 2. 获取数据库存储的哈希
    pin_setting = db.query(Setting).filter(Setting.key == "parent_pin_hash").first()
    if not pin_setting:
        # 若未初始化，写入默认口令
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(settings.DEFAULT_PIN.encode("utf-8"), salt).decode("utf-8")
        pin_setting = Setting(key="parent_pin_hash", value=hashed)
        db.add(pin_setting)
        db.commit()
        db.refresh(pin_setting)

    stored_hash = pin_setting.value.encode("utf-8")

    # 3. 校验口令
    if bcrypt.checkpw(pin.encode("utf-8"), stored_hash):
        _auth_state["failed_attempts"] = 0
        _auth_state["locked_until"] = None
        return True
    else:
        _auth_state["failed_attempts"] += 1
        remaining_chances = max(0, 5 - _auth_state["failed_attempts"])
        if _auth_state["failed_attempts"] >= 5:
            _auth_state["locked_until"] = now + timedelta(minutes=5)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="口令已连续输错 5 次，门禁已自动锁定 5 分钟"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"口令错误，还剩 {remaining_chances} 次机会"
        )


def change_pin(old_pin: str, new_pin: str, db: Session) -> bool:
    """修改家长门禁口令"""
    verify_pin(old_pin, db)
    if len(new_pin) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新口令长度至少需 4 位"
        )
    
    salt = bcrypt.gensalt()
    new_hash = bcrypt.hashpw(new_pin.encode("utf-8"), salt).decode("utf-8")
    
    pin_setting = db.query(Setting).filter(Setting.key == "parent_pin_hash").first()
    pin_setting.value = new_hash
    db.commit()
    return True
