"""Add payment records.

Revision ID: 20261031_03
Revises: 20261031_02
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261031_03"
down_revision: Union[str, Sequence[str], None] = "20261031_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

payment_status = postgresql.ENUM("SUCCESS", "FAILED", name="paymentstatus", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    payment_status.create(bind, checkfirst=True)
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("gateway_reference", sa.String(length=160), nullable=True),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gateway_reference"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_table("payments")
    payment_status.drop(op.get_bind(), checkfirst=True)
