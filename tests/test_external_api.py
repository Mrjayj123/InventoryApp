"""
Unit tests for external API integration (OpenFoodFacts).

All network calls are mocked — no real HTTP requests are made during tests.
"""
from unittest.mock import patch, MagicMock
import pytest

from external_api import (
    fetch_product_by_barcode,
    search_products_by_name,
    ExternalAPIError,
)

BASE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"


def _mock_response(json_data, status_code=200, raise_for_status_side_effect=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    if raise_for_status_side_effect:
        mock_resp.raise_for_status.side_effect = raise_for_status_side_effect
    return mock_resp


# ---------- fetch_product_by_barcode ----------

@patch("external_api.requests.get")
def test_fetch_product_by_barcode_success(mock_get):
    mock_get.return_value = _mock_response({
        "status": 1,
        "product": {
            "code": "1234567890123",
            "product_name": "Chocolate Bar",
            "categories": "Snacks, Sweet snacks",
            "brands": "TestBrand",
            "image_url": "http://example.com/img.jpg",
        },
    })
    result = fetch_product_by_barcode("1234567890123", BASE_URL)
    assert result["name"] == "Chocolate Bar"
    assert result["brand"] == "TestBrand"
    assert result["category"] == "Snacks"


@patch("external_api.requests.get")
def test_fetch_product_by_barcode_not_found(mock_get):
    mock_get.return_value = _mock_response({"status": 0})
    with pytest.raises(ExternalAPIError, match="No product found"):
        fetch_product_by_barcode("0000000000000", BASE_URL)


@patch("external_api.requests.get")
def test_fetch_product_by_barcode_network_failure(mock_get):
    import requests
    mock_get.side_effect = requests.ConnectionError("network down")
    with pytest.raises(ExternalAPIError, match="Failed to reach external API"):
        fetch_product_by_barcode("123", BASE_URL)


# ---------- search_products_by_name ----------

@patch("external_api.requests.get")
def test_search_products_by_name_success(mock_get):
    mock_get.return_value = _mock_response({
        "products": [
            {"code": "111", "product_name": "Peanut Butter", "brands": "BrandA"},
            {"code": "222", "product_name": "Peanut Butter Crunchy", "brands": "BrandB"},
        ]
    })
    results = search_products_by_name("peanut butter", SEARCH_URL)
    assert len(results) == 2
    assert results[0]["name"] == "Peanut Butter"


@patch("external_api.requests.get")
def test_search_products_by_name_no_results(mock_get):
    mock_get.return_value = _mock_response({"products": []})
    results = search_products_by_name("nonexistent-product-xyz", SEARCH_URL)
    assert results == []


@patch("external_api.requests.get")
def test_search_products_by_name_network_failure(mock_get):
    import requests
    mock_get.side_effect = requests.Timeout("timed out")
    with pytest.raises(ExternalAPIError):
        search_products_by_name("milk", SEARCH_URL)


# ---------- Flask route integration (mocked external calls) ----------

@patch("external_api.requests.get")
def test_lookup_barcode_route(mock_get, client):
    mock_get.return_value = _mock_response({
        "status": 1,
        "product": {"code": "999", "product_name": "Mock Soda"},
    })
    response = client.get("/api/lookup/barcode/999")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Mock Soda"


@patch("external_api.requests.get")
def test_lookup_barcode_route_upstream_failure(mock_get, client):
    mock_get.return_value = _mock_response({"status": 0})
    response = client.get("/api/lookup/barcode/000")
    assert response.status_code == 502


@patch("external_api.requests.get")
def test_import_item_route_creates_inventory_item(mock_get, client):
    mock_get.return_value = _mock_response({
        "status": 1,
        "product": {"code": "555", "product_name": "Imported Snack", "brands": "SnackCo"},
    })
    response = client.post("/api/inventory/import/555", json={"quantity": 30, "price": 2.5})
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Imported Snack"
    assert data["quantity"] == 30
    assert data["barcode"] == "555"

    # Confirm it now exists in the DB via the regular CRUD endpoint
    follow_up = client.get("/api/inventory")
    assert len(follow_up.get_json()) == 1


@patch("external_api.requests.get")
def test_import_item_route_duplicate_barcode(mock_get, client, sample_item):
    response = client.post("/api/inventory/import/1234567890123", json={})
    # sample_item fixture already created an item with this barcode
    assert response.status_code == 409
    mock_get.assert_not_called()
