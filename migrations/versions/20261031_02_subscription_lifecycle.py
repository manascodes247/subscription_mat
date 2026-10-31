"""Add subscription lifecycle dates.

Revision ID: 20261031_02
Revises: 20261031_01
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_02"
down_revision: Union[str, Sequence[str], None] = "20261031_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("paused_on", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("cancelled_on", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_column("cancelled_on")
        batch_op.drop_column("paused_on")
