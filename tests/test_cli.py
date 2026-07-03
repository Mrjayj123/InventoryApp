"""
Unit tests for the CLI interface.

The CLI talks to the API over HTTP via `requests`, so those calls are mocked
here — these tests don't require a running Flask server.
"""
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cli import cli


def _mock_response(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    return mock_resp


@patch("cli.requests.get")
def test_list_items(mock_get):
    mock_get.return_value = _mock_response([
        {"id": 1, "name": "Widget", "barcode": "111", "category": "Tools", "quantity": 5, "price": 3.5}
    ])
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Widget" in result.output


@patch("cli.requests.get")
def test_list_items_empty(mock_get):
    mock_get.return_value = _mock_response([])
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "No items found" in result.output


@patch("cli.requests.post")
def test_add_item(mock_post):
    mock_post.return_value = _mock_response(
        {"id": 1, "name": "Gadget", "quantity": 10, "price": 5.0}, status_code=201
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["add", "--name", "Gadget", "--quantity", "10", "--price", "5.0"])
    assert result.exit_code == 0
    assert "Item created" in result.output
    mock_post.assert_called_once()


@patch("cli.requests.get")
def test_view_item_not_found(mock_get):
    mock_get.return_value = _mock_response({"error": "Item 99 not found"}, status_code=404)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "99"])
    assert result.exit_code == 1
    assert "not found" in result.output


@patch("cli.requests.put")
def test_edit_item(mock_put):
    mock_put.return_value = _mock_response({"id": 1, "name": "Gadget", "quantity": 20, "price": 5.0})
    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "1", "--quantity", "20"])
    assert result.exit_code == 0
    assert "Item updated" in result.output


def test_edit_item_no_fields():
    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "1"])
    assert result.exit_code == 1
    assert "Nothing to update" in result.output


@patch("cli.requests.delete")
def test_delete_item(mock_delete):
    mock_delete.return_value = _mock_response({"message": "Item 1 deleted"})
    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "1", "--yes"])
    assert result.exit_code == 0
    assert "deleted" in result.output


@patch("cli.requests.get")
def test_lookup_barcode(mock_get):
    mock_get.return_value = _mock_response({"name": "Soda Can", "barcode": "123"})
    runner = CliRunner()
    result = runner.invoke(cli, ["lookup-barcode", "123"])
    assert result.exit_code == 0
    assert "Soda Can" in result.output


@patch("cli.requests.post")
def test_import_item(mock_post):
    mock_post.return_value = _mock_response(
        {"id": 2, "name": "Imported Product", "quantity": 15, "price": 3.99}, status_code=201
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["import", "555", "--quantity", "15", "--price", "3.99"])
    assert result.exit_code == 0
    assert "Item imported" in result.output
