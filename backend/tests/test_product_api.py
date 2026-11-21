
URL = "/api/v1/inventory/items/"

PRODUCT = {
    "codigo": "PAN-JEAN-32",
    "nombre": "Pantalón jean azul",
    "precio_unitario": 24.99,
    "talla": "32",
    "stock_actual": 5,
}


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
