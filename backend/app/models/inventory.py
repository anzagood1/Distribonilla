from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True)
    auth_user_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    nombre = Column(Text)
    correo = Column(Text)
    rol_id = Column(Integer)
    activo = Column(Boolean, nullable=False, default=True)


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(BigInteger, primary_key=True)
    producto_id = Column(BigInteger, ForeignKey("productos.id"), nullable=False)
    tipo = Column(
        Enum("entrada", "salida", name="tipo_movimiento", create_constraint=False),
        nullable=False,
    )
    cantidad = Column(Integer, nullable=False)
    motivo = Column(Text, nullable=False)
    notas = Column(Text)
    fecha = Column(DateTime(timezone=True), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    venta_id = Column(BigInteger)
    stock_anterior = Column(Integer, nullable=False)
    stock_resultante = Column(Integer, nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(BigInteger, primary_key=True)
    key = Column(Text, nullable=False, unique=True)
    request_hash = Column(Text, nullable=False)
    route = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    movement_id = Column(
        BigInteger,
        ForeignKey("movimientos_inventario.id"),
        nullable=True,
    )
    user_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
