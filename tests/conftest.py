import pytest

from app import create_app
from config import TestConfig
from models import db, InventoryItem


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_item(app):
    with app.app_context():
        item = InventoryItem(
            name="Test Widget",
            barcode="1234567890123",
            category="Hardware",
            quantity=10,
            price=9.99,
        )
        db.session.add(item)
        db.session.commit()
        return item.id
