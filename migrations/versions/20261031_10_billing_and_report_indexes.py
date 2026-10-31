"""Add indexes for recurring billing and high-volume reporting.

Revision ID: 20261031_10
Revises: 20261031_09
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261031_10"
down_revision: Union[str, Sequence[str], None] = "20261031_09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_subscriptions_status_next_billing", "subscriptions", ["status", "next_billing_on"], unique=False)
    op.create_index("ix_subscriptions_customer_status", "subscriptions", ["customer_id", "status"], unique=False)
    op.create_index("ix_invoices_status_due_on", "invoices", ["status", "due_on"], unique=False)
    op.create_index("ix_invoices_period_start", "invoices", ["period_start"], unique=False)
    op.create_index("ix_payments_status_received_on", "payments", ["status", "received_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_status_received_on", table_name="payments")
    op.drop_index("ix_invoices_period_start", table_name="invoices")
    op.drop_index("ix_invoices_status_due_on", table_name="invoices")
    op.drop_index("ix_subscriptions_customer_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status_next_billing", table_name="subscriptions")
