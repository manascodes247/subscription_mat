"""Add required subscription and invoice workflow states.

Revision ID: 20261031_07
Revises: 20261031_06
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261031_07"
down_revision: Union[str, Sequence[str], None] = "20261031_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLAlchemy's SQLite Enum does not use a database enum type. PostgreSQL
    # does, so add only the new values and keep legacy values readable.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'QUOTATION'")
        op.execute("ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'CONFIRMED'")
        op.execute("ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'CLOSED'")
        op.execute("ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'CONFIRMED'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without rebuilding the
    # type. The migration is intentionally irreversible.
    pass
