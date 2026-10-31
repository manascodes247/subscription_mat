"""Add indexes for catalog, customer, and quotation filters.

Revision ID: 20261031_14
Revises: 20261031_13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261031_14"
down_revision: Union[str, Sequence[str], None] = "20261031_13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_role_created_at", "users", ["role", "created_at"], unique=False)
    op.create_index("ix_products_active_name", "products", ["active", "name"], unique=False)
    op.create_index("ix_plans_product_active", "plans", ["product_id", "active"], unique=False)
    op.create_index("ix_discounts_active_dates", "discounts", ["active", "starts_on", "ends_on"], unique=False)
    op.create_index("ix_quotations_customer_status", "quotations", ["customer_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotations_customer_status", table_name="quotations")
    op.drop_index("ix_discounts_active_dates", table_name="discounts")
    op.drop_index("ix_plans_product_active", table_name="plans")
    op.drop_index("ix_products_active_name", table_name="products")
    op.drop_index("ix_users_role_created_at", table_name="users")
