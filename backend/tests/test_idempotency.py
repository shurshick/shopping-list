from app.models import ClientOperation
from app.database import SessionLocal

from .conftest import setup_admin
from .test_security import auth


def test_replayed_create_list_does_not_create_duplicate(client):
    token = setup_admin(client)
    payload = {"name": "weekly", "client_operation_id": "op-list-1", "temp_id": "-1"}

    first = client.post("/lists", json=payload, headers=auth(token))
    second = client.post("/lists", json=payload, headers=auth(token))
    sync = client.get("/sync", headers=auth(token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert [item["name"] for item in sync.json()["lists"]].count("weekly") == 1


def test_replayed_create_item_does_not_create_duplicate(client):
    token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "weekly"}, headers=auth(token)).json()["id"]
    payload = {
        "name": "milk",
        "quantity": "1",
        "client_operation_id": "op-item-1",
        "temp_id": "-10",
    }

    first = client.post(f"/lists/{list_id}/items", json=payload, headers=auth(token))
    second = client.post(f"/lists/{list_id}/items", json=payload, headers=auth(token))
    sync = client.get("/sync", headers=auth(token)).json()
    activity = client.get(f"/lists/{list_id}/activity", headers=auth(token)).json()["events"]
    items = sync["lists"][0]["items"]

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert [item["name"] for item in items].count("milk") == 1
    assert len([event for event in activity if event["action"] == "item_created" and event["item_name"] == "milk"]) == 1


def test_create_item_response_loss_retry_returns_original_result(client):
    token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "weekly"}, headers=auth(token)).json()["id"]
    operation_id = "op-response-lost"
    payload = {
        "name": "bread",
        "quantity": "2",
        "client_operation_id": operation_id,
        "temp_id": "-20",
    }

    applied = client.post(f"/lists/{list_id}/items", json=payload, headers=auth(token))
    retried = client.post(f"/lists/{list_id}/items", json=payload, headers=auth(token))
    sync = client.get("/sync", headers=auth(token)).json()
    items = sync["lists"][0]["items"]

    assert applied.status_code == 200
    assert retried.status_code == 200
    assert applied.json() == retried.json()
    assert len([item for item in items if item["name"] == "bread"]) == 1


def test_create_item_stores_temp_id_mapping(client):
    token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "weekly"}, headers=auth(token)).json()["id"]

    response = client.post(
        f"/lists/{list_id}/items",
        json={
            "name": "cheese",
            "quantity": "",
            "client_operation_id": "op-temp-map",
            "temp_id": "-30",
        },
        headers=auth(token),
    )

    with SessionLocal() as db:
        operation = db.query(ClientOperation).filter_by(client_operation_id="op-temp-map").one()

    assert response.status_code == 200
    assert operation.temp_id == "-30"
    assert operation.resource_id == response.json()["id"]


def test_old_client_without_client_operation_id_still_works(client):
    token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "weekly"}, headers=auth(token)).json()["id"]

    first = client.post(f"/lists/{list_id}/items", json={"name": "eggs", "quantity": "10"}, headers=auth(token))
    second = client.post(f"/lists/{list_id}/items", json={"name": "eggs", "quantity": "10"}, headers=auth(token))
    sync = client.get("/sync", headers=auth(token)).json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert [item["name"] for item in sync["lists"][0]["items"]].count("eggs") == 2
