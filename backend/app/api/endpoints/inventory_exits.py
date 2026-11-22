import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import CURRENT_USER_DEPENDENCY, DB_DEPENDENCY
from app.models.inventory import IdempotencyKey, MovimientoInventario, Usuario
from app.models.item import Item
from app.schemas.inventory import InventoryEntryResponse
from app.schemas.inventory_exits import InventoryExitCreate

router = APIRouter()
logger = logging.getLogger(__name__)
EXIT_ROUTE = "/api/v1/inventory/exits"


@router.post("/exits", response_model=InventoryEntryResponse, status_code=201)
def register_inventory_exit(
    exit_request: InventoryExitCreate,
    db: Annotated[Session, DB_DEPENDENCY],
    current_user: Annotated[Usuario, CURRENT_USER_DEPENDENCY],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ] = None,
):
    return _register_inventory_exit(
        exit_request, db, current_user, idempotency_key, True
    )


def _register_inventory_exit(
    exit_request: InventoryExitCreate,
    db: Session,
    current_user: Usuario,
    idempotency_key: str | None,
    retry_expired: bool,
):
    key = idempotency_key.strip() if idempotency_key else None
    request_hash = hashlib.sha256(
        json.dumps(
            exit_request.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    try:
        if key:
            existing = (
                db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
            )
            if existing is not None:
                expires_at = existing.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at > datetime.now(UTC):
                    if (
                        existing.request_hash != request_hash
                        or existing.route != EXIT_ROUTE
                        or existing.user_id != current_user.id
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail="La clave de idempotencia ya fue utilizada con otro contenido",
                        )
                    return existing.response_body
                # Refresh a potentially stale expired record after acquiring the lock.
                db.expire(existing)

        product = (
            db.query(Item)
            .filter(Item.id == exit_request.producto_id)
            .with_for_update()
            .first()
        )
        if product is None or not product.activo:
            raise HTTPException(
                status_code=404, detail="Producto inexistente o inactivo"
            )

        now = datetime.now(UTC)
        if key:
            existing = (
                db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
            )
            if existing is not None:
                expires_at = existing.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at <= now:
                    db.delete(existing)
                    db.flush()
                elif (
                    existing.request_hash != request_hash
                    or existing.route != EXIT_ROUTE
                    or existing.user_id != current_user.id
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="La clave de idempotencia ya fue utilizada con otro contenido",
                    )
                else:
                    return existing.response_body

        before = product.stock_actual
        if before < exit_request.cantidad:
            raise HTTPException(status_code=409, detail="Stock insuficiente")

        movement = MovimientoInventario(
            producto_id=product.id,
            tipo="salida",
            cantidad=exit_request.cantidad,
            motivo=exit_request.motivo,
            notas=exit_request.notas,
            fecha=now,
            usuario_id=current_user.id,
            venta_id=None,
            stock_anterior=before,
            stock_resultante=before - exit_request.cantidad,
        )
        db.add(movement)
        db.flush()
        # PostgreSQL's AFTER INSERT trigger owns the stock adjustment.
        db.refresh(product, attribute_names=["stock_actual"])
        if product.stock_actual != movement.stock_resultante:
            raise HTTPException(
                status_code=500, detail="No fue posible registrar la salida"
            )

        if key:
            body = InventoryEntryResponse.model_validate(movement).model_dump(
                mode="json"
            )
            db.add(
                IdempotencyKey(
                    key=key,
                    request_hash=request_hash,
                    route=EXIT_ROUTE,
                    response_status=status.HTTP_201_CREATED,
                    response_body=body,
                    movement_id=movement.id,
                    user_id=current_user.id,
                    created_at=now,
                    expires_at=now + timedelta(hours=24),
                )
            )

        db.commit()
        return body if key else movement
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        diagnostic = getattr(exc.orig, "diag", None)
        index_name = getattr(diagnostic, "constraint_name", None)
        if (
            key
            and getattr(exc.orig, "pgcode", None) == "23505"
            and getattr(diagnostic, "table_name", None) == "idempotency_keys"
            and index_name
        ):
            try:
                indexes = inspect(db.connection()).get_indexes(
                    "idempotency_keys", schema=getattr(diagnostic, "schema_name", None)
                )
                key_index = any(
                    index.get("name") == index_name
                    and index.get("unique")
                    and index.get("column_names") == ["key"]
                    and not index.get("dialect_options", {}).get("postgresql_where")
                    for index in indexes
                )
                if key_index:
                    existing = (
                        db.query(IdempotencyKey)
                        .filter(IdempotencyKey.key == key)
                        .first()
                    )
                    if existing is not None:
                        expires_at = existing.expires_at
                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=UTC)
                        if expires_at <= datetime.now(UTC):
                            if retry_expired:
                                return _register_inventory_exit(
                                    exit_request,
                                    db,
                                    current_user,
                                    idempotency_key,
                                    False,
                                )
                        elif (
                            existing.request_hash == request_hash
                            and existing.route == EXIT_ROUTE
                            and existing.user_id == current_user.id
                        ):
                            return existing.response_body
                        else:
                            raise HTTPException(
                                status_code=409,
                                detail="La clave de idempotencia ya fue utilizada con otro contenido",
                            ) from exc
            except SQLAlchemyError:
                db.rollback()
        logger.error("No fue posible registrar la salida por un error de integridad")
        raise HTTPException(
            status_code=500, detail="No fue posible registrar la salida"
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("No fue posible registrar la salida por un error de base de datos")
        raise HTTPException(
            status_code=500, detail="No fue posible registrar la salida"
        ) from exc

    except Exception as exc:
        db.rollback()
        logger.error("No fue posible registrar la salida")
        raise HTTPException(
            status_code=500, detail="No fue posible registrar la salida"
        ) from exc
