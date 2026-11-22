from app.api.dependencies import get_current_user
from app.main import app
from app.models.inventory import Usuario
from app.models.item import Item

ITEMS_URL = "/api/v1/inventory/items/"


def add_product(db_session, codigo, stock_actual, stock_minimo):
    product = Item(
        codigo=codigo,
        nombre=f"Producto {codigo}",
        precio_unitario=10,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def test_tc_inv_12_update_with_negative_threshold_keeps_product(client, db_session):
    product = add_product(db_session, "P-1", stock_actual=5, stock_minimo=3)

    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        response = client.put(
            f"{ITEMS_URL}{product.id}",
            json={"stock_minimo": -1},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422

    db_session.refresh(product)
    assert product.stock_minimo == 3


def test_low_stock_flag_follows_stock_changes(client, db_session):
    product = add_product(db_session, "P-1", stock_actual=4, stock_minimo=3)

    def stock_bajo():
        [item] = client.get(ITEMS_URL).json()
        return item["stock_bajo"]

    assert stock_bajo() is False

    product.stock_actual = 3
    db_session.commit()
    assert stock_bajo() is True

    product.stock_actual = 4
    db_session.commit()
    assert stock_bajo() is False

    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        response = client.put(
            f"{ITEMS_URL}{product.id}",
            json={"stock_minimo": 4},
        )
        assert response.status_code == 200
        assert response.json()["stock_bajo"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_put_rejects_direct_stock_actual_changes(client, db_session):
    product = add_product(db_session, "P-1", stock_actual=5, stock_minimo=3)

    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        response = client.put(
            f"{ITEMS_URL}{product.id}",
            json={"stock_actual": 100},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    db_session.refresh(product)
    assert product.stock_actual == 5
