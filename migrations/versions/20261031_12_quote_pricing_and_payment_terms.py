"""Carry pricing rules and due terms from quotations into subscriptions.

Revision ID: 20261031_12
Revises: 20261031_11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_12"
down_revision: Union[str, Sequence[str], None] = "20261031_11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.add_column(sa.Column("discount_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tax_rule_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("payment_due_days", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key("fk_quotations_discount", "discounts", ["discount_id"], ["id"])
        batch_op.create_foreign_key("fk_quotations_tax_rule", "tax_rules", ["tax_rule_id"], ["id"])
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("payment_due_days", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_column("payment_due_days")
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.drop_constraint("fk_quotations_tax_rule", type_="foreignkey")
        batch_op.drop_constraint("fk_quotations_discount", type_="foreignkey")
        batch_op.drop_column("payment_due_days")
        batch_op.drop_column("tax_rule_id")
        batch_op.drop_column("discount_id")
