from typing import Literal

from pydantic import BaseModel, Field, StrictInt, field_validator


class InventoryExitCreate(BaseModel):
    producto_id: StrictInt = Field(..., gt=0)
    cantidad: StrictInt = Field(..., gt=0)
    motivo: Literal["merma", "daño", "ajuste"]
    notas: str | None = Field(default=None, max_length=2000)

    @field_validator("notas")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None
