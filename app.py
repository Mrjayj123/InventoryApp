"""
Inventory Management System - Flask REST API

Endpoints:
  CRUD:
    GET    /api/inventory              List all items (supports ?search=&category=)
    GET    /api/inventory/<id>         Get a single item
    POST   /api/inventory              Create an item
    PUT    /api/inventory/<id>         Update an item
    DELETE /api/inventory/<id>         Delete an item

  External API (OpenFoodFacts):
    GET    /api/lookup/barcode/<code>  Look up a product by barcode (no DB write)
    GET    /api/lookup/name/<name>     Search products by name (no DB write)
    POST   /api/inventory/import/<code> Fetch by barcode AND create an inventory item
"""
from flask import Flask, request, jsonify

from config import Config
from models import db, InventoryItem
from external_api import (
    fetch_product_by_barcode,
    search_products_by_name,
    ExternalAPIError,
)


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    register_error_handlers(app)
    return app


def register_routes(app):

    # ---------- CRUD ----------

    @app.route("/api/inventory", methods=["GET"])
    def list_items():
        query = InventoryItem.query
        search = request.args.get("search")
        category = request.args.get("category")
        if search:
            query = query.filter(InventoryItem.name.ilike(f"%{search}%"))
        if category:
            query = query.filter(InventoryItem.category.ilike(f"%{category}%"))
        items = query.order_by(InventoryItem.id).all()
        return jsonify([item.to_dict() for item in items]), 200

    @app.route("/api/inventory/<int:item_id>", methods=["GET"])
    def get_item(item_id):
        item = db.session.get(InventoryItem, item_id)
        if not item:
            return jsonify({"error": f"Item {item_id} not found"}), 404
        return jsonify(item.to_dict()), 200

    @app.route("/api/inventory", methods=["POST"])
    def create_item():
        data = request.get_json(silent=True) or {}
        error = _validate_item_payload(data, require_name=True)
        if error:
            return jsonify({"error": error}), 400

        if data.get("barcode") and InventoryItem.query.filter_by(barcode=data["barcode"]).first():
            return jsonify({"error": f"Item with barcode '{data['barcode']}' already exists"}), 409

        item = InventoryItem(
            name=data["name"],
            barcode=data.get("barcode"),
            category=data.get("category"),
            quantity=data.get("quantity", 0),
            price=data.get("price", 0.0),
            description=data.get("description"),
            image_url=data.get("image_url"),
            brand=data.get("brand"),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201

    @app.route("/api/inventory/<int:item_id>", methods=["PUT"])
    def update_item(item_id):
        item = db.session.get(InventoryItem, item_id)
        if not item:
            return jsonify({"error": f"Item {item_id} not found"}), 404

        data = request.get_json(silent=True) or {}
        error = _validate_item_payload(data, require_name=False)
        if error:
            return jsonify({"error": error}), 400

        for field in ("name", "barcode", "category", "quantity", "price",
                      "description", "image_url", "brand"):
            if field in data:
                setattr(item, field, data[field])

        db.session.commit()
        return jsonify(item.to_dict()), 200

    @app.route("/api/inventory/<int:item_id>", methods=["DELETE"])
    def delete_item(item_id):
        item = db.session.get(InventoryItem, item_id)
        if not item:
            return jsonify({"error": f"Item {item_id} not found"}), 404
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": f"Item {item_id} deleted"}), 200

    # ---------- External API integration ----------

    @app.route("/api/lookup/barcode/<string:barcode>", methods=["GET"])
    def lookup_barcode(barcode):
        try:
            product = fetch_product_by_barcode(
                barcode, app.config["OFF_PRODUCT_URL"], app.config["EXTERNAL_API_TIMEOUT"]
            )
        except ExternalAPIError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify(product), 200

    @app.route("/api/lookup/name/<string:name>", methods=["GET"])
    def lookup_name(name):
        try:
            products = search_products_by_name(
                name, app.config["OFF_SEARCH_URL"], app.config["EXTERNAL_API_TIMEOUT"]
            )
        except ExternalAPIError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify(products), 200

    @app.route("/api/inventory/import/<string:barcode>", methods=["POST"])
    def import_item(barcode):
        if InventoryItem.query.filter_by(barcode=barcode).first():
            return jsonify({"error": f"Item with barcode '{barcode}' already exists"}), 409

        try:
            product = fetch_product_by_barcode(
                barcode, app.config["OFF_PRODUCT_URL"], app.config["EXTERNAL_API_TIMEOUT"]
            )
        except ExternalAPIError as exc:
            return jsonify({"error": str(exc)}), 502

        overrides = request.get_json(silent=True) or {}
        item = InventoryItem(
            name=overrides.get("name", product["name"]),
            barcode=product["barcode"] or barcode,
            category=overrides.get("category", product["category"]),
            quantity=overrides.get("quantity", 0),
            price=overrides.get("price", 0.0),
            description=overrides.get("description", product["description"]),
            image_url=overrides.get("image_url", product["image_url"]),
            brand=overrides.get("brand", product["brand"]),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500


def _validate_item_payload(data, require_name=True):
    """Returns an error message string, or None if valid."""
    if require_name and not data.get("name"):
        return "Field 'name' is required"
    if "quantity" in data and not isinstance(data["quantity"], int):
        return "Field 'quantity' must be an integer"
    if "quantity" in data and data["quantity"] < 0:
        return "Field 'quantity' must be non-negative"
    if "price" in data and not isinstance(data["price"], (int, float)):
        return "Field 'price' must be a number"
    if "price" in data and data["price"] < 0:
        return "Field 'price' must be non-negative"
    return None


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
