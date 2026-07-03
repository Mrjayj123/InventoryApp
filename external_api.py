"""
Integration layer for the OpenFoodFacts external API.

Isolated into its own module so it can be mocked easily in unit tests
and swapped out for a different provider without touching route logic.
"""
import requests


class ExternalAPIError(Exception):
    """Raised when the external API call fails or returns unusable data."""


def _extract_product_fields(product: dict) -> dict:
    """Normalize a raw OpenFoodFacts product payload into our schema shape."""
    return {
        "name": product.get("product_name") or product.get("generic_name") or "Unknown Product",
        "barcode": product.get("code"),
        "category": (product.get("categories") or "").split(",")[0].strip() or None,
        "brand": (product.get("brands") or "").split(",")[0].strip() or None,
        "description": product.get("generic_name") or product.get("ingredients_text") or None,
        "image_url": product.get("image_url") or product.get("image_front_url"),
    }


def fetch_product_by_barcode(barcode: str, base_url: str, timeout: int = 8) -> dict:
    """
    Fetch a single product from OpenFoodFacts by barcode.

    Raises ExternalAPIError if the request fails or the product isn't found.
    """
    url = base_url.format(barcode=barcode)
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExternalAPIError(f"Failed to reach external API: {exc}") from exc

    data = response.json()
    if data.get("status") != 1 or "product" not in data:
        raise ExternalAPIError(f"No product found for barcode '{barcode}'")

    return _extract_product_fields(data["product"])


def search_products_by_name(name: str, search_url: str, timeout: int = 8, page_size: int = 10) -> list:
    """
    Search OpenFoodFacts for products matching a name query.

    Returns a list of normalized product dicts (may be empty).
    Raises ExternalAPIError if the request itself fails.
    """
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
    }
    try:
        response = requests.get(search_url, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExternalAPIError(f"Failed to reach external API: {exc}") from exc

    data = response.json()
    products = data.get("products", [])
    return [_extract_product_fields(p) for p in products]
