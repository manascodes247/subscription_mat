"""Track Stripe PaymentIntents for invoice payments.

Revision ID: 20261031_11
Revises: 20261031_10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_11"
down_revision: Union[str, Sequence[str], None] = "20261031_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint("uq_invoices_stripe_payment_intent", ["stripe_payment_intent_id"])
    op.create_index("ix_invoices_stripe_payment_intent_id", "invoices", ["stripe_payment_intent_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invoices_stripe_payment_intent_id", table_name="invoices")
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_constraint("uq_invoices_stripe_payment_intent", type_="unique")
        batch_op.drop_column("stripe_payment_intent_id")
