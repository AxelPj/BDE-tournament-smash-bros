"""add image_url to gages

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-02 14:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("gages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("gages", schema=None) as batch_op:
        batch_op.drop_column("image_url")
