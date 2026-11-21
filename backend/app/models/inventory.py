from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True)
    auth_user_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    nombre = Column(Text)
    correo = Column(Text)
    rol_id = Column(Integer)
    activo = Column(Boolean, nullable=False, default=True)


class Producto(Base):
    __tablename__ = "productos"

    id = Column(BigInteger, primary_key=True)
    codigo = Column(Text, nullable=False, unique=True)
    nombre = Column(Text, nullable=False)
    descripcion = Column(Text)
    categoria_id = Column(BigInteger)
    precio_unitario = Column(Numeric, nullable=False)
    stock_actual = Column(Integer, nullable=False)
    stock_minimo = Column(Integer, nullable=False)
    aplica_iva = Column(Boolean, nullable=False)
    activo = Column(Boolean, nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), nullable=False)


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(BigInteger, primary_key=True)
    producto_id = Column(BigInteger, ForeignKey("productos.id"), nullable=False)
    tipo = Column(Enum("entrada", "salida", name="tipo_movimiento", create_constraint=False), nullable=False)
    cantidad = Column(Integer, nullable=False)
    motivo = Column(Text, nullable=False)
    notas = Column(Text)
    fecha = Column(DateTime(timezone=True), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    venta_id = Column(BigInteger)
    stock_anterior = Column(Integer, nullable=False)
    stock_resultante = Column(Integer, nullable=False)
