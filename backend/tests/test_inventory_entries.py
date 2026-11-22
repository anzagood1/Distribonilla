import hashlib
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.endpoints.inventory import register_inventory_entry
from app.models.inventory import IdempotencyKey, MovimientoInventario, Usuario
from app.models.item import Item
from app.schemas.inventory import InventoryEntryCreate


def make_db(product):
    query = Mock()
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = product

    db = Mock()
    db.query.return_value = query
    db.flush = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.add = Mock()
    return db


def request_hash(entry):
    payload = json.dumps(
        entry.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_idempotent_db(product, existing):
    item_query = Mock()
    item_query.filter.return_value = item_query
    item_query.with_for_update.return_value = item_query
    item_query.first.return_value = product

    key_query = Mock()
    key_query.filter.return_value = key_query
    key_query.first.return_value = existing

    db = Mock()
    db.query.side_effect = lambda model: item_query if model is Item else key_query
    db.flush = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.add = Mock()
    db.delete = Mock()
    return db


def test_quantity_must_be_positive_integer():
    with pytest.raises(ValidationError):
        InventoryEntryCreate(producto_id=1, cantidad=0, motivo="Compra")

    with pytest.raises(ValidationError):
        InventoryEntryCreate(producto_id=1, cantidad=-2, motivo="Compra")


def test_register_entry_updates_stock_and_creates_movement():
    product = Item(id=1, activo=True, stock_actual=20)
    product.actualizado_en = datetime.now(UTC)
    db = make_db(product)
    user = Usuario(id=7, activo=True)
    entry = InventoryEntryCreate(
        producto_id=1,
        cantidad=15,
        motivo="Compra proveedor",
        notas="Lote 123",
    )

    movement = register_inventory_entry(entry=entry, db=db, current_user=user)

    assert product.stock_actual == 35
    assert isinstance(movement, MovimientoInventario)
    assert movement.stock_anterior == 20
    assert movement.cantidad == 15
    assert movement.stock_resultante == 35
    assert movement.tipo == "entrada"
    assert movement.usuario_id == 7
    assert movement.fecha.tzinfo is not None
    db.commit.assert_called_once()


def test_inactive_product_is_rejected():
    product = Item(id=1, activo=False, stock_actual=20)
    db = make_db(product)
    entry = InventoryEntryCreate(producto_id=1, cantidad=5, motivo="Compra")

    with pytest.raises(HTTPException) as exc:
        register_inventory_entry(entry, db, Usuario(id=7, activo=True))

    assert exc.value.status_code == 404


def test_insert_failure_rolls_back_transaction():
    product = Item(id=1, activo=True, stock_actual=20)
    db = make_db(product)
    db.flush.side_effect = SQLAlchemyError("insert failed")
    entry = InventoryEntryCreate(producto_id=1, cantidad=5, motivo="Compra")

    with pytest.raises(HTTPException) as exc:
        register_inventory_entry(entry, db, Usuario(id=7, activo=True))

    assert exc.value.status_code == 500
    db.rollback.assert_called_once()


def test_repeated_idempotency_key_returns_original_response():
    product = Item(id=1, activo=True, stock_actual=20)
    entry = InventoryEntryCreate(
        producto_id=1,
        cantidad=4,
        motivo="Compra proveedor",
        notas="Prueba",
    )
    stored_body = {
        "id": 33,
        "producto_id": 1,
        "tipo": "entrada",
        "cantidad": 4,
        "motivo": "Compra proveedor",
        "notas": "Prueba",
        "fecha": datetime.now(UTC).isoformat(),
        "usuario_id": 7,
        "stock_anterior": 5,
        "stock_resultante": 9,
    }
    existing = IdempotencyKey(
        key="X",
        request_hash=request_hash(entry),
        route="/api/v1/inventory/entries",
        response_status=201,
        response_body=stored_body,
        movement_id=33,
        user_id=7,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db = make_idempotent_db(product, existing)

    result = register_inventory_entry(
        entry,
        db,
        Usuario(id=7, activo=True),
        idempotency_key="X",
    )

    assert result == stored_body
    assert product.stock_actual == 20
    db.commit.assert_not_called()


def test_same_key_with_different_content_is_conflict():
    product = Item(id=1, activo=True, stock_actual=20)
    entry = InventoryEntryCreate(
        producto_id=1,
        cantidad=5,
        motivo="Contenido distinto",
    )
    existing = IdempotencyKey(
        key="X",
        request_hash="hash-original",
        route="/api/v1/inventory/entries",
        response_status=201,
        response_body={"id": 33},
        movement_id=33,
        user_id=7,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db = make_idempotent_db(product, existing)

    with pytest.raises(HTTPException) as exc:
        register_inventory_entry(
            entry,
            db,
            Usuario(id=7, activo=True),
            idempotency_key="X",
        )

    assert exc.value.status_code == 409
    assert product.stock_actual == 20
    db.commit.assert_not_called()


def test_expired_idempotency_key_is_removed_and_entry_is_registered():
    product = Item(id=1, activo=True, stock_actual=20)
    entry = InventoryEntryCreate(
        producto_id=1,
        cantidad=5,
        motivo="Compra",
    )
    existing = IdempotencyKey(
        key="EXPIRED",
        request_hash=request_hash(entry),
        route="/api/v1/inventory/entries",
        response_status=201,
        response_body={"id": 33},
        movement_id=33,
        user_id=7,
        created_at=datetime.now(UTC) - timedelta(days=2),
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db = make_idempotent_db(product, existing)

    movement = register_inventory_entry(
        entry,
        db,
        Usuario(id=7, activo=True),
        idempotency_key="EXPIRED",
    )

    assert movement.stock_resultante == 25
    db.delete.assert_called_once_with(existing)
    db.commit.assert_called_once()


def test_idempotency_query_failure_returns_500():
    product = Item(id=1, activo=True, stock_actual=20)
    entry = InventoryEntryCreate(producto_id=1, cantidad=5, motivo="Compra")

    item_query = Mock()
    item_query.filter.return_value = item_query
    item_query.with_for_update.return_value = item_query
    item_query.first.return_value = product

    db = Mock()
    db.query.side_effect = lambda model: (
        item_query
        if model is Item
        else (_ for _ in ()).throw(SQLAlchemyError("query failed"))
    )

    with pytest.raises(HTTPException) as exc:
        register_inventory_entry(
            entry,
            db,
            Usuario(id=7, activo=True),
            idempotency_key="BROKEN",
        )

    assert exc.value.status_code == 500


def test_integrity_error_returns_409():
    product = Item(id=1, activo=True, stock_actual=20)
    db = make_db(product)
    db.flush.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    entry = InventoryEntryCreate(producto_id=1, cantidad=5, motivo="Compra")

    with pytest.raises(HTTPException) as exc:
        register_inventory_entry(entry, db, Usuario(id=7, activo=True))

    assert exc.value.status_code == 409
    db.rollback.assert_called_once()


def test_unexpected_error_returns_500():
    product = Item(id=1, activo=True, stock_actual=20)
    db = make_db(product)
    db.flush.side_effect = RuntimeError("unexpected")
    entry = InventoryEntryCreate(producto_id=1, cantidad=5, motivo="Compra")

    with pytest.raises(HTTPException) as exc:
        register_inventory_entry(entry, db, Usuario(id=7, activo=True))

    assert exc.value.status_code == 500
    db.rollback.assert_called_once()
