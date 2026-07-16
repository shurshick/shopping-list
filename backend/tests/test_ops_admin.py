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


def test_admin_users_support_search_filters_and_sort(client):
    admin_token = setup_admin(client)
    register_user(client, "active-filter@example.com")
    register_user(client, "disabled-filter@example.com")
    users = client.get("/admin/users", headers=auth(admin_token)).json()["users"]
    disabled_id = next(user["id"] for user in users if user["email"] == "disabled-filter@example.com")
    client.post(f"/admin/users/{disabled_id}/disable", headers=auth(admin_token))

    active = client.get(
        "/admin/users?status=active&query=active-filter&sort=email",
        headers=auth(admin_token),
    )
    disabled = client.get("/admin/users?status=disabled", headers=auth(admin_token))
    admins = client.get("/admin/users?status=admins", headers=auth(admin_token))

    assert active.status_code == 200
    assert [user["email"] for user in active.json()["users"]] == ["active-filter@example.com"]
    assert any(user["email"] == "disabled-filter@example.com" for user in disabled.json()["users"])
    assert all(user["is_admin"] for user in admins.json()["users"])


def test_sync_records_client_version_for_admin_users(client):
    admin_token = setup_admin(client)

    sync_response = client.get(
        "/sync",
        headers={
            **auth(admin_token),
            "X-Client-App": "shopping-list-android",
            "X-Client-Version": "1.4.7",
            "X-Client-Version-Code": "30",
            "X-Client-Platform": "android",
            "X-Client-Os-Version": "14",
        },
    )
    users_response = client.get("/admin/users", headers=auth(admin_token))
    user = next(item for item in users_response.json()["users"] if item["email"] == "admin@example.com")

    assert sync_response.status_code == 200
    assert user["last_client_app"] == "shopping-list-android"
    assert user["last_client_version"] == "1.4.7"
    assert user["last_client_version_code"] == 30
    assert user["last_client_platform"] == "android"
    assert user["last_client_os_version"] == "14"
    assert user["last_client_seen_at"] is not None


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


def test_admin_set_password_requires_body_not_query_string(client):
    admin_token = setup_admin(client)
    register_user(client, "query-password@example.com", "oldpass123")
    users = client.get("/admin/users", headers=auth(admin_token)).json()["users"]
    user_id = next(user["id"] for user in users if user["email"] == "query-password@example.com")

    response = client.post(
        f"/admin/users/{user_id}/set-password?password=querypass123",
        headers=auth(admin_token),
    )

    assert response.status_code == 422


def test_admin_can_open_admin_lists(client):
    admin_token = setup_admin(client)
    client.post("/lists", json={"name": "ops list"}, headers=auth(admin_token))

    response = client.get("/admin/lists", headers=auth(admin_token))

    assert response.status_code == 200
    assert any(item["name"] == "ops list" for item in response.json()["lists"])


def test_admin_lists_support_search_and_archive_filter(client):
    admin_token = setup_admin(client)
    active_id = client.post("/lists", json={"name": "active admin list"}, headers=auth(admin_token)).json()["id"]
    archived_id = client.post("/lists", json={"name": "archived admin list"}, headers=auth(admin_token)).json()["id"]
    client.post(f"/admin/lists/{archived_id}/archive", headers=auth(admin_token))

    active = client.get("/admin/lists?status=active&query=active admin", headers=auth(admin_token))
    archived = client.get("/admin/lists?status=archived&query=archived admin", headers=auth(admin_token))

    assert [item["id"] for item in active.json()["lists"]] == [active_id]
    assert [item["id"] for item in archived.json()["lists"]] == [archived_id]


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


def test_admin_invites_support_active_and_revoked_filters(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "filter invites"}, headers=auth(admin_token)).json()["id"]
    client.post(f"/lists/{list_id}/invite", headers=auth(admin_token))
    invite_id = client.get("/admin/invites?status=active&query=filter", headers=auth(admin_token)).json()["invites"][0]["id"]

    client.post(f"/admin/invites/{invite_id}/revoke", headers=auth(admin_token))
    active = client.get("/admin/invites?status=active&query=filter", headers=auth(admin_token))
    revoked = client.get("/admin/invites?status=revoked&query=filter", headers=auth(admin_token))

    assert active.json()["invites"] == []
    assert revoked.json()["invites"][0]["id"] == invite_id


def test_admin_invites_do_not_expose_raw_token(client):
    admin_token = setup_admin(client)
    list_id = client.post("/lists", json={"name": "masked"}, headers=auth(admin_token)).json()["id"]
    invite = client.post(f"/lists/{list_id}/invite", headers=auth(admin_token)).json()

    response = client.get("/admin/invites", headers=auth(admin_token))

    assert response.status_code == 200
    assert invite["token"] not in response.text
    assert response.json()["invites"][0]["token_preview"].startswith("...")


def test_admin_logs_filter_and_do_not_expose_sensitive_headers(client):
    admin_token = setup_admin(client)

    response = client.get("/admin/logs?level=info&event_type=start", headers=auth(admin_token))

    assert response.status_code == 200
    assert "authorization" not in response.text.lower()
    assert "password" not in response.text.lower()
    assert "jwt_secret" not in response.text.lower()


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
    assert response.json()["version"] == "1.5.3"
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


def test_admin_diagnostics_does_not_expose_secrets(client):
    admin_token = setup_admin(client)

    response = client.get("/admin/diagnostics", headers=auth(admin_token))

    assert response.status_code == 200
    lowered = response.text.lower()
    assert "jwt_secret" not in lowered
    assert "postgres_password" not in lowered
    assert "password_hash" not in lowered


def test_admin_page_links_new_ops_sections(client):
    response = client.get("/admin")

    assert response.status_code == 200
    assert 'data-admin-view="home"' in response.text
    assert 'class="toolbar admin-nav"' in response.text
    assert "Поиск по email" in response.text
    assert 'data-admin-view="users"' in response.text
    assert 'data-admin-view="lists"' in response.text
    assert 'data-admin-view="invites"' in response.text
    assert 'data-admin-view="system"' in response.text
    assert 'data-admin-view="logs"' in response.text
    assert 'data-admin-view="diagnostics"' in response.text
    assert "color-scheme: dark" in response.text
    assert 'data-label="Email"' in response.text
    assert "escapeHtml(value)" in response.text


def test_admin_page_does_not_break_script_with_embedded_script_tags(client):
    response = client.get("/admin")

    assert response.status_code == 200
    assert '<script type="application/json"' not in response.text
    assert response.text.count("</script>") == 1
