
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"

    op.create_table(
        "categorias",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="categorias_pkey"),
        sa.UniqueConstraint("nombre", name="categorias_nombre_key"),
    )

    if is_postgres:
        op.execute("CREATE SEQUENCE IF NOT EXISTS seq_codigo_producto")
        codigo_default = sa.text(
            "('PRD-'::text || lpad((nextval('seq_codigo_producto'::regclass))::text,"
            " 5, '0'::text))"
        )
    else:
        codigo_default = None

    op.create_table(
        "productos",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False, server_default=codigo_default),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("categoria_id", sa.BigInteger(), nullable=True),
        sa.Column("precio_unitario", sa.Numeric(), nullable=False),
        sa.Column("stock_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_minimo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aplica_iva", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="productos_pkey"),
        sa.UniqueConstraint("codigo", name="productos_codigo_key"),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["categorias.id"], name="productos_categoria_id_fkey"
        ),
        sa.CheckConstraint(
            "precio_unitario > 0", name="productos_precio_unitario_check"
        ),
        sa.CheckConstraint("stock_actual >= 0", name="productos_stock_actual_check"),
        sa.CheckConstraint("stock_minimo >= 0", name="productos_stock_minimo_check"),
    )


def downgrade() -> None:
    op.drop_table("productos")
    op.drop_table("categorias")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP SEQUENCE IF EXISTS seq_codigo_producto")
