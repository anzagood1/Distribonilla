from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.endpoints.inventory import register_inventory_entry
from app.models.inventory import MovimientoInventario, Usuario
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


def test_quantity_must_be_positive_integer():
    with pytest.raises(ValidationError):
        InventoryEntryCreate(producto_id=1, cantidad=0, motivo="Compra")

    with pytest.raises(ValidationError):
        InventoryEntryCreate(producto_id=1, cantidad=-2, motivo="Compra")


def test_register_entry_updates_stock_and_creates_movement():
    product = Item(id=1, activo=True, stock_actual=20)
    product.actualizado_en = datetime.now(timezone.utc)
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
