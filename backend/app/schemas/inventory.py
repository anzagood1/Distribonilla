from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


class InventoryEntryCreate(BaseModel):
    producto_id: StrictInt = Field(..., gt=0)
    cantidad: StrictInt = Field(..., gt=0)
    motivo: str = Field(..., min_length=1, max_length=500)
    notas: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El motivo no puede estar vacío")
        return value

    @field_validator("notas")
    @classmethod
    def notas_validas(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class InventoryEntryResponse(BaseModel):
    id: int
    producto_id: int
    tipo: str
    cantidad: int
    motivo: str
    notas: Optional[str]
    fecha: datetime
    usuario_id: int
    stock_anterior: int
    stock_resultante: int

    model_config = ConfigDict(from_attributes=True)
