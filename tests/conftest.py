import os
import sys
from pathlib import Path

# ------------------------------------------------------------------------------
# 必须在导入任何 backend 模块前设置环境变量，实现测试库与生产库 100% 物理隔离
# ------------------------------------------------------------------------------
TEST_DB_PATH = Path("data/temp/test_study_trace.db").resolve()
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 若存在旧测试库则先行清理
if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.seed import seed_database
from backend.app.config import settings

# 确保 settings 载入正确的测试数据库 URL
settings.DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 显式加载所有模型并立即在顶层完成建表，确保后续模块级 seed_database() 安全执行
import backend.app.models  # noqa: F401
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """测试会话级别 fixture：初始化种子数据并在会话结束清理"""
    seed_database()
    yield
    test_engine.dispose()
    # 测试结束后可清理测试文件
    test_engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


@pytest.fixture
def test_db():
    """每个用例可用的干净独立 DB session"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
