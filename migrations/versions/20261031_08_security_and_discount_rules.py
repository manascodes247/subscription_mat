"""Add password reset tokens and advanced discount eligibility rules.

Revision ID: 20261031_08
Revises: 20261031_07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_08"
down_revision: Union[str, Sequence[str], None] = "20261031_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False)
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=False)
    with op.batch_alter_table("discounts") as batch_op:
        batch_op.add_column(sa.Column("minimum_purchase", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column("minimum_quantity", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("usage_limit", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("product_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_discounts_product", "products", ["product_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("discounts") as batch_op:
        batch_op.drop_constraint("fk_discounts_product", type_="foreignkey")
        batch_op.drop_column("product_id")
        batch_op.drop_column("times_used")
        batch_op.drop_column("usage_limit")
        batch_op.drop_column("minimum_quantity")
        batch_op.drop_column("minimum_purchase")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
