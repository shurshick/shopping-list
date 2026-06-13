import json

from app.cli import build_backup, migration_status

from .conftest import login, register_user, setup_admin
from .test_security import auth


def test_non_admin_cannot_open_admin_users(client):
    setup_admin(client)
    user_token = register_user(client, "user-admin-users@example.com")

    response = client.get("/admin/users", headers=auth(user_token))

    assert response.status_code == 403


def test_admin_can_open_admin_users(client):
    admin_token = setup_admin(client)
    register_user(client, "listed@example.com")

    response = client.get("/admin/users", headers=auth(admin_token))

    assert response.status_code == 200
    assert any(user["email"] == "listed@example.com" for user in response.json()["users"])
    assert "password_hash" not in response.text


def test_admin_can_disable_user_and_disabled_user_cannot_login(client):
    admin_token = setup_admin(client)
    register_user(client, "disabled@example.com", "userpass123")
    users = client.get("/admin/users", headers=auth(admin_token)).json()["users"]
    user_id = next(user["id"] for user in users if user["email"] == "disabled@example.com")

    disable = client.post(f"/admin/users/{user_id}/disable", headers=auth(admin_token))
    login_response = client.post("/auth/login", json={"email": "disabled@example.com", "password": "userpass123"})

    assert disable.status_code == 200
    assert login_response.status_code == 403


def test_admin_cannot_disable_last_active_admin(client):
    admin_token = setup_admin(client)
    users = client.get("/admin/users", headers=auth(admin_token)).json()["users"]
    admin_id = next(user["id"] for user in users if user["email"] == "admin@example.com")

    response = client.post(f"/admin/users/{admin_id}/disable", headers=auth(admin_token))

    assert response.status_code == 400


def test_admin_can_enable_user(client):
    admin_token = setup_admin(client)
    register_user(client, "enabled@example.com", "userpass123")
    users = client.get("/admin/users", headers=auth(admin_token)).json()["users"]
    user_id = next(user["id"] for user in users if user["email"] == "enabled@example.com")

    client.post(f"/admin/users/{user_id}/disable", headers=auth(admin_token))
    response = client.post(f"/admin/users/{user_id}/enable", headers=auth(admin_token))
    token = login(client, "enabled@example.com", "userpass123")

    assert response.status_code == 200
    assert token


def test_admin_can_set_user_password(client):
    admin_token = setup_admin(client)
    register_user(client, "reset@example.com", "oldpass123")
    users = client.get("/admin/users", headers=auth(admin_token)).json()["users"]
    user_id = next(user["id"] for user in users if user["email"] == "reset@example.com")

    response = client.post(
        f"/admin/users/{user_id}/set-password",
        json={"password": "newpass123"},
        headers=auth(admin_token),
    )
    login_response = client.post("/auth/login", json={"email": "reset@example.com", "password": "newpass123"})

    assert response.status_code == 200
    assert login_response.status_code == 200


def test_admin_can_open_admin_lists(client):
    admin_token = setup_admin(client)
    client.post("/lists", json={"name": "ops list"}, headers=auth(admin_token))

    response = client.get("/admin/lists", headers=auth(admin_token))

    assert response.status_code == 200
    assert any(item["name"] == "ops list" for item in response.json()["lists"])


def test_non_admin_cannot_open_admin_lists(client):
    setup_admin(client)
    user_token = register_user(client, "list-user@example.com")

    response = client.get("/admin/lists", headers=auth(user_token))

    assert response.status_code == 403


def test_archive_list_hides_it_from_sync(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "archive me"}, headers=auth(admin_token)).json()["id"]

    response = client.post(f"/admin/lists/{list_id}/archive", headers=auth(admin_token))
    sync = client.get("/sync", headers=auth(admin_token)).json()

    assert response.status_code == 200
    assert sync["lists"] == []


def test_restore_list_returns_it_to_sync(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "restore me"}, headers=auth(admin_token)).json()["id"]

    client.post(f"/admin/lists/{list_id}/archive", headers=auth(admin_token))
    response = client.post(f"/admin/lists/{list_id}/restore", headers=auth(admin_token))
    sync = client.get("/sync", headers=auth(admin_token)).json()

    assert response.status_code == 200
    assert [item["name"] for item in sync["lists"]] == ["restore me"]


def test_admin_can_open_admin_invites(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "invite list"}, headers=auth(admin_token)).json()["id"]
    client.post(f"/lists/{list_id}/invite", headers=auth(admin_token))

    response = client.get("/admin/invites", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["invites"][0]["list_name"] == "invite list"


def test_admin_can_revoke_invite_and_revoked_invite_cannot_be_accepted(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "revoked"}, headers=auth(admin_token)).json()["id"]
    invite = client.post(f"/lists/{list_id}/invite", headers=auth(admin_token)).json()
    admin_invites = client.get("/admin/invites", headers=auth(admin_token)).json()["invites"]
    invite_id = admin_invites[0]["id"]
    user_token = register_user(client, "revoked-user@example.com")

    revoke = client.post(f"/admin/invites/{invite_id}/revoke", headers=auth(admin_token))
    accept = client.post(f"/invites/{invite['token']}/accept", headers=auth(user_token))

    assert revoke.status_code == 200
    assert accept.status_code == 404


def test_admin_invites_do_not_expose_raw_token(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "masked"}, headers=auth(admin_token)).json()["id"]
    invite = client.post(f"/lists/{list_id}/invite", headers=auth(admin_token)).json()

    response = client.get("/admin/invites", headers=auth(admin_token))

    assert response.status_code == 200
    assert invite["token"] not in response.text
    assert response.json()["invites"][0]["token_preview"].startswith("...")


def test_health_live_returns_200(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_returns_200_when_db_is_available(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_health_db_does_not_expose_database_url(client):
    response = client.get("/health/db")

    assert response.status_code == 200
    assert "sqlite" not in response.text.lower()
    assert "database_url" not in response.text.lower()


def test_metrics_contains_counts_and_no_email(client):
    setup_admin(client)
    register_user(client, "metrics@example.com")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["version"] == "1.4.0"
    assert "users_total" in response.json()
    assert "metrics@example.com" not in response.text


def test_backup_default_does_not_contain_password_hash_or_secrets(client):
    setup_admin(client)

    backup = build_backup()
    raw = json.dumps(backup)

    assert backup["contains_auth_hashes"] is False
    assert "password_hash" not in raw
    assert "JWT_SECRET" not in raw
    assert "POSTGRES_PASSWORD" not in raw


def test_db_status_contains_current_head_and_status(client):
    status = migration_status()

    assert "current" in status
    assert "head" in status
    assert status["status"] in {"up-to-date", "pending"}


def test_admin_system_shows_migration_status(client):
    admin_token = setup_admin(client)

    response = client.get("/admin/system", headers=auth(admin_token))

    assert response.status_code == 200
    assert "migration" in response.json()
    assert "jwt_secret" not in response.text.lower()
