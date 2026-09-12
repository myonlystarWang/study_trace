import os
import sys
from pathlib import Path

# ------------------------------------------------------------------------------
# 必须在导入任何 backend 模块前设置环境变量，实现测试库与生产库 100% 物理隔离
# ------------------------------------------------------------------------------
TEST_DB_PATH = Path("data/temp/test_study_trace.db").resolve()
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 图片业务目录同样隔离：指到 data/temp/uploads。
# 否则测试上传的 fixture 图会写进生产 data/uploads，在生产库里留下孤儿文件
# （文件名 = 内容 sha256，会覆写同名文件并刷新 mtime，排查时极易误判）。
TEST_UPLOADS_DIR = Path("data/temp/uploads").resolve()
os.environ["STUDYTRACE_UPLOADS_DIR"] = str(TEST_UPLOADS_DIR)

# 若存在旧测试库则先行清理
if TEST_DB_PATH.exists():
    try:
        TEST_DB_PATH.unlink()
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"


def _purge_test_uploads():
    """清空 data/temp/uploads（带路径守卫，绝不允许指向真实 uploads 目录）"""
    import shutil

    resolved = TEST_UPLOADS_DIR.resolve()
    if "temp" not in resolved.parts or resolved.name != "uploads":
        raise RuntimeError(f"拒绝清理非测试目录: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved, ignore_errors=True)


# 会话开始先清空测试图片目录，保证每次 pytest 都从干净状态出发
_purge_test_uploads()

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

# ------------------------------------------------------------------------------
# 通过 Alembic 执行迁移构建测试库结构，严禁 create_all 捷径，确保与生产环境 100% 一致
# ------------------------------------------------------------------------------
import backend.app.models  # noqa: F401
from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
command.upgrade(alembic_cfg, "head")


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
    _purge_test_uploads()


@pytest.fixture
def test_db():
    """每个用例可用的干净独立 DB session"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
