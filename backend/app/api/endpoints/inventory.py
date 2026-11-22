import hashlib
import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.crud import crud_item
from app.models.inventory import IdempotencyKey, MovimientoInventario, Usuario
from app.models.item import Item
from app.schemas.inventory import InventoryEntryCreate, InventoryEntryResponse
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED
)
def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Registra un nuevo producto en el catálogo.
    """
    return crud_item.create_item(db=db, item=item)


@router.get("/items/", response_model=list[ItemResponse])
def read_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Lista los productos del catálogo con paginación.
    """
    items = crud_item.get_items(db, skip=skip, limit=limit)
    return items


@router.get("/items/low-stock/", response_model=list[ItemResponse])
def read_low_stock_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Lista los productos activos con stock bajo (stock_actual <= stock_minimo),
    primero los más críticos.
    """
    return crud_item.get_low_stock_items(db, skip=skip, limit=limit)


@router.get(
    "/items/{item_id}/movements",
    response_model=list[InventoryEntryResponse],
)
def read_item_movements(
    item_id: int,
    db: Session = Depends(get_db),
    from_date: date | None = None,
    to_date: date | None = None,
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem no encontrado",
        )

    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha inicial no puede ser posterior a la fecha final",
        )

    query = db.query(MovimientoInventario).filter(
        MovimientoInventario.producto_id == item_id
    )
    if from_date:
        query = query.filter(
            MovimientoInventario.fecha
            >= datetime.combine(from_date, datetime.min.time())
        )
    if to_date:
        end = datetime.combine(to_date + timedelta(days=1), datetime.min.time())
        query = query.filter(MovimientoInventario.fecha < end)

    return query.order_by(MovimientoInventario.fecha.asc()).all()


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
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
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ] = None,
):
    key = idempotency_key.strip() if idempotency_key else None
    request_hash = hashlib.sha256(
        json.dumps(
            entry.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    producto = (
        db.query(Item).filter(Item.id == entry.producto_id).with_for_update().first()
    )

    if producto is None or not producto.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto inexistente o inactivo",
        )

    if key:
        try:
            existing = (
                db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
            )
        except SQLAlchemyError:
            logger.exception("No fue posible consultar la clave de idempotencia")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No fue posible validar la clave de idempotencia",
            )
        now = datetime.now(UTC)

        if existing is not None:
            expires_at = existing.expires_at
            if expires_at is not None and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)

            if expires_at is not None and expires_at <= now:
                db.delete(existing)
                db.flush()
            elif (
                existing.request_hash != request_hash
                or existing.route != "/api/v1/inventory/entries"
                or existing.user_id != current_user.id
            ):
                logger.error(
                    "Idempotency key conflict: %s",
                    {"key": key, "request_hash": request_hash},
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="La clave de idempotencia ya fue utilizada con otro contenido",
                )
            else:
                return existing.response_body

    stock_anterior = producto.stock_actual
    stock_resultante = stock_anterior + entry.cantidad

    movimiento = MovimientoInventario(
        producto_id=producto.id,
        tipo="entrada",
        cantidad=entry.cantidad,
        motivo=entry.motivo,
        notas=entry.notas,
        fecha=datetime.now(UTC),
        usuario_id=current_user.id,
        venta_id=None,
        stock_anterior=stock_anterior,
        stock_resultante=stock_resultante,
    )

    try:
        producto.stock_actual = stock_resultante
        producto.actualizado_en = datetime.now(UTC)
        db.add(movimiento)
        db.flush()

        if key:
            response_body = {
                "id": movimiento.id,
                "producto_id": movimiento.producto_id,
                "tipo": movimiento.tipo,
                "cantidad": movimiento.cantidad,
                "motivo": movimiento.motivo,
                "notas": movimiento.notas,
                "fecha": movimiento.fecha.isoformat(),
                "usuario_id": movimiento.usuario_id,
                "stock_anterior": movimiento.stock_anterior,
                "stock_resultante": movimiento.stock_resultante,
            }
            db.add(
                IdempotencyKey(
                    key=key,
                    request_hash=request_hash,
                    route="/api/v1/inventory/entries",
                    response_status=status.HTTP_201_CREATED,
                    response_body=response_body,
                    movement_id=movimiento.id,
                    user_id=current_user.id,
                    created_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(hours=24),
                )
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La clave de idempotencia ya fue utilizada",
        )
    except SQLAlchemyError:
        logger.exception("No fue posible registrar la entrada de mercancía")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar la entrada de mercancía",
        )
    except Exception:
        logger.exception("Error inesperado al registrar la entrada de mercancía")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar la entrada de mercancía",
        )

    return movimiento
