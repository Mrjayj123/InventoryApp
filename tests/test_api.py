"""
Unit tests for the CRUD inventory endpoints.
"""


def test_list_items_empty(client):
    response = client.get("/api/inventory")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_item_success(client):
    payload = {"name": "Blue Pen", "quantity": 25, "price": 1.5, "category": "Stationery"}
    response = client.post("/api/inventory", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Blue Pen"
    assert data["quantity"] == 25
    assert data["id"] is not None


def test_create_item_missing_name(client):
    response = client.post("/api/inventory", json={"quantity": 5})
    assert response.status_code == 400
    assert "name" in response.get_json()["error"]


def test_create_item_negative_quantity(client):
    response = client.post("/api/inventory", json={"name": "Bad Item", "quantity": -1})
    assert response.status_code == 400


def test_create_item_duplicate_barcode(client):
    payload = {"name": "Item A", "barcode": "999", "quantity": 1, "price": 1.0}
    client.post("/api/inventory", json=payload)
    response = client.post("/api/inventory", json={**payload, "name": "Item B"})
    assert response.status_code == 409


def test_get_item_success(client, sample_item):
    response = client.get(f"/api/inventory/{sample_item}")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Test Widget"


def test_get_item_not_found(client):
    response = client.get("/api/inventory/9999")
    assert response.status_code == 404


def test_list_items_with_search(client, sample_item):
    client.post("/api/inventory", json={"name": "Other Product", "quantity": 1, "price": 1.0})
    response = client.get("/api/inventory?search=Test")
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Widget"


def test_update_item_success(client, sample_item):
    response = client.put(f"/api/inventory/{sample_item}", json={"quantity": 50})
    assert response.status_code == 200
    assert response.get_json()["quantity"] == 50


def test_update_item_not_found(client):
    response = client.put("/api/inventory/9999", json={"quantity": 5})
    assert response.status_code == 404


def test_update_item_invalid_price(client, sample_item):
    response = client.put(f"/api/inventory/{sample_item}", json={"price": -5})
    assert response.status_code == 400


def test_delete_item_success(client, sample_item):
    response = client.delete(f"/api/inventory/{sample_item}")
    assert response.status_code == 200
    follow_up = client.get(f"/api/inventory/{sample_item}")
    assert follow_up.status_code == 404


def test_delete_item_not_found(client):
    response = client.delete("/api/inventory/9999")
    assert response.status_code == 404


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
