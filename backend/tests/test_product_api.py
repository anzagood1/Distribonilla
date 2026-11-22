from app.api.dependencies import get_current_user
from app.main import app
from app.models.inventory import Usuario

URL = "/api/v1/inventory/items/"

PRODUCT = {
    "codigo": "PAN-JEAN-32",
    "nombre": "Pantalón jean azul",
    "precio_unitario": 24.99,
    "talla": "32",
    "stock_actual": 5,
}


def test_prod_api_01_create_and_list_product(client):
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        response = client.post(URL, json=PRODUCT)
        assert response.status_code == 201
        body = response.json()
        assert body["talla"] == "32"
        assert body["precio_unitario"] == 24.99
        assert body["aplica_iva"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    listed = client.get(URL).json()
    assert [item["codigo"] for item in listed] == ["PAN-JEAN-32"]


def test_prod_api_02_invalid_price_returns_422(client):
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        response = client.post(URL, json={**PRODUCT, "precio_unitario": 0})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_tc_apl_create_without_token_returns_401(client):
    response = client.post(URL, json=PRODUCT)
    assert response.status_code == 401


def test_tc_apl_create_unregistered_user_returns_403(client, monkeypatch):
    import uuid
    from unittest.mock import Mock

    fake = Mock()
    fake.auth.get_user.return_value.user.id = str(uuid.uuid4())
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: fake)

    response = client.post(
        URL,
        json=PRODUCT,
        headers={"Authorization": "Bearer simulated"},
    )
    assert response.status_code == 403


def test_prod_api_03_update_size(client):
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        item_id = client.post(URL, json=PRODUCT).json()["id"]

        response = client.put(f"{URL}{item_id}", json={"talla": "34"})
        assert response.status_code == 200
        assert response.json()["talla"] == "34"
        assert response.json()["nombre"] == "Pantalón jean azul"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_tc_apl02_put_without_token_returns_401(client):
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        item_id = client.post(URL, json=PRODUCT).json()["id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    response = client.put(
        f"{URL}{item_id}",
        json={"precio_unitario": -1},
    )
    assert response.status_code == 401


def test_tc_apl02_put_negative_price_by_authorized_user_returns_422(client):
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        item_id = client.post(URL, json=PRODUCT).json()["id"]
        response = client.put(
            f"{URL}{item_id}",
            json={"precio_unitario": -1},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_tc_apl02_put_unregistered_user_returns_403(client, monkeypatch):
    import uuid
    from unittest.mock import Mock

    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        item_id = client.post(URL, json=PRODUCT).json()["id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    fake = Mock()
    fake.auth.get_user.return_value.user.id = str(uuid.uuid4())
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: fake)

    response = client.put(
        f"{URL}{item_id}",
        json={"precio_unitario": -1},
        headers={"Authorization": "Bearer simulated"},
    )
    assert response.status_code == 403

    listed = client.get(URL).json()
    item = next(product for product in listed if product["id"] == item_id)
    assert item["precio_unitario"] == 24.99


def test_prod_api_get_and_put_expose_low_stock_flag(client):
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    try:
        item_id = client.post(URL, json=PRODUCT).json()["id"]
        response = client.put(
            f"{URL}{item_id}",
            json={"stock_minimo": 6},
        )
        assert response.status_code == 200
        assert response.json()["stock_bajo"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    item = next(
        product for product in client.get(URL).json() if product["id"] == item_id
    )
    assert item["stock_bajo"] is True
