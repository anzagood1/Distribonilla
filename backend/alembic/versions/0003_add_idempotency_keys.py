"""Add idempotency keys table.

Revision ID: 0003_idempotency
Revises: 0002_add_talla
Create Date: 2026-11-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("idempotency_keys"):
        return

    if bind.dialect.name == "postgresql":
        response_body = postgresql.JSONB(astext_type=sa.Text())
    else:
        response_body = sa.JSON()

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("route", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", response_body, nullable=False),
        sa.Column("movement_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["movement_id"], ["movimientos_inventario.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    """No-op: preserve idempotency records because the table may predate migration 0003."""
    pass
