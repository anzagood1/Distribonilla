from datetime import date, datetime, timezone
from unittest.mock import Mock

import pytest

from app.api.dependencies import get_current_user
from app.api.endpoints.inventory import read_item_movements
from app.main import app
from app.models.inventory import MovimientoInventario, Usuario
from app.models.item import Item
from fastapi import HTTPException

URL = "/api/v1/inventory/items/"

PRODUCT = {
    "codigo": "PAN-JEAN-32",
    "nombre": "Pantalón jean azul",
    "precio_unitario": 24.99,
    "talla": "32",
    "stock_actual": 5,
}


@pytest.fixture(autouse=True)
def authenticated_product_requests():
    app.dependency_overrides[get_current_user] = lambda: Usuario(
        id=7,
        activo=True,
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_prod_api_01_create_and_list_product(client):
    response = client.post(URL, json=PRODUCT)
    assert response.status_code == 201
    body = response.json()
    assert body["talla"] == "32"
    assert body["precio_unitario"] == 24.99
    assert body["aplica_iva"] is True

    listed = client.get(URL).json()
    assert [item["codigo"] for item in listed] == ["PAN-JEAN-32"]


def test_prod_api_02_invalid_price_returns_422(client):
    response = client.post(URL, json={**PRODUCT, "precio_unitario": 0})
    assert response.status_code == 422


def test_prod_api_03_update_size(client):
    item_id = client.post(URL, json=PRODUCT).json()["id"]

    response = client.put(f"{URL}{item_id}", json={"talla": "34"})
    assert response.status_code == 200
    assert response.json()["talla"] == "34"
    assert response.json()["nombre"] == "Pantalón jean azul"


def test_create_product_requires_bearer_token(client):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post(URL, json=PRODUCT)
    assert response.status_code == 401
    assert response.json() == {"detail": "Autenticación requerida"}


def test_read_item_movements_orders_complete_history():
    item_query = Mock()
    item_query.filter.return_value = item_query
    item_query.first.return_value = Item(id=1, activo=True, stock_actual=57)

    first = MovimientoInventario(
        id=16,
        producto_id=1,
        tipo="entrada",
        cantidad=5,
        motivo="Compra",
        notas="Entrada prueba",
        fecha=datetime.now(timezone.utc),
        usuario_id=4,
        stock_anterior=54,
        stock_resultante=59,
    )
    second = MovimientoInventario(
        id=17,
        producto_id=1,
        tipo="salida",
        cantidad=2,
        motivo="ajuste",
        notas="Salida prueba",
        fecha=datetime.now(timezone.utc),
        usuario_id=4,
        stock_anterior=59,
        stock_resultante=57,
    )

    movement_query = Mock()
    movement_query.filter.return_value = movement_query
    movement_query.order_by.return_value = movement_query
    movement_query.all.return_value = [first, second]

    db = Mock()
    db.query.side_effect = lambda model: (
        item_query if model is Item else movement_query
    )

    movements = read_item_movements(item_id=1, db=db)

    assert [movement.tipo for movement in movements] == ["entrada", "salida"]
    assert [movement.cantidad for movement in movements] == [5, 2]
    assert movements[-1].stock_resultante == 57


def test_read_item_movements_rejects_reversed_date_range():
    item_query = Mock()
    item_query.filter.return_value = item_query
    item_query.first.return_value = Item(id=1, activo=True, stock_actual=57)
    db = Mock()
    db.query.return_value = item_query

    try:
        read_item_movements(
            item_id=1,
            db=db,
            from_date=date(2026, 11, 22),
            to_date=date(2026, 11, 21),
        )
    except HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Expected reversed date range to be rejected")
