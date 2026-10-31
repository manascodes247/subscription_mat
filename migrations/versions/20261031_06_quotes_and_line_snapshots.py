"""Add quotations, subscription lines, and invoice snapshots.

Revision ID: 20261031_06
Revises: 20261031_05
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261031_06"
down_revision: Union[str, Sequence[str], None] = "20261031_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

quotation_status = postgresql.ENUM("DRAFT", "QUOTATION", "CONFIRMED", "CLOSED", name="quotationstatus", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    quotation_status.create(bind, checkfirst=True)

    op.create_table(
        "quotation_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "quotation_template_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["quotation_templates.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "quotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quotation_number", sa.String(length=40), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("status", quotation_status, nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=False),
        sa.Column("payment_terms", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_number"),
    )
    op.create_index("ix_quotations_quotation_number", "quotations", ["quotation_number"], unique=False)
    op.create_index("ix_quotations_customer_id", "quotations", ["customer_id"], unique=False)
    op.create_table(
        "quotation_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_lines_quotation_id", "quotation_lines", ["quotation_id"], unique=False)

    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("subscription_number", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("expires_on", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("payment_terms", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("source_quotation_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_subscriptions_number", ["subscription_number"])
        batch_op.create_unique_constraint("uq_subscriptions_source_quotation", ["source_quotation_id"])
        batch_op.create_foreign_key("fk_subscriptions_source_quotation", "quotations", ["source_quotation_id"], ["id"])
    op.create_index("ix_subscriptions_subscription_number", "subscriptions", ["subscription_number"], unique=False)
    op.create_table(
        "subscription_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_lines_subscription_id", "subscription_lines", ["subscription_id"], unique=False)

    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(sa.Column("customer_id_snapshot", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("customer_name_snapshot", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("customer_email_snapshot", sa.String(length=255), nullable=True))
    op.create_index("ix_invoices_customer_id_snapshot", "invoices", ["customer_id_snapshot"], unique=False)
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("product_id_snapshot", sa.Integer(), nullable=True),
        sa.Column("variant_id_snapshot", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"], unique=False)

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("note", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_column("note")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index("ix_invoices_customer_id_snapshot", table_name="invoices")
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_column("customer_email_snapshot")
        batch_op.drop_column("customer_name_snapshot")
        batch_op.drop_column("customer_id_snapshot")
    op.drop_index("ix_subscription_lines_subscription_id", table_name="subscription_lines")
    op.drop_table("subscription_lines")
    op.drop_index("ix_subscriptions_subscription_number", table_name="subscriptions")
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_constraint("fk_subscriptions_source_quotation", type_="foreignkey")
        batch_op.drop_constraint("uq_subscriptions_source_quotation", type_="unique")
        batch_op.drop_constraint("uq_subscriptions_number", type_="unique")
        batch_op.drop_column("source_quotation_id")
        batch_op.drop_column("payment_terms")
        batch_op.drop_column("expires_on")
        batch_op.drop_column("subscription_number")
    op.drop_index("ix_quotation_lines_quotation_id", table_name="quotation_lines")
    op.drop_table("quotation_lines")
    op.drop_index("ix_quotations_customer_id", table_name="quotations")
    op.drop_index("ix_quotations_quotation_number", table_name="quotations")
    op.drop_table("quotations")
    op.drop_table("quotation_template_lines")
    op.drop_table("quotation_templates")
    quotation_status.drop(op.get_bind(), checkfirst=True)
