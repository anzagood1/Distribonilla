from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
    field_validator,
)

from app.services.stock_alerts import es_stock_bajo


Precio = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


def _normalizar_talla(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip().upper()
    if not value:
        raise ValueError("La talla no puede estar vacía")
    return value


def _sin_espacios(value: Optional[str]) -> Optional[str]:
    """Evita textos que solo contienen espacios (p. ej. nombre '   ')."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("El campo no puede estar vacío")
    return value


class ItemBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = Field(None, gt=0)
    precio_unitario: Precio
    talla: Optional[str] = Field(None, max_length=10, description="S, M, 32...")
    stock_actual: int = Field(0, ge=0)
    stock_minimo: int = Field(0, ge=0)
    aplica_iva: bool = True
    activo: bool = True

    _normalizar_talla = field_validator("talla")(_normalizar_talla)
    _sin_espacios = field_validator("nombre")(_sin_espacios)


class ItemCreate(ItemBase):
    codigo: Optional[str] = Field(None, max_length=50)

    _codigo_sin_espacios = field_validator("codigo")(_sin_espacios)

    def model_dump(self, **kwargs: Any) -> dict:
        data = super().model_dump(**kwargs)
        if data.get("codigo") is None:
            data.pop("codigo", None)
        return data


class ItemUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=50)
    nombre: Optional[str] = Field(None, max_length=150)
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = Field(None, gt=0)
    precio_unitario: Optional[Precio] = None
    talla: Optional[str] = Field(None, max_length=10)
    stock_actual: Optional[int] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    aplica_iva: Optional[bool] = None
    activo: Optional[bool] = None

    _normalizar_talla = field_validator("talla")(_normalizar_talla)
    _sin_espacios = field_validator("codigo", "nombre")(_sin_espacios)

    @field_validator("stock_minimo")
    @classmethod
    def _stock_minimo_no_nulo(cls, value: Optional[int]) -> int:
        # Solo se ejecuta si el cliente envía el campo: null explícito no vale
        if value is None:
            raise ValueError("stock_minimo no puede ser nulo; use 0 si no aplica")
        return value


class ItemResponse(ItemBase):
    id: int
    codigo: str
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def stock_bajo(self) -> bool:
        """GRUPO5-12: producto activo con stock_actual <= stock_minimo."""
        return self.activo and es_stock_bajo(self.stock_actual, self.stock_minimo)
