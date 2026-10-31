"""Add product variants and full plan rules.

Revision ID: 20261031_05
Revises: 20261031_04
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261031_05"
down_revision: Union[str, Sequence[str], None] = "20261031_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

billing_interval = postgresql.ENUM("DAILY", "WEEKLY", "MONTHLY", "YEARLY", name="billinginterval", create_type=False)

def upgrade() -> None:
    bind = op.get_bind()
    billing_interval.create(bind, checkfirst=True)
    with op.batch_alter_table("products") as b:
        b.add_column(sa.Column("product_type", sa.String(length=80), nullable=True))
        b.add_column(sa.Column("sales_price", sa.Numeric(12, 2), nullable=True))
        b.add_column(sa.Column("cost_price", sa.Numeric(12, 2), nullable=True))
        b.add_column(sa.Column("notes", sa.String(length=2000), nullable=True))
    op.create_table("product_variants", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("additional_price", sa.Numeric(12, 2), nullable=False, server_default="0"), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("plans") as b:
        b.add_column(sa.Column("billing_interval", billing_interval, nullable=True))
        b.add_column(sa.Column("minimum_quantity", sa.Integer(), nullable=False, server_default="1"))
        b.add_column(sa.Column("available_from", sa.Date(), nullable=True))
        b.add_column(sa.Column("available_until", sa.Date(), nullable=True))
        b.add_column(sa.Column("auto_close_on_end", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("allow_early_close", sa.Boolean(), nullable=False, server_default=sa.true()))
        b.add_column(sa.Column("allow_pause", sa.Boolean(), nullable=False, server_default=sa.true()))
        b.add_column(sa.Column("allow_renew", sa.Boolean(), nullable=False, server_default=sa.true()))

def downgrade() -> None:
    with op.batch_alter_table("plans") as b:
        for col in ("allow_renew", "allow_pause", "allow_early_close", "auto_close_on_end", "available_until", "available_from", "minimum_quantity", "billing_interval"): b.drop_column(col)
    op.drop_table("product_variants")
    with op.batch_alter_table("products") as b:
        for col in ("notes", "cost_price", "sales_price", "product_type"): b.drop_column(col)
    billing_interval.drop(op.get_bind(), checkfirst=True)
