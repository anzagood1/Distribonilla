from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

# Propiedades compartidas
class ItemBase(BaseModel):
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    sku: str = Field(..., max_length=50)
    price: float = Field(..., gt=0, description="El precio debe ser mayor a 0")
    stock: int = Field(0, ge=0)
    is_active: bool = True

# Propiedades para crear (POST)
class ItemCreate(ItemBase):
    pass

# Propiedades para actualizar (PUT) - Todos los campos son opcionales
class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    sku: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

# Propiedades que devuelve la API (GET)
class ItemResponse(ItemBase):
    id: int

    # Configuración para que Pydantic sepa leer el modelo de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)