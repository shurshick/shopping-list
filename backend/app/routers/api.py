import secrets
from html import escape
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..models import ActivityLog, ListInvite, ListMember, ShoppingItem, ShoppingList, User
from ..rate_limit import check_rate_limit
from ..schemas import (
    ActivityResponse,
    AdminStatusResponse,
    AuthRequest,
    HealthResponse,
    InviteResponse,
    ItemCreate,
    ItemUpdate,
    ListCreate,
    ListUpdate,
    MembersResponse,
    PublicServerConfig,
    ShareRequest,
    SyncResponse,
    TokenResponse,
)
from ..security import create_access_token, get_current_user, hash_password, verify_password
from ..services.diagnostics_service import record_event
from ..services.idempotency_service import remember_client_operation, replay_client_operation
from ..services.migration_service import current_revision
from ..setup import get_server_settings


APP_VERSION = "1.4.1"

router = APIRouter()


def clean_client_header(value: str | None, max_length: int) -> str:
    if value is None:
        return ""
    return value.strip()[:max_length]


def parse_client_version_code(value: str | None) -> int | None:
    if value is None or not value.strip().isdigit():
        return None
    return int(value.strip()[:10])


def update_user_client_info(
    db: Session,
    user: User,
    client_app: str | None,
    client_version: str | None,
    client_version_code: str | None,
    client_platform: str | None,
    client_os_version: str | None,
) -> None:
    app_name = clean_client_header(client_app, 80)
    version = clean_client_header(client_version, 40)
    platform = clean_client_header(client_platform, 40)
    os_version = clean_client_header(client_os_version, 80)
    version_code = parse_client_version_code(client_version_code)
    if not any((app_name, version, platform, os_version, version_code is not None)):
        return

    user.last_client_app = app_name
    user.last_client_version = version
    user.last_client_version_code = version_code
    user.last_client_platform = platform
    user.last_client_os_version = os_version
    user.last_client_seen_at = datetime.utcnow()
    db.commit()


