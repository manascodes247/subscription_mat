"""Store allocated discounts on invoice line snapshots.

Revision ID: 20261031_09
Revises: 20261031_08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_09"
down_revision: Union[str, Sequence[str], None] = "20261031_08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("invoice_lines") as batch_op:
        batch_op.add_column(sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("invoice_lines") as batch_op:
        batch_op.drop_column("discount_amount")
