"""create_exam_tables

Revision ID: b7751890cf12
Revises: a664048047b8
Create Date: 2026-09-06 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7751890cf12'
down_revision: Union[str, Sequence[str], None] = 'a664048047b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'exam_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('exam_type', sa.String(length=30), nullable=True),
        sa.Column('exam_date', sa.Date(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=True),
        sa.Column('total_full_score', sa.Float(), nullable=True),
        sa.Column('class_rank', sa.Integer(), nullable=True),
        sa.Column('grade_rank', sa.Integer(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_records_student_id'), 'exam_records', ['student_id'], unique=False)
    op.create_index(op.f('ix_exam_records_exam_date'), 'exam_records', ['exam_date'], unique=False)
    op.create_index(op.f('ix_exam_records_exam_type'), 'exam_records', ['exam_type'], unique=False)
    op.create_index(op.f('ix_exam_records_created_at'), 'exam_records', ['created_at'], unique=False)

    op.create_table(
        'exam_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('full_score', sa.Float(), nullable=False),
        sa.Column('class_average', sa.Float(), nullable=True),
        sa.Column('class_rank', sa.Integer(), nullable=True),
        sa.Column('grade_rank', sa.Integer(), nullable=True),
        sa.Column('is_absent', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['exam_id'], ['exam_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'subject_id', name='uq_exam_subject')
    )
    op.create_index(op.f('ix_exam_scores_exam_id'), 'exam_scores', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_scores_subject_id'), 'exam_scores', ['subject_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_exam_scores_subject_id'), table_name='exam_scores')
    op.drop_index(op.f('ix_exam_scores_exam_id'), table_name='exam_scores')
    op.drop_table('exam_scores')

    op.drop_index(op.f('ix_exam_records_created_at'), table_name='exam_records')
    op.drop_index(op.f('ix_exam_records_exam_type'), table_name='exam_records')
    op.drop_index(op.f('ix_exam_records_exam_date'), table_name='exam_records')
    op.drop_index(op.f('ix_exam_records_student_id'), table_name='exam_records')
    op.drop_table('exam_records')
