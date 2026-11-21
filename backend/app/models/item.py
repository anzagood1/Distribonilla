from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    FetchedValue,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True
    )
    nombre = Column(Text, nullable=False, unique=True)

    productos = relationship("Item", back_populates="categoria")


class Item(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("precio_unitario > 0", name="productos_precio_unitario_check"),
        CheckConstraint("stock_actual >= 0", name="productos_stock_actual_check"),
        CheckConstraint("stock_minimo >= 0", name="productos_stock_minimo_check"),
    )

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True
    )
    codigo = Column(Text, nullable=False, unique=True, server_default=FetchedValue())
    nombre = Column(Text, nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria_id = Column(BigInteger, ForeignKey("categorias.id"), nullable=True)
    precio_unitario = Column(Numeric, nullable=False)
    stock_actual = Column(Integer, nullable=False, default=0, server_default="0")
    stock_minimo = Column(Integer, nullable=False, default=0, server_default="0")
    aplica_iva = Column(Boolean, nullable=False, default=True, server_default="true")
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    talla = Column(Text, nullable=True)
    creado_en = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    categoria = relationship("Categoria", back_populates="productos")
