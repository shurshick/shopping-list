from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models import ListInvite, ShoppingItem, User

from .conftest import register_user, setup_admin
from .test_security import auth


def test_repeated_setup_does_not_create_second_admin(client):
    admin_token = setup_admin(client)
    page = client.get("/setup")
    csrf_token = page.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]

    response = client.post(
        "/setup",
        data={
            "csrf_token": csrf_token,
            "admin_email": "second-admin@example.com",
            "admin_password": "adminpass123",
            "admin_password_confirm": "adminpass123",
            "app_name": "Список покупок",
            "external_url": "https://shopping.example.com",
            "allow_registration": "true",
        },
        headers={"origin": "http://testserver"},
    )
    status = client.get("/admin/status", headers=auth(admin_token)).json()

    assert response.status_code == 403
    assert status["users_count"] == 1
    with SessionLocal() as db:
        assert db.query(User).filter_by(is_admin=True).count() == 1


def test_server_config_does_not_expose_jwt_secret(client):
    setup_admin(client)

    response = client.get("/server-config")

    assert response.status_code == 200
    assert "jwt_secret" not in response.text.lower()


def test_server_config_does_not_expose_postgres_password(client):
    setup_admin(client)

    response = client.get("/server-config")

    assert response.status_code == 200
    assert "postgres_password" not in response.text.lower()


def test_server_config_does_not_expose_database_url(client):
    setup_admin(client)

    response = client.get("/server-config")

    assert response.status_code == 200
    assert "database_url" not in response.text.lower()


def test_user_does_not_see_another_users_list_in_sync(client):
    admin_token = setup_admin(client)
    client.post("/lists", json={"name": "admin private"}, headers=auth(admin_token))
    user_token = register_user(client, "sync-user@example.com")

    response = client.get("/sync", headers=auth(user_token))

    assert response.status_code == 200
    assert response.json()["lists"] == []


def test_user_cannot_delete_another_users_list(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "private"}, headers=auth(admin_token)).json()["id"]
    user_token = register_user(client, "delete-user@example.com")

    response = client.delete(f"/lists/{list_id}", headers=auth(user_token))

    assert response.status_code == 404


def test_create_item_stores_checked_state_atomically(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "checked"}, headers=auth(admin_token)).json()["id"]

    response = client.post(
        f"/lists/{list_id}/items",
        json={"name": "done", "quantity": "", "is_checked": True, "client_operation_id": "checked-create"},
        headers=auth(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["is_checked"] is True
    with SessionLocal() as db:
        assert db.query(ShoppingItem).filter_by(name="done", is_checked=True).count() == 1


def test_clear_checked_items_cannot_touch_foreign_list(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "foreign"}, headers=auth(admin_token)).json()["id"]
    client.post(f"/lists/{list_id}/items", json={"name": "done", "is_checked": True}, headers=auth(admin_token))
    user_token = register_user(client, "clear-user@example.com")

    response = client.delete(f"/lists/{list_id}/items/checked", headers=auth(user_token))
    sync = client.get("/sync", headers=auth(admin_token)).json()

    assert response.status_code == 404
    assert sync["lists"][0]["items"][0]["name"] == "done"


def test_expired_invite_cannot_be_accepted(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "expired"}, headers=auth(admin_token)).json()["id"]
    invite = client.post(f"/lists/{list_id}/invite", headers=auth(admin_token)).json()
    user_token = register_user(client, "expired-user@example.com")

    with SessionLocal() as db:
        row = db.query(ListInvite).filter_by(token=invite["token"]).one()
        row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        db.commit()

    response = client.post(f"/invites/{invite['token']}/accept", headers=auth(user_token))

    assert response.status_code == 404