def render_admin_page() -> str:
    return f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Администрирование списка покупок</title>
        <style>
          :root {{
            color-scheme: light;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }}
          body {{ margin: 0; background: #f6f7f9; color: #1f2933; }}
          main {{ max-width: 960px; margin: 0 auto; padding: 32px 18px; }}
          section {{
            background: #ffffff;
            border: 1px solid #dde3ea;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 18px;
          }}
          h1 {{ margin: 0 0 8px; font-size: 30px; }}
          h2 {{ margin: 0 0 14px; font-size: 20px; }}
          p {{ margin: 0 0 18px; color: #52616f; line-height: 1.5; }}
          label {{ display: block; margin: 14px 0 6px; font-weight: 650; }}
          input {{
            box-sizing: border-box;
            width: 100%;
            min-height: 44px;
            border: 1px solid #b8c4d0;
            border-radius: 6px;
            padding: 10px 12px;
            font: inherit;
          }}
          button {{
            min-height: 44px;
            border: 0;
            border-radius: 6px;
            background: #2364aa;
            color: white;
            padding: 0 18px;
            font: inherit;
            font-weight: 700;
            cursor: pointer;
          }}
          button.secondary {{ background: #e8eef5; color: #1f2933; }}
          .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }}
          .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
          .card {{ border: 1px solid #e1e7ef; border-radius: 8px; padding: 16px; background: #fbfcfe; }}
          .label {{ color: #65758b; font-size: 13px; margin-bottom: 6px; }}
          .value {{ font-size: 24px; font-weight: 750; overflow-wrap: anywhere; }}
          .small .value {{ font-size: 16px; font-weight: 650; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
          th, td {{ border-bottom: 1px solid #e1e7ef; padding: 10px 8px; text-align: left; vertical-align: top; }}
          th {{ color: #52616f; font-size: 13px; font-weight: 750; }}
          td {{ overflow-wrap: anywhere; }}
          pre {{ background: #101828; color: #eef2f6; border-radius: 8px; padding: 16px; overflow: auto; }}
          button.danger {{ background: #b42318; }}
          button.compact {{ min-height: 36px; padding: 0 12px; font-size: 14px; }}
          .message {{
            display: none;
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 6px;
            background: #eef2f6;
            color: #1f2933;
          }}
          .message.error {{ background: #fdecec; color: #8a1f17; }}
          .message.ok {{ background: #e7f5ec; color: #14532d; }}
          .hidden {{ display: none; }}
          code {{ background: #eef2f6; padding: 2px 5px; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <main>
          <section>
            <h1>Администрирование списка покупок</h1>
            <p>Войдите под администратором, чтобы посмотреть состояние сервера, базы данных и основные счётчики.</p>
            <div id="message" class="message"></div>
            <form id="login-form">
              <label for="email">Email администратора</label>
              <input id="email" type="email" autocomplete="username" required />
              <label for="password">Пароль администратора</label>
              <input id="password" type="password" autocomplete="current-password" required />
              <div class="actions">
                <button type="submit">Войти</button>
                <button type="button" class="secondary" id="clear-token">Выйти</button>
              </div>
            </form>
          </section>

          <section id="status-section" class="hidden">
            <h2>Состояние сервера</h2>
            <div class="grid" id="status-grid"></div>
            <div class="actions">
              <button type="button" id="refresh">Обновить</button>
              <button type="button" class="secondary" id="clear-activity">Очистить историю</button>
              <a href="/docs"><button type="button" class="secondary">Открыть Swagger</button></a>
              <a href="/setup"><button type="button" class="secondary">Настройки сервера</button></a>
            </div>
          </section>

          <section id="ops-section" class="hidden">
            <h2>Администрирование</h2>
            <div class="toolbar">
              <button type="button" class="secondary" data-admin-view="users">Пользователи</button>
              <button type="button" class="secondary" data-admin-view="lists">Списки</button>
              <button type="button" class="secondary" data-admin-view="invites">Приглашения</button>
              <button type="button" class="secondary" data-admin-view="system">Система</button>
              <button type="button" class="secondary" data-admin-view="logs">Логи</button>
              <button type="button" class="secondary" data-admin-view="diagnostics">Диагностика</button>
            </div>
            <div id="ops-panel">
              <p>Выберите раздел администрирования.</p>
            </div>
          </section>
        </main>

        <script>
          const tokenKey = "shoppingListAdminToken";
          const message = document.querySelector("#message");
          const form = document.querySelector("#login-form");
          const statusSection = document.querySelector("#status-section");
          const opsSection = document.querySelector("#ops-section");
          const opsPanel = document.querySelector("#ops-panel");
          const statusGrid = document.querySelector("#status-grid");
          const refreshButton = document.querySelector("#refresh");
          const clearActivityButton = document.querySelector("#clear-activity");
          const clearTokenButton = document.querySelector("#clear-token");

          function showMessage(text, kind) {{
            message.textContent = text;
            message.className = "message " + (kind || "");
            message.style.display = text ? "block" : "none";
          }}

          function formatDate(value) {{
            if (!value) return "нет данных";
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return value;
            return date.toLocaleString("ru-RU");
          }}

          function card(label, value, small = false) {{
            return `<div class="card${{small ? " small" : ""}}"><div class="label">${{label}}</div><div class="value">${{value}}</div></div>`;
          }}

          function escapeHtml(value) {{
            return String(value ?? "")
              .replaceAll("&", "&amp;")
              .replaceAll("<", "&lt;")
              .replaceAll(">", "&gt;")
              .replaceAll('"', "&quot;")
              .replaceAll("'", "&#039;");
          }}

          async function adminFetch(path, options = {{}}) {{
            const token = localStorage.getItem(tokenKey);
            if (!token) {{
              throw new Error("Нужно войти под администратором.");
            }}
            const response = await fetch(path, {{
              ...options,
              headers: {{
                "Content-Type": "application/json",
                Authorization: `Bearer ${{token}}`,
                ...(options.headers || {{}}),
              }},
            }});
            if (!response.ok) {{
              const text = await response.text();
              throw new Error(text || `Ошибка ${{response.status}}`);
            }}
            return response.json();
          }}

          function renderJson(title, data) {{
            opsPanel.innerHTML = `<h3>${{escapeHtml(title)}}</h3><pre>${{escapeHtml(JSON.stringify(data, null, 2))}}</pre>`;
          }}

          function renderUsers(data) {{
            const rows = data.users.map((user) => `
              <tr>
                <td>${{escapeHtml(user.email)}}</td>
                <td>${{user.is_admin ? "да" : "нет"}}</td>
                <td>${{user.is_active ? "активен" : "отключен"}}</td>
                <td>${{escapeHtml(formatDate(user.created_at))}}</td>
                <td>${{escapeHtml(formatDate(user.last_login_at))}}</td>
                <td>${{escapeHtml([user.last_client_app, user.last_client_version, user.last_client_version_code].filter(Boolean).join(" ")) || "—"}}</td>
                <td>${{escapeHtml(user.last_client_platform || "")}}{{user.last_client_os_version ? " " + escapeHtml(user.last_client_os_version) : ""}}</td>
                <td>${{escapeHtml(formatDate(user.last_client_seen_at))}}</td>
                <td>${{user.lists_count}}</td>
                <td>
                  <button class="compact secondary" data-user-action="${{user.is_active ? "disable" : "enable"}}" data-user-id="${{user.id}}">
                    ${{user.is_active ? "Отключить" : "Включить"}}
                  </button>
                  <button class="compact secondary" data-user-action="set-password" data-user-id="${{user.id}}">Пароль</button>
                </td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Пользователи</h3>
              <table>
                <thead><tr><th>Email</th><th>Admin</th><th>Статус</th><th>Создан</th><th>Последний вход</th><th>Версия приложения</th><th>Платформа</th><th>Последний запуск</th><th>Списков</th><th>Действия</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="10">Пользователей нет.</td></tr>'}}</tbody>
              </table>`;
          }}

          function renderLists(data) {{
            const rows = data.lists.map((item) => `
              <tr>
                <td>${{escapeHtml(item.name)}}</td>
                <td>${{escapeHtml(item.owner_email || item.owner_id)}}</td>
                <td>${{item.items_count}}</td>
                <td>${{item.members_count}}</td>
                <td>${{item.is_archived ? "архив" : "активен"}}</td>
                <td>${{escapeHtml(formatDate(item.updated_at))}}</td>
                <td>
                  <button class="compact secondary" data-list-action="details" data-list-id="${{item.id}}">Детали</button>
                  <button class="compact secondary" data-list-action="${{item.is_archived ? "restore" : "archive"}}" data-list-id="${{item.id}}">
                    ${{item.is_archived ? "Восстановить" : "Архивировать"}}
                  </button>
                </td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Списки</h3>
              <table>
                <thead><tr><th>Название</th><th>Владелец</th><th>Товаров</th><th>Участников</th><th>Статус</th><th>Обновлен</th><th>Действия</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="7">Списков нет.</td></tr>'}}</tbody>
              </table>`;
          }}

          function renderInvites(data) {{
            const rows = data.invites.map((invite) => `
              <tr>
                <td>${{escapeHtml(invite.list_name || invite.list_id)}}</td>
                <td>${{escapeHtml(invite.created_by || "")}}</td>
                <td>${{escapeHtml(invite.token_preview)}}</td>
                <td>${{escapeHtml(formatDate(invite.expires_at))}}</td>
                <td>${{escapeHtml(formatDate(invite.used_at))}}</td>
                <td>${{escapeHtml(formatDate(invite.revoked_at))}}</td>
                <td>
                  ${{invite.used_at || invite.revoked_at ? "" : `<button class="compact danger" data-invite-action="revoke" data-invite-id="${{invite.id}}">Отозвать</button>`}}
                </td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Приглашения</h3>
              <table>
                <thead><tr><th>Список</th><th>Создал</th><th>Token</th><th>Истекает</th><th>Использовано</th><th>Отозвано</th><th>Действия</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="7">Приглашений нет.</td></tr>'}}</tbody>
              </table>`;
          }}

          async function loadAdminView(view) {{
            try {{
              opsPanel.innerHTML = "<p>Загрузка...</p>";
              if (view === "users") renderUsers(await adminFetch("/admin/users"));
              if (view === "lists") renderLists(await adminFetch("/admin/lists"));
              if (view === "invites") renderInvites(await adminFetch("/admin/invites"));
              if (view === "system") renderJson("Система", await adminFetch("/admin/system"));
              if (view === "logs") renderJson("Логи", await adminFetch("/admin/logs"));
              if (view === "diagnostics") renderJson("Диагностика", await adminFetch("/admin/diagnostics"));
            }} catch (error) {{
              showMessage(error.message, "error");
              opsPanel.innerHTML = "<p>Не удалось загрузить раздел.</p>";
            }}
          }}

          function renderStatus(data) {{
            statusGrid.innerHTML = [
              card("Версия API", data.version, true),
              card("База данных", data.database === "ok" ? "доступна" : data.database, true),
              card("Миграция", data.migration || "нет данных", true),
              card("Время сервера", formatDate(data.server_time), true),
              card("Пользователи", data.users_count),
              card("Списки", data.lists_count),
              card("Товары", data.items_count),
              card("Куплено", data.checked_items_count),
              card("События истории", data.activity_events_count),
              card("Активные приглашения", data.invites_active_count),
              card("Ожидающие приглашения", data.pending_invites_count),
              card("Срок приглашения", `${{data.invite_token_hours}} ч.`, true),
              card("Название приложения", data.app_name, true),
              card("Внешний адрес", data.external_url || "не задан", true),
              card("Регистрация", data.allow_registration ? "разрешена" : "отключена", true),
              card("Первичная настройка", data.setup_completed ? "завершена" : "не завершена", true),
            ].join("");
            statusSection.classList.remove("hidden");
          }}

          async function loadStatus() {{
            const token = localStorage.getItem(tokenKey);
            if (!token) {{
              statusSection.classList.add("hidden");
              opsSection.classList.add("hidden");
              return;
            }}
            const response = await fetch("/admin/status", {{
              headers: {{ Authorization: `Bearer ${{token}}` }},
            }});
            if (response.status === 401 || response.status === 403) {{
              localStorage.removeItem(tokenKey);
              statusSection.classList.add("hidden");
              opsSection.classList.add("hidden");
              showMessage("Нужно войти под администратором.", "error");
              return;
            }}
            if (!response.ok) {{
              showMessage("Не удалось получить статус сервера.", "error");
              return;
            }}
            renderStatus(await response.json());
            opsSection.classList.remove("hidden");
            showMessage("Статус обновлён.", "ok");
          }}

          form.addEventListener("submit", async (event) => {{
            event.preventDefault();
            showMessage("Выполняется вход...", "");
            const response = await fetch("/auth/login", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{
                email: document.querySelector("#email").value,
                password: document.querySelector("#password").value,
              }}),
            }});
            if (!response.ok) {{
              showMessage("Неверный email или пароль.", "error");
              return;
            }}
            const data = await response.json();
            localStorage.setItem(tokenKey, data.access_token);
            await loadStatus();
          }});

          refreshButton.addEventListener("click", loadStatus);
          document.querySelectorAll("[data-admin-view]").forEach((button) => {{
            button.addEventListener("click", () => loadAdminView(button.dataset.adminView));
          }});
          opsPanel.addEventListener("click", async (event) => {{
            const button = event.target.closest("button");
            if (!button) return;
            try {{
              if (button.dataset.userAction === "disable") {{
                if (!confirm("Отключить пользователя?")) return;
                await adminFetch(`/admin/users/${{button.dataset.userId}}/disable`, {{ method: "POST" }});
                await loadAdminView("users");
              }}
              if (button.dataset.userAction === "enable") {{
                await adminFetch(`/admin/users/${{button.dataset.userId}}/enable`, {{ method: "POST" }});
                await loadAdminView("users");
              }}
              if (button.dataset.userAction === "set-password") {{
                const password = prompt("Новый пароль пользователя, минимум 8 символов");
                if (!password) return;
                await adminFetch(`/admin/users/${{button.dataset.userId}}/set-password`, {{
                  method: "POST",
                  body: JSON.stringify({{ password }}),
                }});
                showMessage("Пароль обновлен.", "ok");
              }}
              if (button.dataset.listAction === "details") {{
                renderJson("Детали списка", await adminFetch(`/admin/lists/${{button.dataset.listId}}`));
              }}
              if (button.dataset.listAction === "archive") {{
                if (!confirm("Архивировать список? Обычные пользователи перестанут видеть его в синхронизации.")) return;
                await adminFetch(`/admin/lists/${{button.dataset.listId}}/archive`, {{ method: "POST" }});
                await loadAdminView("lists");
              }}
              if (button.dataset.listAction === "restore") {{
                await adminFetch(`/admin/lists/${{button.dataset.listId}}/restore`, {{ method: "POST" }});
                await loadAdminView("lists");
              }}
              if (button.dataset.inviteAction === "revoke") {{
                if (!confirm("Отозвать приглашение?")) return;
                await adminFetch(`/admin/invites/${{button.dataset.inviteId}}/revoke`, {{ method: "POST" }});
                await loadAdminView("invites");
              }}
              await loadStatus();
            }} catch (error) {{
              showMessage(error.message, "error");
            }}
          }});
          clearActivityButton.addEventListener("click", async () => {{
            const token = localStorage.getItem(tokenKey);
            if (!token) {{
              showMessage("Нужно войти под администратором.", "error");
              return;
            }}
            if (!confirm("Очистить всю историю действий? Списки и товары останутся без изменений.")) {{
              return;
            }}
            const response = await fetch("/admin/activity", {{
              method: "DELETE",
              headers: {{ Authorization: `Bearer ${{token}}` }},
            }});
            if (!response.ok) {{
              showMessage("Не удалось очистить историю.", "error");
              return;
            }}
            const data = await response.json();
            showMessage(`История очищена. Удалено событий: ${{data.deleted}}.`, "ok");
            await loadStatus();
          }});
          clearTokenButton.addEventListener("click", () => {{
            localStorage.removeItem(tokenKey);
            statusSection.classList.add("hidden");
            opsSection.classList.add("hidden");
            showMessage("Вы вышли из админ-панели.", "ok");
          }});

          loadStatus();
        </script>
      </body>
    </html>
    """


def sort_items_for_display(items: list[ShoppingItem]) -> list[ShoppingItem]:
    def item_timestamp(item: ShoppingItem) -> float:
        return item.updated_at.timestamp() if item.updated_at is not None else 0

    return sorted(
        items,
        key=lambda item: (
            item.is_checked,
            item_timestamp(item) if item.is_checked else -item_timestamp(item),
            item.id,
        ),
    )


def require_list_access(db: Session, user: User, list_id: int) -> ShoppingList:
    shopping_list = db.scalar(
        select(ShoppingList)
        .join(ListMember, ListMember.list_id == ShoppingList.id)
        .where(ShoppingList.id == list_id, ListMember.user_id == user.id, ShoppingList.archived_at.is_(None))
    )
    if shopping_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список не найден")
    return shopping_list


def require_list_owner(db: Session, user: User, list_id: int) -> ShoppingList:
    shopping_list = db.scalar(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == user.id,
            ShoppingList.archived_at.is_(None),
        )
    )
    if shopping_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список не найден")
    return shopping_list


def add_member_if_missing(db: Session, list_id: int, user_id: int) -> None:
    exists = db.scalar(select(ListMember.id).where(ListMember.list_id == list_id, ListMember.user_id == user_id))
    if exists is None:
        db.add(ListMember(list_id=list_id, user_id=user_id))


def invite_is_expired(invite: ListInvite) -> bool:
    return invite.expires_at is not None and invite.expires_at < datetime.utcnow()


def current_migration() -> str | None:
    return current_revision()


def require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступно только администратору")


def write_activity(
    db: Session,
    user: User,
    action: str,
    list_id: int | None = None,
    item_id: int | None = None,
    item_name: str = "",
    details: str = "",
) -> None:
    db.add(
        ActivityLog(
            list_id=list_id,
            user_id=user.id,
            action=action,
            item_id=item_id,
            item_name=item_name[:180],
            details=details[:255],
        )
    )


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "version": APP_VERSION,
        "database": "ok",
        "migration": current_migration(),
        "server_time": datetime.utcnow(),
    }


@router.get("/admin", response_class=HTMLResponse)
def admin_page():
    return HTMLResponse(render_admin_page())


@router.get("/admin/status", response_model=AdminStatusResponse)
def admin_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    server_settings = get_server_settings(db)
    now = datetime.utcnow()
    return {
        "version": APP_VERSION,
        "database": "ok",
        "migration": current_migration(),
        "server_time": now,
        "users_count": db.scalar(select(func.count(User.id))) or 0,
        "lists_count": db.scalar(select(func.count(ShoppingList.id))) or 0,
        "items_count": db.scalar(select(func.count(ShoppingItem.id))) or 0,
        "checked_items_count": db.scalar(select(func.count(ShoppingItem.id)).where(ShoppingItem.is_checked.is_(True))) or 0,
        "activity_events_count": db.scalar(select(func.count(ActivityLog.id))) or 0,
        "invites_active_count": db.scalar(
            select(func.count(ListInvite.id)).where(
                ListInvite.used_at.is_(None),
                ListInvite.revoked_at.is_(None),
                (ListInvite.expires_at.is_(None)) | (ListInvite.expires_at >= now),
            )
        ) or 0,
        "pending_invites_count": db.scalar(
            select(func.count(ListInvite.id)).where(ListInvite.used_at.is_(None), ListInvite.revoked_at.is_(None))
        ) or 0,
        "invite_token_hours": settings.invite_token_hours,
        "app_name": server_settings.app_name,
        "external_url": server_settings.external_url,
        "allow_registration": server_settings.allow_registration,
        "setup_completed": server_settings.setup_completed,
    }


@router.delete("/admin/activity")
def clear_activity(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    result = db.execute(delete(ActivityLog))
    db.commit()
    return {"deleted": result.rowcount or 0}


@router.get("/server-config", response_model=PublicServerConfig)
def server_config(db: Session = Depends(get_db)):
    return get_server_settings(db)


@router.post("/auth/register", response_model=TokenResponse)
def register(payload: AuthRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "register", payload.email, limit=8, window_seconds=60)
    server_settings = get_server_settings(db)
    if not server_settings.setup_completed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Первичная настройка сервера не завершена")
    if not server_settings.allow_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Регистрация отключена")

    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Этот email уже зарегистрирован")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: AuthRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request, "login", payload.email, limit=10, window_seconds=60)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        record_event("login failed", payload.email, "warning")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if not user.is_active:
        record_event("login disabled user", payload.email, "warning")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Учетная запись отключена")
    user.last_login_at = datetime.utcnow()
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/sync", response_model=SyncResponse)
def sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_client_app: str | None = Header(default=None),
    x_client_version: str | None = Header(default=None),
    x_client_version_code: str | None = Header(default=None),
    x_client_platform: str | None = Header(default=None),
    x_client_os_version: str | None = Header(default=None),
):
    update_user_client_info(
        db,
        current_user,
        x_client_app,
        x_client_version,
        x_client_version_code,
        x_client_platform,
        x_client_os_version,
    )
    lists = db.scalars(
        select(ShoppingList)
        .join(ListMember, ListMember.list_id == ShoppingList.id)
        .where(ListMember.user_id == current_user.id, ShoppingList.archived_at.is_(None))
        .options(selectinload(ShoppingList.items))
        .order_by(ShoppingList.updated_at.desc())
    ).all()
    for shopping_list in lists:
        shopping_list.items = sort_items_for_display(shopping_list.items)
    return {"lists": lists}


@router.post("/lists")
def create_list(
    payload: ListCreate,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client_operation_id = payload.client_operation_id or x_client_operation_id
    replayed = replay_client_operation(db, current_user, client_operation_id)
    if replayed is not None:
        return replayed
    shopping_list = ShoppingList(name=payload.name, owner_id=current_user.id)
    db.add(shopping_list)
    db.flush()
    db.add(ListMember(list_id=shopping_list.id, user_id=current_user.id))
    write_activity(db, current_user, "list_created", list_id=shopping_list.id, details=shopping_list.name)
    response = {"id": shopping_list.id, "name": shopping_list.name}
    remember_client_operation(
        db,
        current_user,
        client_operation_id,
        "create_list",
        response,
        temp_id=payload.temp_id,
        resource_id=shopping_list.id,
    )
    db.commit()
    return response


@router.patch("/lists/{list_id}")
def update_list(
    list_id: int,
    payload: ListUpdate,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    shopping_list = require_list_owner(db, current_user, list_id)
    old_name = shopping_list.name
    shopping_list.name = payload.name
    write_activity(db, current_user, "list_renamed", list_id=shopping_list.id, details=f"{old_name} -> {payload.name}")
    response = {"id": shopping_list.id, "name": shopping_list.name}
    remember_client_operation(db, current_user, x_client_operation_id, "rename_list", response, resource_id=shopping_list.id)
    db.commit()
    return response


@router.delete("/lists/{list_id}")
def delete_list(
    list_id: int,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    shopping_list = require_list_access(db, current_user, list_id)
    if shopping_list.owner_id == current_user.id:
        write_activity(db, current_user, "list_deleted", list_id=shopping_list.id, details=shopping_list.name)
        db.delete(shopping_list)
    else:
        membership = db.scalar(
            select(ListMember).where(ListMember.list_id == shopping_list.id, ListMember.user_id == current_user.id)
        )
        if membership is not None:
            write_activity(db, current_user, "list_left", list_id=shopping_list.id, details=shopping_list.name)
            db.delete(membership)
    response = {"status": "deleted"}
    remember_client_operation(db, current_user, x_client_operation_id, "delete_list", response, resource_id=list_id)
    db.commit()
    return response


@router.delete("/lists/{list_id}/items")
def clear_list(
    list_id: int,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    shopping_list = require_list_access(db, current_user, list_id)
    items = db.scalars(select(ShoppingItem).where(ShoppingItem.list_id == shopping_list.id)).all()
    for item in items:
        db.delete(item)
    write_activity(db, current_user, "list_cleared", list_id=shopping_list.id, details=f"Удалено позиций: {len(items)}")
    response = {"status": "cleared"}
    remember_client_operation(db, current_user, x_client_operation_id, "clear_list", response, resource_id=list_id)
    db.commit()
    return response


@router.delete("/lists/{list_id}/items/checked")
def clear_checked_items(
    list_id: int,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    shopping_list = require_list_access(db, current_user, list_id)
    items = db.scalars(
        select(ShoppingItem).where(ShoppingItem.list_id == shopping_list.id, ShoppingItem.is_checked.is_(True))
    ).all()
    for item in items:
        db.delete(item)
    write_activity(db, current_user, "checked_items_cleared", list_id=shopping_list.id, details=f"Удалено позиций: {len(items)}")
    response = {"status": "cleared"}
    remember_client_operation(db, current_user, x_client_operation_id, "clear_checked", response, resource_id=list_id)
    db.commit()
    return response


@router.patch("/lists/{list_id}/items/checked")
def restore_checked_items(
    list_id: int,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    shopping_list = require_list_access(db, current_user, list_id)
    items = db.scalars(
        select(ShoppingItem).where(ShoppingItem.list_id == shopping_list.id, ShoppingItem.is_checked.is_(True))
    ).all()
    for item in items:
        item.is_checked = False
    write_activity(db, current_user, "checked_items_restored", list_id=shopping_list.id, details=f"Возвращено позиций: {len(items)}")
    response = {"status": "restored", "count": len(items)}
    remember_client_operation(db, current_user, x_client_operation_id, "restore_checked", response, resource_id=list_id)
    db.commit()
    return response


@router.post("/lists/{list_id}/copy")
def copy_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    source = require_list_access(db, current_user, list_id)
    source_items = db.scalars(select(ShoppingItem).where(ShoppingItem.list_id == source.id)).all()
    copied = ShoppingList(name=f"{source.name} копия", owner_id=current_user.id)
    db.add(copied)
    db.flush()
    db.add(ListMember(list_id=copied.id, user_id=current_user.id))
    for item in source_items:
        db.add(
            ShoppingItem(
                list_id=copied.id,
                name=item.name,
                quantity=item.quantity,
                is_checked=False,
            )
        )
    write_activity(db, current_user, "list_copied", list_id=copied.id, details=f"Источник: {source.name}")
    db.commit()
    return {"id": copied.id, "name": copied.name}


@router.get("/lists/{list_id}/members", response_model=MembersResponse)
def list_members(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    rows = db.execute(
        select(User.id, User.email)
        .join(ListMember, ListMember.user_id == User.id)
        .where(ListMember.list_id == shopping_list.id)
        .order_by(User.email)
    ).all()
    return {
        "members": [
            {"id": user_id, "email": email, "is_owner": user_id == shopping_list.owner_id}
            for user_id, email in rows
        ]
    }


@router.get("/lists/{list_id}/activity", response_model=ActivityResponse)
def list_activity(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    rows = db.execute(
        select(ActivityLog, User.email)
        .outerjoin(User, User.id == ActivityLog.user_id)
        .where(ActivityLog.list_id == shopping_list.id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(100)
    ).all()
    return {
        "events": [
            {
                "id": event.id,
                "list_id": event.list_id,
                "user_id": event.user_id,
                "user_email": email,
                "action": event.action,
                "item_id": event.item_id,
                "item_name": event.item_name,
                "details": event.details,
                "created_at": event.created_at,
            }
            for event, email in rows
        ]
    }


@router.delete("/lists/{list_id}/activity")
def clear_list_activity(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    result = db.execute(delete(ActivityLog).where(ActivityLog.list_id == shopping_list.id))
    db.commit()
    return {"deleted": result.rowcount or 0}


@router.post("/lists/{list_id}/share")
def share_list(
    list_id: int,
    payload: ShareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shopping_list = require_list_access(db, current_user, list_id)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    add_member_if_missing(db, shopping_list.id, user.id)
    write_activity(db, current_user, "list_shared", list_id=shopping_list.id, details=user.email)
    db.commit()
    return {"status": "shared"}


@router.post("/lists/{list_id}/invite", response_model=InviteResponse)
def create_invite(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    invite = ListInvite(
        token=secrets.token_urlsafe(24),
        list_id=shopping_list.id,
        created_by_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=settings.invite_token_hours),
    )
    db.add(invite)
    write_activity(db, current_user, "invite_created", list_id=shopping_list.id, details=f"До {invite.expires_at.isoformat()}")
    db.commit()
    db.refresh(invite)

    external_url = get_server_settings(db).external_url.rstrip("/")
    web_url = f"{external_url}/join/{invite.token}" if external_url else f"/join/{invite.token}"
    return {"token": invite.token, "url": web_url, "app_url": f"shoppinglist://join/{invite.token}", "expires_at": invite.expires_at}


@router.post("/invites/{token}/accept")
def accept_invite(token: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invite = db.scalar(select(ListInvite).where(ListInvite.token == token).with_for_update())
    if invite is None or invite.used_at is not None or invite.revoked_at is not None or invite_is_expired(invite):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
    add_member_if_missing(db, invite.list_id, current_user.id)
    invite.used_at = datetime.utcnow()
    write_activity(db, current_user, "invite_accepted", list_id=invite.list_id)
    db.commit()
    return {"status": "joined", "list_id": invite.list_id}


@router.get("/join/{token}", response_class=HTMLResponse)
def join_page(token: str, db: Session = Depends(get_db)):
    invite = db.scalar(select(ListInvite).where(ListInvite.token == token))
    if invite is None or invite.used_at is not None or invite.revoked_at is not None or invite_is_expired(invite):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
    shopping_list = db.get(ShoppingList, invite.list_id)
    app_url = f"shoppinglist://join/{escape(token)}"
    list_name = escape(shopping_list.name if shopping_list else "списку покупок")
    return f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Приглашение в список покупок</title>
        <script>
          window.addEventListener("load", function () {{
            window.location.href = "{app_url}";
          }});
        </script>
        <style>
          body {{ font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #1f2933; }}
          main {{ max-width: 560px; margin: 0 auto; padding: 32px 18px; }}
          section {{ background: white; border: 1px solid #dde3ea; border-radius: 8px; padding: 24px; }}
          a {{ display: inline-block; margin-top: 16px; padding: 12px 16px; border-radius: 6px; background: #2364aa; color: white; text-decoration: none; font-weight: 700; }}
        </style>
      </head>
      <body>
        <main>
          <section>
            <h1>Доступ к списку</h1>
            <p>Вам открыли доступ к списку «{list_name}».</p>
            <a href="{app_url}">Открыть в приложении</a>
          </section>
        </main>
      </body>
    </html>
    """


@router.post("/lists/{list_id}/items")
def create_item(
    list_id: int,
    payload: ItemCreate,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client_operation_id = payload.client_operation_id or x_client_operation_id
    replayed = replay_client_operation(db, current_user, client_operation_id)
    if replayed is not None:
        return replayed
    require_list_access(db, current_user, list_id)
    item = ShoppingItem(list_id=list_id, name=payload.name, quantity=payload.quantity, is_checked=payload.is_checked)
    db.add(item)
    db.flush()
    db.refresh(item)
    write_activity(db, current_user, "item_created", list_id=list_id, item_id=item.id, item_name=item.name, details=item.quantity)
    response = {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity,
        "is_checked": item.is_checked,
        "updated_at": item.updated_at,
    }
    remember_client_operation(
        db,
        current_user,
        client_operation_id,
        "create_item",
        response,
        temp_id=payload.temp_id,
        resource_id=item.id,
    )
    db.commit()
    return response


@router.patch("/items/{item_id}")
def update_item(
    item_id: int,
    payload: ItemUpdate,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    item = db.scalar(select(ShoppingItem).where(ShoppingItem.id == item_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    require_list_access(db, current_user, item.list_id)
    update = payload.model_dump(exclude_unset=True)
    old_checked = item.is_checked
    old_name = item.name
    for key, value in update.items():
        setattr(item, key, value)
    if "is_checked" in update and update["is_checked"] != old_checked:
        action = "item_checked" if update["is_checked"] else "item_unchecked"
    elif "name" in update or "quantity" in update:
        action = "item_updated"
    else:
        action = "item_updated"
    details = f"{old_name} -> {item.name}" if old_name != item.name else item.quantity
    write_activity(db, current_user, action, list_id=item.list_id, item_id=item.id, item_name=item.name, details=details)
    db.flush()
    db.refresh(item)
    response = {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity,
        "is_checked": item.is_checked,
        "updated_at": item.updated_at,
    }
    remember_client_operation(db, current_user, x_client_operation_id, "update_item", response, resource_id=item.id)
    db.commit()
    db.refresh(item)
    return response


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    x_client_operation_id: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    replayed = replay_client_operation(db, current_user, x_client_operation_id)
    if replayed is not None:
        return replayed
    item = db.scalar(select(ShoppingItem).where(ShoppingItem.id == item_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    require_list_access(db, current_user, item.list_id)
    write_activity(db, current_user, "item_deleted", list_id=item.list_id, item_id=item.id, item_name=item.name, details=item.quantity)
    db.delete(item)
    response = {"status": "deleted"}
    remember_client_operation(db, current_user, x_client_operation_id, "delete_item", response, resource_id=item_id)
    db.commit()
    return response
