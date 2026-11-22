from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

Precio = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


def _normalizar_talla(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not value:
        raise ValueError("La talla no puede estar vacía")
    return value


def _sin_espacios(value: str | None) -> str | None:
    """Evita textos que solo contienen espacios (p. ej. nombre '   ')."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("El campo no puede estar vacío")
    return value


class ItemBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: str | None = None
    categoria_id: int | None = Field(None, gt=0)
    precio_unitario: Precio
    talla: str | None = Field(None, max_length=10, description="S, M, 32...")
    stock_actual: int = Field(0, ge=0)
    stock_minimo: int = Field(0, ge=0)
    aplica_iva: bool = True
    activo: bool = True

    _normalizar_talla = field_validator("talla")(_normalizar_talla)
    _sin_espacios = field_validator("nombre")(_sin_espacios)


class ItemCreate(ItemBase):
    codigo: str | None = Field(None, max_length=50)

    _codigo_sin_espacios = field_validator("codigo")(_sin_espacios)

    def model_dump(self, **kwargs: Any) -> dict:
        data = super().model_dump(**kwargs)
        if data.get("codigo") is None:
            data.pop("codigo", None)
        return data


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(None, max_length=50)
    nombre: str | None = Field(None, max_length=150)
    descripcion: str | None = None
    categoria_id: int | None = Field(None, gt=0)
    precio_unitario: Precio | None = None
    talla: str | None = Field(None, max_length=10)
    stock_minimo: int | None = Field(None, ge=0)
    aplica_iva: bool | None = None
    activo: bool | None = None

    _normalizar_talla = field_validator("talla")(_normalizar_talla)
    _sin_espacios = field_validator("codigo", "nombre")(_sin_espacios)


class ItemResponse(ItemBase):
    id: int
    codigo: str
    stock_bajo: bool
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)
