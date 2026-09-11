from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 根目录与关键路径定位
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
ORIGINALS_DIR = UPLOADS_DIR / "originals"
THUMBNAILS_DIR = UPLOADS_DIR / "thumbnails"
EXPORTS_DIR = DATA_DIR / "exports"
BACKUPS_DIR = DATA_DIR / "backups"
TEMP_DIR = DATA_DIR / "temp"
OCR_TEMP_DIR = TEMP_DIR / "ocr_in"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

import secrets

# 自动确保数据持久化与临时目录存在
for d in [DATA_DIR, UPLOADS_DIR, ORIGINALS_DIR, THUMBNAILS_DIR, EXPORTS_DIR, BACKUPS_DIR, TEMP_DIR, OCR_TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def _ensure_secret_key():
    """首次启动若 data/.env 中无 SECRET_KEY，动态生成 32 字节高强度随机密钥写入 data/.env"""
    env_file = DATA_DIR / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        if "SECRET_KEY=" in content:
            return
    token = secrets.token_hex(32)
    with open(env_file, "a", encoding="utf-8") as f:
        f.write(f"\nSECRET_KEY={token}\n")


_ensure_secret_key()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DATA_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "智学迹 StudyTrace"
    VERSION: str = "0.1.0"
    TIMEZONE: str = "Asia/Shanghai"
    
    # 数据库路径
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'study_trace.db'}"
    
    # 服务绑定与端口隔离（M6 决议：生产 28000，开发 28001）
    HOST: str = "0.0.0.0"
    PORT: int = 28000
    DEV_PORT: int = 28001
    
    # 安全
    SECRET_KEY: str = "study-trace-secure-local-key-2026"
    DEFAULT_PIN: str = "888888"

    # 微信公众平台接口测试号 (Sandbox 官方直推与双向交互通道)
    WECHAT_APP_ID: str = "wx631c06dc9c8a1819"
    WECHAT_APP_SECRET: str = "088fa6a0c2d1bc5fdefd152bba06d66d"
    WECHAT_TEMPLATE_ID: str = "6LSmd6HG59OXRqCoHbzG5pVHPDpi7KcgsHQuFcU3t_E"
    WECHAT_OPEN_IDS: str = "oz1nN3D7D2MKPBE0ah2CmroanhVc,oz1nN3CuVUQ4S8yJ4PWU6wY2jsmo"
    WECHAT_CALLBACK_TOKEN: str = "studytrace2026"

    # CORS 域名白名单（收紧生产暴露面）
    ALLOWED_ORIGINS: list[str] = [
        "https://study.raddishlab.tech",
        "http://127.0.0.1:28000",
        "http://localhost:28000",
        "http://127.0.0.1:28001",
        "http://localhost:28001",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()

