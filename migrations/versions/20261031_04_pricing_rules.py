"""Add discounts, tax rules, and invoice pricing snapshots.

Revision ID: 20261031_04
Revises: 20261031_03
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261031_04"
down_revision: Union[str, Sequence[str], None] = "20261031_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

discount_type = postgresql.ENUM("PERCENTAGE", "FIXED", name="discounttype", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    discount_type.create(bind, checkfirst=True)
    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_type", discount_type, nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_discounts_code", "discounts", ["code"], unique=False)
    op.create_table(
        "tax_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("discount_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tax_rule_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_subscriptions_discount", "discounts", ["discount_id"], ["id"])
        batch_op.create_foreign_key("fk_subscriptions_tax_rule", "tax_rules", ["tax_rule_id"], ["id"])
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("tax_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"))
    op.execute("UPDATE invoices SET subtotal = amount")


def downgrade() -> None:
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_column("tax_amount")
        batch_op.drop_column("discount_amount")
        batch_op.drop_column("subtotal")
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_constraint("fk_subscriptions_tax_rule", type_="foreignkey")
        batch_op.drop_constraint("fk_subscriptions_discount", type_="foreignkey")
        batch_op.drop_column("tax_rule_id")
        batch_op.drop_column("discount_id")
    op.drop_table("tax_rules")
    op.drop_index("ix_discounts_code", table_name="discounts")
    op.drop_table("discounts")
    discount_type.drop(op.get_bind(), checkfirst=True)
