"""add_unique_constraint_to_notification_log

Revision ID: 63d716a523ac
Revises: a5ed36dbabf9
Create Date: 2026-09-06 00:45:53.592518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63d716a523ac'
down_revision: Union[str, Sequence[str], None] = 'a5ed36dbabf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("notification_logs", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_notification_date_slot_channel",
            ["date", "slot", "channel"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("notification_logs", schema=None) as batch_op:
        batch_op.drop_constraint("uq_notification_date_slot_channel", type_="unique")
