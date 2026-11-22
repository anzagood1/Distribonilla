"""Add request_hash column to idempotency_keys.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("idempotency_keys"):
        return

    columns = {
        column["name"] for column in inspect(bind).get_columns("idempotency_keys")
    }
    if "request_hash" not in columns:
        op.add_column(
            "idempotency_keys",
            sa.Column("request_hash", sa.Text(), nullable=True),
        )
        op.execute(
            "UPDATE idempotency_keys SET request_hash = '' "
            "WHERE request_hash IS NULL"
        )
        op.alter_column(
            "idempotency_keys",
            "request_hash",
            existing_type=sa.Text(),
            nullable=False,
        )


def downgrade() -> None:
    """No-op: request_hash belongs to 0003 and is not removed by 0004."""
    pass
