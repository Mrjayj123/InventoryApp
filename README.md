# Inventory Management System

A Flask REST API + CLI admin portal backend for retail inventory management, with
real-time product enrichment from the [OpenFoodFacts](https://world.openfoodfacts.org/) API.

## Features

- **CRUD REST API** for inventory items (Flask + SQLAlchemy + SQLite)
- **External API integration** — look up products by barcode or name via OpenFoodFacts,
  and import them directly into inventory
- **CLI client** for interacting with the API from the terminal
- **33 unit tests** covering the API, external integration (fully mocked), and CLI

## Project Structure

```
inventory-system/
├── app.py                  # Flask app + routes
├── models.py                # SQLAlchemy InventoryItem model
├── external_api.py          # OpenFoodFacts integration (isolated, mockable)
├── config.py                 # App + test configuration
├── cli.py                    # CLI client
├── requirements.txt
└── tests/
    ├── conftest.py           # Shared pytest fixtures
    ├── test_api.py            # CRUD endpoint tests
    ├── test_external_api.py   # External API tests (mocked) + import route
    └── test_cli.py             # CLI tests (mocked HTTP)
```

## Setup

```bash
pip install -r requirements.txt
```

## Running the API server

```bash
python app.py
```

The server starts at `http://127.0.0.1:5000`. A SQLite file `inventory.db` is created
automatically on first run.

## REST API Reference

### CRUD

| Method | Endpoint                  | Description             |
|--------|----------------------------|--------------------------|
| GET    | `/api/inventory`            | List items (`?search=`, `?category=`) |
| GET    | `/api/inventory/<id>`       | Get one item             |
| POST   | `/api/inventory`            | Create item              |
| PUT    | `/api/inventory/<id>`       | Update item               |
| DELETE | `/api/inventory/<id>`       | Delete item               |

**Create/update body example:**
```json
{
  "name": "Coffee Beans",
  "barcode": "3017620422003",
  "category": "Beverages",
  "quantity": 50,
  "price": 12.99,
  "description": "Dark roast, 1kg",
  "brand": "RoastCo"
}
```

### External API (OpenFoodFacts)

| Method | Endpoint                              | Description                                  |
|--------|-----------------------------------------|-----------------------------------------------|
| GET    | `/api/lookup/barcode/<barcode>`          | Fetch product details (read-only, no DB write) |
| GET    | `/api/lookup/name/<name>`                | Search products by name (read-only)             |
| POST   | `/api/inventory/import/<barcode>`         | Fetch by barcode **and** create an inventory item |

The `import` endpoint accepts an optional JSON body to override/supplement fetched
fields (e.g. `{"quantity": 20, "price": 4.99}`) since OpenFoodFacts doesn't know your
stock levels or pricing.

### Health check
`GET /api/health`

## CLI Usage

Make sure the Flask server is running first (`python app.py`), then in another terminal:

```bash
python cli.py list                                        # list all items
python cli.py list --search milk --category Dairy          # filter
python cli.py view 3                                        # view one item
python cli.py add --name "Coffee Beans" --quantity 50 --price 12.99
python cli.py edit 3 --quantity 40 --price 11.99
python cli.py delete 3                                       # prompts for confirmation
python cli.py lookup-barcode 3017620422003                    # OpenFoodFacts lookup only
python cli.py lookup-name "peanut butter"
python cli.py import 3017620422003 --quantity 20 --price 4.99  # fetch + add
```

Run `python cli.py --help` or `python cli.py <command> --help` for full option lists.

## Running Tests

```bash
python -m pytest tests/ -v
```

All 33 tests pass. External API calls are mocked throughout (`unittest.mock.patch`),
so the test suite runs offline and doesn't depend on OpenFoodFacts' availability.

## Design Notes

- **SQLite is the system of record; OpenFoodFacts is enrichment only.** The external
  API is read-only from this system's perspective — it supplies name/brand/category/
  image data, but quantity, price, and all edits live in the local database.
- **`external_api.py` is intentionally decoupled** from Flask routes so it can be
  unit-tested in isolation and swapped for a different provider later.
- **Barcode uniqueness** is enforced at the API layer (409 Conflict on duplicates)
  to prevent accidental double-imports.
# InventoryApp
