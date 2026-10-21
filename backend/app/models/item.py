from sqlalchemy import Column, Integer, String, Float, Text, Boolean  # type: ignore[reportMissingImports]
from app.db.base import Base # Asegúrate de tener tu Base = declarative_base() en db/base.py

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), index=True, nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True)