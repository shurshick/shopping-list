import secrets
from html import escape
from datetime import timedelta

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
from ..time_utils import utc_now


APP_VERSION = "1.5.3"

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
    user.last_client_seen_at = utc_now()
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
            color-scheme: dark;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            --background: #111014;
            --surface: #1c1b20;
            --surface-high: #27242c;
            --surface-highest: #322f37;
            --outline: #49454f;
            --text: #e8e1eb;
            --muted: #cac4d0;
            --primary: #d0bcff;
            --on-primary: #381e72;
            --primary-container: #4f378b;
            --secondary: #b8ccc6;
            --success: #a8d5ba;
            --warning: #f2cb81;
            --danger: #ffb4ab;
          }}
          * {{ box-sizing: border-box; }}
          body {{ margin: 0; background: var(--background); color: var(--text); }}
          main {{ max-width: 1280px; margin: 0 auto; padding: 24px 20px 48px; }}
          section {{ margin-bottom: 28px; }}
          .login-shell {{
            max-width: 720px;
            margin: 32px auto 28px;
            padding: 28px;
            border: 1px solid var(--outline);
            border-radius: 8px;
            background: var(--surface);
          }}
          .authenticated .login-shell {{ max-width: none; margin: 0 0 24px; padding: 20px 24px; }}
          .authenticated #login-form, .authenticated .login-copy {{ display: none; }}
          #clear-token {{ display: none; }}
          .authenticated #clear-token {{ display: inline-flex; }}
          .title-row {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
          .eyebrow {{ color: var(--primary); font-size: 13px; font-weight: 750; text-transform: uppercase; }}
          .product-mark {{
            display: grid;
            place-items: center;
            width: 48px;
            height: 48px;
            border-radius: 8px;
            background: var(--primary-container);
            color: #efe7ff;
            font-size: 18px;
            font-weight: 800;
          }}
          h1 {{ margin: 4px 0 8px; font-size: 30px; letter-spacing: 0; }}
          h2 {{ margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }}
          h3 {{ margin: 0 0 14px; font-size: 20px; }}
          h4 {{ margin: 22px 0 10px; }}
          p {{ margin: 0 0 18px; color: var(--muted); line-height: 1.5; }}
          label {{ display: block; margin: 14px 0 6px; color: var(--muted); font-size: 14px; font-weight: 650; }}
          input, select {{
            width: 100%;
            min-height: 48px;
            border: 1px solid var(--outline);
            border-radius: 6px;
            padding: 10px 12px;
            background: var(--surface-high);
            color: var(--text);
            font: inherit;
            outline: none;
          }}
          input:focus, select:focus {{ border-color: var(--primary); box-shadow: 0 0 0 2px rgba(208, 188, 255, .18); }}
          input::placeholder {{ color: #938f99; }}
          button, .button-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 44px;
            border: 1px solid transparent;
            border-radius: 8px;
            background: var(--primary);
            color: var(--on-primary);
            padding: 0 18px;
            font: inherit;
            font-weight: 750;
            text-decoration: none;
            cursor: pointer;
          }}
          button:hover, .button-link:hover {{ filter: brightness(1.06); }}
          button:focus-visible, .button-link:focus-visible {{ outline: 3px solid rgba(208, 188, 255, .45); outline-offset: 2px; }}
          button.secondary, .button-link.secondary {{ background: var(--surface-high); border-color: var(--outline); color: var(--text); }}
          button.secondary.active {{ background: var(--primary-container); border-color: var(--primary); color: #f1e9ff; }}
          button.danger {{ background: #5f2523; border-color: #8c3b36; color: var(--danger); }}
          button.compact {{ min-height: 38px; padding: 0 12px; font-size: 14px; }}
          .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }}
          .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }}
          .admin-nav {{
            position: sticky;
            top: 8px;
            z-index: 2;
            display: grid;
            grid-template-columns: repeat(7, minmax(112px, 1fr));
            padding: 8px;
            margin-bottom: 20px;
            border: 1px solid var(--outline);
            border-radius: 8px;
            background: rgba(28, 27, 32, .96);
            backdrop-filter: blur(12px);
          }}
          .admin-nav button {{ min-height: 52px; padding: 0 10px; }}
          .filters {{
            display: grid;
            grid-template-columns: minmax(180px, 1fr) minmax(160px, 220px) minmax(160px, 220px) auto;
            gap: 10px;
            align-items: end;
            margin: 12px 0 16px;
            padding: 14px;
            border: 1px solid var(--outline);
            border-radius: 8px;
            background: var(--surface);
          }}
          .filters label {{ margin: 0 0 5px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }}
          .card {{
            min-height: 112px;
            border: 1px solid var(--outline);
            border-radius: 8px;
            padding: 16px;
            background: var(--surface);
          }}
          .card:nth-child(3n+2) {{ background: #192321; border-color: #334844; }}
          .label {{ color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
          .value {{ font-size: 26px; font-weight: 750; overflow-wrap: anywhere; }}
          .small .value {{ font-size: 16px; font-weight: 650; line-height: 1.4; }}
          .table-wrap {{ overflow-x: auto; border: 1px solid var(--outline); border-radius: 8px; background: var(--surface); }}
          table, .admin-table {{ width: 100%; min-width: 980px; border-collapse: collapse; margin: 0; }}
          th, td {{ border-bottom: 1px solid var(--outline); padding: 12px 10px; text-align: left; vertical-align: top; }}
          tr:last-child td {{ border-bottom: 0; }}
          tbody tr:hover {{ background: rgba(208, 188, 255, .05); }}
          th {{ color: var(--muted); font-size: 12px; font-weight: 750; text-transform: uppercase; }}
          td {{ overflow-wrap: anywhere; }}
          .admin-actions {{ display: flex; gap: 8px; align-items: center; flex-wrap: nowrap; }}
          .admin-actions button {{ white-space: nowrap; }}
          .badge {{ display: inline-flex; align-items: center; min-height: 26px; padding: 0 9px; border-radius: 999px; background: var(--surface-highest); color: var(--muted); font-weight: 700; font-size: 12px; }}
          .badge.ok {{ background: #1d3a2a; color: var(--success); }}
          .badge.warn {{ background: #453819; color: var(--warning); }}
          .badge.error {{ background: #4b2524; color: var(--danger); }}
          pre {{ background: #0b0b0e; color: #e3dde7; border: 1px solid var(--outline); border-radius: 8px; padding: 16px; overflow: auto; }}
          .message {{ display: none; margin-bottom: 16px; padding: 12px 14px; border: 1px solid var(--outline); border-radius: 8px; background: var(--surface-high); color: var(--text); }}
          .message.error {{ background: #4b2524; border-color: #8c3b36; color: var(--danger); }}
          .message.ok {{ background: #1d3a2a; border-color: #37664a; color: var(--success); }}
          .hidden {{ display: none; }}
          code {{ background: var(--surface-highest); padding: 2px 5px; border-radius: 4px; }}
          @media (max-width: 900px) {{
            .admin-nav {{ grid-template-columns: repeat(4, minmax(120px, 1fr)); }}
            .filters {{ grid-template-columns: 1fr 1fr; }}
          }}
          @media (max-width: 720px) {{
            main {{ padding: 12px 12px 32px; }}
            .login-shell, .authenticated .login-shell {{ margin: 0 0 20px; padding: 18px; }}
            h1 {{ font-size: 24px; }}
            h2 {{ font-size: 20px; }}
            .product-mark {{ width: 42px; height: 42px; }}
            .admin-nav {{ position: static; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .filters {{ grid-template-columns: 1fr; padding: 12px; }}
            .filters > div:empty {{ display: none; }}
            .actions > button, .actions > .button-link {{ flex: 1 1 150px; }}
            .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .card {{ min-height: 104px; padding: 14px; }}
            .value {{ font-size: 22px; }}
            .table-wrap {{ overflow: visible; border: 0; background: transparent; }}
            .admin-table {{ min-width: 0; }}
            .admin-table thead {{ display: none; }}
            .admin-table tbody, .admin-table tr, .admin-table td {{ display: block; width: 100%; }}
            .admin-table tr {{ margin-bottom: 10px; padding: 10px 12px; border: 1px solid var(--outline); border-radius: 8px; background: var(--surface); }}
            .admin-table td {{ display: grid; grid-template-columns: minmax(108px, 38%) 1fr; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--outline); }}
            .admin-table td:last-child {{ border-bottom: 0; }}
            .admin-table td::before {{ content: attr(data-label); color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
            .admin-actions {{ flex-wrap: wrap; }}
          }}
          @media (max-width: 420px) {{
            .grid {{ grid-template-columns: 1fr; }}
          }}
        </style>
      </head>
      <body>
        <main>
          <section id="login-section" class="login-shell">
            <div class="title-row">
              <div>
                <div class="eyebrow">Список покупок</div>
                <h1>Администрирование</h1>
              </div>
              <div class="product-mark" aria-hidden="true">SL</div>
            </div>
            <p class="login-copy">Войдите под администратором для управления сервером и пользователями.</p>
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
               <a class="button-link secondary" href="/docs">Открыть Swagger</a>
               <a class="button-link secondary" href="/setup">Настройки сервера</a>
            </div>
          </section>

          <section id="ops-section" class="hidden">
            <h2>Администрирование</h2>
            <div class="toolbar admin-nav" aria-label="Разделы администрирования">
              <button type="button" class="secondary active" data-admin-view="home">Главная</button>
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

          function card(label, value, small = false, trustedHtml = false) {{
            const renderedValue = trustedHtml ? String(value ?? "") : escapeHtml(value);
            return `<div class="card${{small ? " small" : ""}}"><div class="label">${{escapeHtml(label)}}</div><div class="value">${{renderedValue}}</div></div>`;
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

          function buildQuery(params) {{
            const query = new URLSearchParams();
            Object.entries(params).forEach(([key, value]) => {{
              if (value) query.set(key, value);
            }});
            const text = query.toString();
            return text ? `?${{text}}` : "";
          }}

          function setActiveView(view) {{
            document.querySelectorAll("[data-admin-view]").forEach((button) => {{
              button.classList.toggle("active", button.dataset.adminView === view);
            }});
          }}

          function renderHome() {{
            opsPanel.innerHTML = `
              <h3>Главная</h3>
              <p>Выберите раздел в навигации выше. Все действия выполняются от имени администратора, без передачи паролей в URL.</p>
              <div class="grid">
                ${{card("Пользователи", "учётные записи", true)}}
                ${{card("Списки", "архивирование и детали", true)}}
                ${{card("Приглашения", "просмотр и отзыв", true)}}
                ${{card("Система", "миграции и uptime", true)}}
                ${{card("Логи", "последние события", true)}}
                ${{card("Диагностика", "безопасная сводка", true)}}
              </div>`;
          }}

          function renderUsers(data, filters = {{}}) {{
            const rows = data.users.map((user) => `
              <tr>
                <td data-label="Email">${{escapeHtml(user.email)}}</td>
                <td data-label="Admin"><span class="badge${{user.is_admin ? " warn" : ""}}">${{user.is_admin ? "да" : "нет"}}</span></td>
                <td data-label="Статус"><span class="badge${{user.is_active ? " ok" : " error"}}">${{user.is_active ? "активен" : "отключен"}}</span></td>
                <td data-label="Создан">${{escapeHtml(formatDate(user.created_at))}}</td>
                <td data-label="Последний вход">${{escapeHtml(formatDate(user.last_login_at))}}</td>
                <td data-label="Версия приложения">${{escapeHtml([user.last_client_app, user.last_client_version, user.last_client_version_code].filter(Boolean).join(" ")) || "—"}}</td>
                <td data-label="Платформа">${{escapeHtml([user.last_client_platform, user.last_client_os_version].filter(Boolean).join(" ")) || "—"}}</td>
                <td data-label="Последний запуск">${{escapeHtml(formatDate(user.last_client_seen_at))}}</td>
                <td data-label="Списков">${{user.lists_count}}</td>
                <td data-label="Действия">
                  <div class="admin-actions">
                  <button class="compact secondary" data-user-action="${{user.is_active ? "disable" : "enable"}}" data-user-id="${{user.id}}">
                    ${{user.is_active ? "Отключить" : "Включить"}}
                  </button>
                  <button class="compact secondary" data-user-action="set-password" data-user-id="${{user.id}}">Пароль</button>
                  </div>
                </td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Пользователи</h3>
              <div class="filters">
                <div><label for="users-query">Поиск по email</label><input id="users-query" value="${{escapeHtml(filters.query || "")}}" placeholder="user@example.com" /></div>
                <div><label for="users-status">Фильтр</label><select id="users-status">
                  <option value="all" ${{(filters.status || "all") === "all" ? "selected" : ""}}>Все</option>
                  <option value="active" ${{filters.status === "active" ? "selected" : ""}}>Активные</option>
                  <option value="disabled" ${{filters.status === "disabled" ? "selected" : ""}}>Отключённые</option>
                  <option value="admins" ${{filters.status === "admins" ? "selected" : ""}}>Администраторы</option>
                </select></div>
                <div><label for="users-sort">Сортировка</label><select id="users-sort">
                  <option value="created_at" ${{(filters.sort || "created_at") === "created_at" ? "selected" : ""}}>Дата создания</option>
                  <option value="email" ${{filters.sort === "email" ? "selected" : ""}}>Email</option>
                  <option value="last_sync" ${{filters.sort === "last_sync" ? "selected" : ""}}>Последняя синхронизация</option>
                  <option value="android_version" ${{filters.sort === "android_version" ? "selected" : ""}}>Версия Android</option>
                </select></div>
                <button type="button" data-filter-action="users">Применить</button>
              </div>
              <div class="table-wrap">
              <table class="admin-table">
                <thead><tr><th>Email</th><th>Admin</th><th>Статус</th><th>Создан</th><th>Последний вход</th><th>Версия приложения</th><th>Платформа</th><th>Последний запуск</th><th>Списков</th><th>Действия</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="10">Пользователей нет.</td></tr>'}}</tbody>
              </table>
              </div>`;
          }}

          function renderLists(data, filters = {{}}) {{
            const rows = data.lists.map((item) => `
              <tr>
                <td data-label="ID">${{item.id}}</td>
                <td data-label="Название">${{escapeHtml(item.name)}}</td>
                <td data-label="Владелец">${{escapeHtml(item.owner_email || item.owner_id)}}</td>
                <td data-label="Товаров">${{item.items_count}}</td>
                <td data-label="Участников">${{item.members_count}}</td>
                <td data-label="Статус"><span class="badge${{item.is_archived ? " warn" : " ok"}}">${{item.is_archived ? "архив" : "активен"}}</span></td>
                <td data-label="Обновлён">${{escapeHtml(formatDate(item.updated_at))}}</td>
                <td data-label="Действия">
                  <div class="admin-actions">
                  <button class="compact secondary" data-list-action="details" data-list-id="${{item.id}}">Детали</button>
                  <button class="compact secondary" data-list-action="${{item.is_archived ? "restore" : "archive"}}" data-list-id="${{item.id}}">
                    ${{item.is_archived ? "Восстановить" : "Архивировать"}}
                  </button>
                  </div>
                </td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Списки</h3>
              <div class="filters">
                <div><label for="lists-query">Поиск по названию</label><input id="lists-query" value="${{escapeHtml(filters.query || "")}}" placeholder="Покупки" /></div>
                <div><label for="lists-status">Фильтр</label><select id="lists-status">
                  <option value="all" ${{(filters.status || "all") === "all" ? "selected" : ""}}>Все</option>
                  <option value="active" ${{filters.status === "active" ? "selected" : ""}}>Активные</option>
                  <option value="archived" ${{filters.status === "archived" ? "selected" : ""}}>Архивные</option>
                </select></div>
                <div></div>
                <button type="button" data-filter-action="lists">Применить</button>
              </div>
              <div class="table-wrap">
              <table class="admin-table">
                <thead><tr><th>ID</th><th>Название</th><th>Владелец</th><th>Товаров</th><th>Участников</th><th>Статус</th><th>Обновлен</th><th>Действия</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="8">Списков нет.</td></tr>'}}</tbody>
              </table>
              </div>`;
          }}

          function renderInvites(data, filters = {{}}) {{
            const rows = data.invites.map((invite) => `
              <tr>
                <td data-label="Список">${{escapeHtml(invite.list_name || invite.list_id)}} <span class="label">#${{invite.list_id}}</span></td>
                <td data-label="Создал">${{escapeHtml(invite.created_by || "")}}</td>
                <td data-label="Token">${{escapeHtml(invite.token_preview)}}</td>
                <td data-label="Создано">${{escapeHtml(formatDate(invite.created_at))}}</td>
                <td data-label="Истекает">${{escapeHtml(formatDate(invite.expires_at))}}</td>
                <td data-label="Использовано">${{escapeHtml(formatDate(invite.used_at))}}</td>
                <td data-label="Отозвано">${{escapeHtml(formatDate(invite.revoked_at))}}</td>
                <td data-label="Действия">
                  <div class="admin-actions">
                    ${{invite.used_at || invite.revoked_at ? "" : `<button class="compact danger" data-invite-action="revoke" data-invite-id="${{invite.id}}">Отозвать</button>`}}
                  </div>
                </td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Приглашения</h3>
              <div class="filters">
                <div><label for="invites-query">Поиск по списку или ID</label><input id="invites-query" value="${{escapeHtml(filters.query || "")}}" placeholder="Покупки или 12" /></div>
                <div><label for="invites-status">Фильтр</label><select id="invites-status">
                  <option value="active" ${{(filters.status || "active") === "active" ? "selected" : ""}}>Активные</option>
                  <option value="used" ${{filters.status === "used" ? "selected" : ""}}>Использованные</option>
                  <option value="expired" ${{filters.status === "expired" ? "selected" : ""}}>Истёкшие</option>
                  <option value="revoked" ${{filters.status === "revoked" ? "selected" : ""}}>Отозванные</option>
                  <option value="all" ${{filters.status === "all" ? "selected" : ""}}>Все</option>
                </select></div>
                <div></div>
                <button type="button" data-filter-action="invites">Применить</button>
              </div>
              <div class="table-wrap">
              <table class="admin-table">
                <thead><tr><th>Список</th><th>Создал</th><th>Token</th><th>Создано</th><th>Истекает</th><th>Использовано</th><th>Отозвано</th><th>Действия</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="8">Приглашений нет.</td></tr>'}}</tbody>
              </table>
              </div>`;
          }}

          function renderSystem(data) {{
            const migration = data.migration || {{}};
            opsPanel.innerHTML = `
              <h3>Система</h3>
              <div class="grid">
                ${{card("Backend version", data.version, true)}}
                ${{card("База данных", data.database === "ok" ? '<span class="badge ok">доступна</span>' : '<span class="badge error">ошибка</span>', true, true)}}
                ${{card("Current revision", migration.current || "нет данных", true)}}
                ${{card("Head revision", migration.head || "нет данных", true)}}
                ${{card("Migration status", `<span class="badge ${{migration.status === "up-to-date" ? "ok" : "warn"}}">${{escapeHtml(migration.status || "unknown")}}</span>`, true, true)}}
                ${{card("Uptime", `${{data.uptime_seconds}} сек.`, true)}}
                ${{card("Server time", formatDate(data.server_time), true)}}
                ${{card("Регистрация", data.registration_enabled ? '<span class="badge ok">разрешена</span>' : '<span class="badge warn">отключена</span>', true, true)}}
                ${{card("Rate limit", data.rate_limit || "нет данных", true)}}
                ${{card("Окружение", data.environment || "production", true)}}
              </div>`;
          }}

          function safeReport(title, data) {{
            return `${{title}}\n${{JSON.stringify(data, null, 2)}}`;
          }}

          function renderLogs(data, filters = {{}}) {{
            const events = data.events || [];
            const rows = events.map((event) => `
              <tr>
                <td data-label="Время">${{escapeHtml(formatDate(event.timestamp))}}</td>
                <td data-label="Уровень"><span class="badge${{event.level === "error" ? " error" : event.level === "warning" ? " warn" : " ok"}}">${{escapeHtml(event.level || "info")}}</span></td>
                <td data-label="Событие">${{escapeHtml(event.event || "")}}</td>
                <td data-label="Детали">${{escapeHtml(event.details || "")}}</td>
              </tr>`).join("");
            opsPanel.innerHTML = `
              <h3>Логи</h3>
              <div class="filters">
                <div><label for="logs-event">Фильтр события</label><input id="logs-event" value="${{escapeHtml(filters.event_type || "")}}" placeholder="login, rate limit..." /></div>
                <div><label for="logs-level">Уровень</label><select id="logs-level">
                  <option value="all" ${{(filters.level || "all") === "all" ? "selected" : ""}}>Все</option>
                  <option value="info" ${{filters.level === "info" ? "selected" : ""}}>Info</option>
                  <option value="warning" ${{filters.level === "warning" ? "selected" : ""}}>Warning</option>
                  <option value="error" ${{filters.level === "error" ? "selected" : ""}}>Error</option>
                </select></div>
                <button type="button" data-filter-action="logs">Обновить</button>
                <button type="button" class="secondary" data-copy-report="logs">Скопировать логи</button>
              </div>
              <div class="table-wrap">
              <table class="admin-table">
                <thead><tr><th>Время</th><th>Уровень</th><th>Событие</th><th>Детали</th></tr></thead>
                <tbody>${{rows || '<tr><td colspan="4">Событий нет.</td></tr>'}}</tbody>
              </table>
              </div>
              <textarea class="hidden" id="logs-report" readonly>${{escapeHtml(safeReport("Shopping List Admin Logs", data))}}</textarea>`;
          }}

          function renderDiagnostics(data) {{
            opsPanel.innerHTML = `
              <h3>Диагностика</h3>
              <div class="actions" style="margin-top: 0; margin-bottom: 14px;">
                <button type="button" class="secondary" data-copy-report="diagnostics">Скопировать диагностику</button>
              </div>
              <div class="grid">
                ${{card("Backend version", data.version, true)}}
                ${{card("DB status", data.health?.database || "нет данных", true)}}
                ${{card("Migration", data.migration?.status || "нет данных", true)}}
                ${{card("Uptime", `${{data.uptime_seconds}} сек.`, true)}}
                ${{card("Users", data.counts?.users ?? 0)}}
                ${{card("Lists", data.counts?.lists ?? 0)}}
                ${{card("Items", data.counts?.items ?? 0)}}
                ${{card("Invites", data.counts?.invites ?? 0)}}
                ${{card("Client operations", data.counts?.client_operations ?? 0)}}
              </div>
              <h4>Последние события</h4>
              <pre>${{escapeHtml(JSON.stringify(data.last_events || [], null, 2))}}</pre>
              <textarea class="hidden" id="diagnostics-report" readonly>${{escapeHtml(safeReport("Shopping List Admin Diagnostics", data))}}</textarea>`;
          }}

          async function loadAdminView(view, filters = {{}}) {{
            try {{
              setActiveView(view);
              opsPanel.innerHTML = "<p>Загрузка...</p>";
              if (view === "home") renderHome();
              if (view === "users") renderUsers(await adminFetch("/admin/users" + buildQuery(filters)), filters);
              if (view === "lists") renderLists(await adminFetch("/admin/lists" + buildQuery(filters)), filters);
              if (view === "invites") renderInvites(await adminFetch("/admin/invites" + buildQuery(filters)), filters);
              if (view === "system") renderSystem(await adminFetch("/admin/system"));
              if (view === "logs") renderLogs(await adminFetch("/admin/logs" + buildQuery(filters)), filters);
              if (view === "diagnostics") renderDiagnostics(await adminFetch("/admin/diagnostics"));
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
              document.body.classList.remove("authenticated");
              statusSection.classList.add("hidden");
              opsSection.classList.add("hidden");
              return;
            }}
            const response = await fetch("/admin/status", {{
              headers: {{ Authorization: `Bearer ${{token}}` }},
            }});
            if (response.status === 401 || response.status === 403) {{
              localStorage.removeItem(tokenKey);
              document.body.classList.remove("authenticated");
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
            document.body.classList.add("authenticated");
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
            renderHome();
            setActiveView("home");
          }});

          refreshButton.addEventListener("click", loadStatus);
          document.querySelectorAll("[data-admin-view]").forEach((button) => {{
            button.addEventListener("click", () => loadAdminView(button.dataset.adminView));
          }});
          opsPanel.addEventListener("click", async (event) => {{
            const button = event.target.closest("button");
            if (!button) return;
            try {{
              if (button.dataset.filterAction === "users") {{
                await loadAdminView("users", {{
                  query: document.querySelector("#users-query")?.value || "",
                  status: document.querySelector("#users-status")?.value || "all",
                  sort: document.querySelector("#users-sort")?.value || "created_at",
                }});
                return;
              }}
              if (button.dataset.filterAction === "lists") {{
                await loadAdminView("lists", {{
                  query: document.querySelector("#lists-query")?.value || "",
                  status: document.querySelector("#lists-status")?.value || "all",
                }});
                return;
              }}
              if (button.dataset.filterAction === "invites") {{
                await loadAdminView("invites", {{
                  query: document.querySelector("#invites-query")?.value || "",
                  status: document.querySelector("#invites-status")?.value || "active",
                }});
                return;
              }}
              if (button.dataset.filterAction === "logs") {{
                await loadAdminView("logs", {{
                  event_type: document.querySelector("#logs-event")?.value || "",
                  level: document.querySelector("#logs-level")?.value || "all",
                }});
                return;
              }}
              if (button.dataset.copyReport === "logs" || button.dataset.copyReport === "diagnostics") {{
                const report = document.querySelector(`#${{button.dataset.copyReport}}-report`)?.textContent || "";
                await navigator.clipboard.writeText(report);
                showMessage("Отчёт скопирован.", "ok");
                return;
              }}
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
            document.body.classList.remove("authenticated");
            statusSection.classList.add("hidden");
            opsSection.classList.add("hidden");
            showMessage("Вы вышли из админ-панели.", "ok");
          }});

          loadStatus().then(() => {{
            if (localStorage.getItem(tokenKey)) {{
              renderHome();
              setActiveView("home");
            }}
          }});
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
    return invite.expires_at is not None and invite.expires_at < utc_now()


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
        "server_time": utc_now(),
    }


@router.get("/admin", response_class=HTMLResponse)
def admin_page():
    return HTMLResponse(
        render_admin_page(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/admin/status", response_model=AdminStatusResponse)
def admin_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    server_settings = get_server_settings(db)
    now = utc_now()
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
    user.last_login_at = utc_now()
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
        expires_at=utc_now() + timedelta(hours=settings.invite_token_hours),
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
    invite.used_at = utc_now()
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
