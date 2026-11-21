from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.schemas.inventory import InventoryEntryCreate, InventoryEntryResponse
from app.models.inventory import MovimientoInventario, Producto, Usuario
from app.crud import crud_item

router = APIRouter()


@router.post(
    "/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED
)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo producto en el catálogo.
    """
    return crud_item.create_item(db=db, item=item)


@router.get("/items/", response_model=List[ItemResponse])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista los productos del catálogo con paginación.
    """
    items = crud_item.get_items(db, skip=skip, limit=limit)
    return items


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    """
    Edita la información de un producto existente.
    """
    db_item = crud_item.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado"
        )

    return crud_item.update_item(db=db, db_item=db_item, item_update=item_update)


@router.post(
    "/entries",
    response_model=InventoryEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_inventory_entry(
    entry: InventoryEntryCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    producto = (
        db.query(Producto)
        .filter(Producto.id == entry.producto_id)
        .with_for_update()
        .first()
    )

    if producto is None or not producto.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto inexistente o inactivo",
        )

    stock_anterior = producto.stock_actual
    stock_resultante = stock_anterior + entry.cantidad

    movimiento = MovimientoInventario(
        producto_id=producto.id,
        tipo="entrada",
        cantidad=entry.cantidad,
        motivo=entry.motivo,
        notas=entry.notas,
        fecha=datetime.now(timezone.utc),
        usuario_id=current_user.id,
        venta_id=None,
        stock_anterior=stock_anterior,
        stock_resultante=stock_resultante,
    )

    try:
        producto.stock_actual = stock_resultante
        producto.actualizado_en = datetime.now(timezone.utc)
        db.add(movimiento)
        db.flush()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar la entrada de mercancía",
        )

    return movimiento
