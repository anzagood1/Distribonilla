import pytest
from pydantic import ValidationError

from app.models.item import Item
from app.schemas.item import ItemUpdate
from app.services.stock_alerts import STOCK_MINIMO_POR_DEFECTO, es_stock_bajo

ITEMS_URL = "/api/v1/inventory/items/"
LOW_STOCK_URL = "/api/v1/inventory/items/low-stock/"


def add_product(db_session, codigo, stock_actual, stock_minimo=3, **extra):
    product = Item(
        codigo=codigo,
        nombre=extra.pop("nombre", f"Producto {codigo}"),
        precio_unitario=10,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
        **extra,
    )
    db_session.add(product)
    db_session.commit()
    return product


# --------------------------------------------------------------------------
# TC-INV-11 — valores límite alrededor del umbral
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stock_actual, esperado",
    [(2, True), (3, True), (4, False)],
    ids=["umbral-1", "umbral", "umbral+1"],
)
def test_tc_inv_11_rule_boundaries(stock_actual, esperado):
    assert es_stock_bajo(stock_actual, stock_minimo=3) is esperado


@pytest.mark.parametrize(
    "stock_actual, esperado",
    [(2, True), (3, True), (4, False)],
    ids=["umbral-1", "umbral", "umbral+1"],
)
def test_tc_inv_11_api_flag_per_product(client, db_session, stock_actual, esperado):
    """Cada stock se consulta como prueba independiente."""
    add_product(db_session, "P-1", stock_actual=stock_actual, stock_minimo=3)

    [producto] = client.get(ITEMS_URL).json()
    assert producto["stock_bajo"] is esperado

    low_stock = client.get(LOW_STOCK_URL).json()
    assert [p["codigo"] for p in low_stock] == (["P-1"] if esperado else [])


def test_tc_inv_11_low_stock_endpoint_lists_only_alerts(client, db_session):
    add_product(db_session, "STOCK-2", stock_actual=2)
    add_product(db_session, "STOCK-3", stock_actual=3)
    add_product(db_session, "STOCK-4", stock_actual=4)

    response = client.get(LOW_STOCK_URL)

    assert response.status_code == 200
    # Primero el más crítico (más lejos por debajo del mínimo)
    assert [p["codigo"] for p in response.json()] == ["STOCK-2", "STOCK-3"]
    assert all(p["stock_bajo"] for p in response.json())


# --------------------------------------------------------------------------
# TC-INV-12 — umbral negativo o ausente
# --------------------------------------------------------------------------


def test_tc_inv_12_rule_rejects_negative_threshold():
    with pytest.raises(ValueError):
        es_stock_bajo(5, stock_minimo=-1)


def test_tc_inv_12_api_rejects_negative_threshold_on_create(client):
    response = client.post(
        ITEMS_URL, json={"nombre": "X", "precio_unitario": 1, "stock_minimo": -1}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("valor", [-1, None])
def test_tc_inv_12_update_rejects_negative_or_null_threshold(valor):
    with pytest.raises(ValidationError):
        ItemUpdate(stock_minimo=valor)


def test_tc_inv_12_update_with_negative_threshold_keeps_product(client, db_session):
    product = add_product(db_session, "P-1", stock_actual=5, stock_minimo=3)

    response = client.put(f"{ITEMS_URL}{product.id}", json={"stock_minimo": -1})

    assert response.status_code == 422
    db_session.refresh(product)
    assert product.stock_minimo == 3


@pytest.mark.parametrize("stock_actual, esperado", [(0, True), (1, False), (50, False)])
def test_tc_inv_12_unconfigured_threshold_uses_default(stock_actual, esperado):
    """Sin mínimo configurado (None o 0): solo alerta cuando se agota."""
    assert STOCK_MINIMO_POR_DEFECTO == 0
    assert es_stock_bajo(stock_actual, stock_minimo=None) is esperado


def test_tc_inv_12_product_created_without_threshold_has_no_false_alert(client):
    response = client.post(
        ITEMS_URL,
        json={
            "codigo": "SIN-MIN",
            "nombre": "X",
            "precio_unitario": 1,
            "stock_actual": 5,
        },
    )
    assert response.status_code == 201
    assert response.json()["stock_minimo"] == 0
    assert response.json()["stock_bajo"] is False
    assert client.get(LOW_STOCK_URL).json() == []


def test_low_stock_excludes_inactive_products(client, db_session):
    add_product(db_session, "ACTIVO", stock_actual=1)
    add_product(db_session, "INACTIVO", stock_actual=1, activo=False)

    assert [p["codigo"] for p in client.get(LOW_STOCK_URL).json()] == ["ACTIVO"]
    flags = {p["codigo"]: p["stock_bajo"] for p in client.get(ITEMS_URL).json()}
    assert flags == {"ACTIVO": True, "INACTIVO": False}


def test_low_stock_flag_follows_stock_changes(client, db_session):
    """La alerta sigue al stock que dejan los movimientos y al umbral configurado."""
    product = add_product(db_session, "P-1", stock_actual=4, stock_minimo=3)

    def stock_bajo():
        [p] = client.get(ITEMS_URL).json()
        return p["stock_bajo"]

    assert stock_bajo() is False

    # Simula el stock que deja una salida (GRUPO5-11) o entrada (GRUPO5-10)
    product.stock_actual = 3
    db_session.commit()
    assert stock_bajo() is True

    product.stock_actual = 4
    db_session.commit()
    assert stock_bajo() is False

    # El umbral sí se configura por PUT
    url = f"{ITEMS_URL}{product.id}"
    assert client.put(url, json={"stock_minimo": 4}).json()["stock_bajo"] is True


def test_low_stock_pagination_is_validated(client):
    assert client.get(LOW_STOCK_URL, params={"limit": 0}).status_code == 422
    assert client.get(LOW_STOCK_URL, params={"skip": -1}).status_code == 422
