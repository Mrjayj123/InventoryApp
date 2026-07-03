"""
CLI Interface for the Inventory Management System.

Talks to the Flask REST API over HTTP. Run the server first:
    python app.py

Usage examples:
    python cli.py list
    python cli.py list --search milk
    python cli.py view 3
    python cli.py add --name "Coffee Beans" --quantity 50 --price 12.99
    python cli.py edit 3 --quantity 40
    python cli.py delete 3
    python cli.py lookup-barcode 3017620422003
    python cli.py lookup-name "peanut butter"
    python cli.py import 3017620422003 --quantity 20 --price 4.99
"""
import click
import requests
from tabulate import tabulate

API_BASE = "http://127.0.0.1:5000/api"


def _handle_response(response, success_codes=(200, 201)):
    try:
        payload = response.json()
    except ValueError:
        click.echo(f"Error: non-JSON response (status {response.status_code})", err=True)
        raise SystemExit(1)

    if response.status_code not in success_codes:
        click.echo(f"Error: {payload.get('error', payload)}", err=True)
        raise SystemExit(1)
    return payload


def _print_items(items):
    if not items:
        click.echo("No items found.")
        return
    rows = [
        [i["id"], i["name"], i.get("barcode", ""), i.get("category", ""),
         i["quantity"], i["price"]]
        for i in items
    ]
    click.echo(tabulate(rows, headers=["ID", "Name", "Barcode", "Category", "Qty", "Price"]))


def _print_item(item):
    click.echo(tabulate(item.items(), headers=["Field", "Value"]))


@click.group()
def cli():
    """Inventory Management CLI."""
    pass


@cli.command("list")
@click.option("--search", default=None, help="Filter by name substring")
@click.option("--category", default=None, help="Filter by category substring")
def list_items(search, category):
    """List all inventory items."""
    params = {}
    if search:
        params["search"] = search
    if category:
        params["category"] = category
    response = requests.get(f"{API_BASE}/inventory", params=params)
    items = _handle_response(response)
    _print_items(items)


@cli.command("view")
@click.argument("item_id", type=int)
def view_item(item_id):
    """View a single inventory item by ID."""
    response = requests.get(f"{API_BASE}/inventory/{item_id}")
    item = _handle_response(response)
    _print_item(item)


@cli.command("add")
@click.option("--name", required=True, help="Product name")
@click.option("--barcode", default=None)
@click.option("--category", default=None)
@click.option("--quantity", default=0, type=int)
@click.option("--price", default=0.0, type=float)
@click.option("--description", default=None)
@click.option("--brand", default=None)
def add_item(name, barcode, category, quantity, price, description, brand):
    """Add a new inventory item manually."""
    payload = {
        "name": name, "barcode": barcode, "category": category,
        "quantity": quantity, "price": price,
        "description": description, "brand": brand,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    response = requests.post(f"{API_BASE}/inventory", json=payload)
    item = _handle_response(response, success_codes=(201,))
    click.echo("Item created:")
    _print_item(item)


@cli.command("edit")
@click.argument("item_id", type=int)
@click.option("--name", default=None)
@click.option("--barcode", default=None)
@click.option("--category", default=None)
@click.option("--quantity", default=None, type=int)
@click.option("--price", default=None, type=float)
@click.option("--description", default=None)
@click.option("--brand", default=None)
def edit_item(item_id, **kwargs):
    """Edit fields on an existing inventory item."""
    payload = {k: v for k, v in kwargs.items() if v is not None}
    if not payload:
        click.echo("Nothing to update — provide at least one field.", err=True)
        raise SystemExit(1)
    response = requests.put(f"{API_BASE}/inventory/{item_id}", json=payload)
    item = _handle_response(response)
    click.echo("Item updated:")
    _print_item(item)


@cli.command("delete")
@click.argument("item_id", type=int)
@click.confirmation_option(prompt="Are you sure you want to delete this item?")
def delete_item(item_id):
    """Delete an inventory item."""
    response = requests.delete(f"{API_BASE}/inventory/{item_id}")
    result = _handle_response(response)
    click.echo(result.get("message", "Deleted."))


@cli.command("lookup-barcode")
@click.argument("barcode")
def lookup_barcode(barcode):
    """Look up product details by barcode via OpenFoodFacts (no DB write)."""
    response = requests.get(f"{API_BASE}/lookup/barcode/{barcode}")
    product = _handle_response(response)
    _print_item(product)


@cli.command("lookup-name")
@click.argument("name")
def lookup_name(name):
    """Search product details by name via OpenFoodFacts (no DB write)."""
    response = requests.get(f"{API_BASE}/lookup/name/{name}")
    products = _handle_response(response)
    _print_items([{**p, "id": "-"} for p in products]) if products else click.echo("No results.")


@cli.command("import")
@click.argument("barcode")
@click.option("--quantity", default=0, type=int)
@click.option("--price", default=0.0, type=float)
@click.option("--name", default=None, help="Override the fetched product name")
@click.option("--category", default=None, help="Override the fetched category")
def import_item(barcode, quantity, price, name, category):
    """Fetch a product by barcode from OpenFoodFacts and add it to inventory."""
    overrides = {"quantity": quantity, "price": price}
    if name:
        overrides["name"] = name
    if category:
        overrides["category"] = category
    response = requests.post(f"{API_BASE}/inventory/import/{barcode}", json=overrides)
    item = _handle_response(response, success_codes=(201,))
    click.echo("Item imported and added to inventory:")
    _print_item(item)


if __name__ == "__main__":
    cli()
