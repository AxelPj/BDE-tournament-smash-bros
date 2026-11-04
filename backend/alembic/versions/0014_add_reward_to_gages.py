"""add reward to gages

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-03 09:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("gages")}
    if "reward" not in columns:
        with op.batch_alter_table("gages", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("reward", sa.Integer(), server_default="50", nullable=False)
            )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("gages")}
    if "reward" in columns:
        with op.batch_alter_table("gages", schema=None) as batch_op:
            batch_op.drop_column("reward")
