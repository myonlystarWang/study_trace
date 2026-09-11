"""add answer column to mistake_records

Revision ID: e17a3b9c4d52
Revises: b7751890cf12
Create Date: 2026-09-11 22:45:00.000000

背景
----
`0535dad` 给 MistakeRecord 增加了 `answer` 字段（错题答案），但当时只改了模型、
接口与前端，漏写迁移，且生产库是手工补的列，因此一直未暴露。

后果：任何「从迁移链重建」的场景（`tests/conftest.py` 走 alembic upgrade head、
新机器部署、灾备还原）都建不出该列，导致错题列表/新增 500
（`sqlite3.OperationalError: no such column: mistake_records.answer`）。

兼容处理
--------
生产库 `data/study_trace.db` 已存在该列（`alembic_version` 已在 head 但列是手工加的）。
故 upgrade/downgrade 均先探测列是否存在，存在则跳过，保证本迁移对已有库幂等、
对新建库补齐。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e17a3b9c4d52'
down_revision: Union[str, Sequence[str], None] = 'b7751890cf12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "mistake_records"
COLUMN = "answer"


def _has_column(table: str, column: str) -> bool:
    """探测目标表是否已存在指定列（SQLite/MySQL 通用，不依赖方言特定语法）。"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    """补齐 MistakeRecord.answer（已存在则跳过）。"""
    if _has_column(TABLE, COLUMN):
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.Text(), nullable=True))


def downgrade() -> None:
    """回滚：删除该列（不存在则跳过）。

    注意：该列可能存有已录入的错题答案，downgrade 会一并丢弃，仅用于本地回退。
    """
    if not _has_column(TABLE, COLUMN):
        return
    op.drop_column(TABLE, COLUMN)
