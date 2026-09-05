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
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# 自动确保数据持久化目录存在
for d in [DATA_DIR, UPLOADS_DIR, ORIGINALS_DIR, THUMBNAILS_DIR, EXPORTS_DIR, BACKUPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DATA_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "学迹 StudyTrace"
    VERSION: str = "0.1.0"
    TIMEZONE: str = "Asia/Shanghai"
    
    # 数据库路径
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'study_trace.db'}"
    
    # 服务绑定
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 安全
    SECRET_KEY: str = "study-trace-secure-local-key-2026"
    DEFAULT_PIN: str = "888888"


settings = Settings()
