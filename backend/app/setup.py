from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import ServerSetting


router = APIRouter()


def get_server_settings(db: Session) -> ServerSetting:
    server_settings = db.get(ServerSetting, 1)
    if server_settings is None:
        server_settings = ServerSetting(id=1)
        db.add(server_settings)
        db.commit()
        db.refresh(server_settings)
    return server_settings


def verify_setup_token(token: str | None) -> None:
    if settings.setup_token and token != settings.setup_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong setup token")


def has_setup_access(server_settings: ServerSetting, token: str | None) -> bool:
    if not server_settings.setup_completed:
        return True
    return bool(settings.setup_token and token == settings.setup_token)


def render_locked_page(server_settings: ServerSetting) -> str:
    return f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Shopping List setup</title>
        <style>
          :root {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
          body {{ margin: 0; background: #f6f7f9; color: #1f2933; }}
          main {{ max-width: 680px; margin: 0 auto; padding: 32px 18px; }}
          section {{ background: #ffffff; border: 1px solid #dde3ea; border-radius: 8px; padding: 24px; }}
          h1 {{ margin: 0 0 8px; font-size: 28px; }}
          p {{ margin: 0 0 14px; color: #52616f; line-height: 1.5; }}
          code {{ background: #eef2f6; padding: 2px 5px; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <main>
          <section>
            <h1>Setup is complete</h1>
            <p>The server is configured and the first-run wizard is locked.</p>
            <p>External address: <code>{escape(server_settings.external_url)}</code></p>
            <p>To reconfigure from the web UI later, set <code>SETUP_TOKEN</code> for the API container and open <code>/setup?token=your-token</code>.</p>
          </section>
        </main>
      </body>
    </html>
    """


def render_setup_page(server_settings: ServerSetting, token: str = "", message: str = "") -> str:
    token_field = ""
    if server_settings.setup_completed and settings.setup_token:
        token_field = f"""
              <label for="token">Admin token</label>
              <input id="token" name="token" type="password" value="{escape(token)}" autocomplete="current-password" />
        """
    else:
        token_field = f'<input name="token" type="hidden" value="{escape(token)}" />'

    return f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Shopping List setup</title>
        <style>
          :root {{
            color-scheme: light;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }}
          body {{
            margin: 0;
            background: #f6f7f9;
            color: #1f2933;
          }}
          main {{
            max-width: 680px;
            margin: 0 auto;
            padding: 32px 18px;
          }}
          section {{
            background: #ffffff;
            border: 1px solid #dde3ea;
            border-radius: 8px;
            padding: 24px;
          }}
          h1 {{
            margin: 0 0 8px;
            font-size: 28px;
          }}
          p {{
            margin: 0 0 20px;
            color: #52616f;
            line-height: 1.5;
          }}
          label {{
            display: block;
            margin: 14px 0 6px;
            font-weight: 650;
          }}
          input[type="text"], input[type="password"], input[type="url"] {{
            box-sizing: border-box;
            width: 100%;
            min-height: 44px;
            border: 1px solid #b8c4d0;
            border-radius: 6px;
            padding: 10px 12px;
            font: inherit;
          }}
          .row {{
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 14px;
          }}
          .row input {{
            width: 18px;
            height: 18px;
          }}
          button {{
            margin-top: 22px;
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
          .message {{
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 6px;
            background: #e7f5ec;
            color: #14532d;
          }}
          .warning {{
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 6px;
            background: #fff7ed;
            color: #9a3412;
          }}
          code {{
            background: #eef2f6;
            padding: 2px 5px;
            border-radius: 4px;
          }}
        </style>
      </head>
      <body>
        <main>
          <section>
            <h1>Shopping List setup</h1>
            <p>Configure the public server address and key runtime options after Docker startup.</p>
            {f'<div class="message">{escape(message)}</div>' if message else ''}
            <form method="post" action="/setup">
              {token_field}

              <label for="app_name">App name</label>
              <input id="app_name" name="app_name" type="text" value="{escape(server_settings.app_name)}" required maxlength="80" />

              <label for="external_url">External HTTPS address</label>
              <input id="external_url" name="external_url" type="url" value="{escape(server_settings.external_url)}" placeholder="https://shopping.example.com" required maxlength="255" />

              <label class="row" for="allow_registration">
                <input id="allow_registration" name="allow_registration" type="checkbox" value="true" {"checked" if server_settings.allow_registration else ""} />
                Allow new account registration
              </label>

              <button type="submit">Save settings</button>
            </form>
            <p style="margin-top: 18px;">Public config is available at <code>/server-config</code>.</p>
          </section>
        </main>
      </body>
    </html>
    """


@router.get("/setup", response_class=HTMLResponse)
def setup_page(token: str = "", message: str = "", db: Session = Depends(get_db)):
    server_settings = get_server_settings(db)
    if not has_setup_access(server_settings, token or None):
        return render_locked_page(server_settings)

    if server_settings.setup_completed:
        verify_setup_token(token or None)
    return render_setup_page(server_settings, token=token, message=message)


@router.post("/setup")
def save_setup(
    token: str = Form(default=""),
    app_name: str = Form(...),
    external_url: str = Form(...),
    allow_registration: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    server_settings = get_server_settings(db)
    if not has_setup_access(server_settings, token or None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Setup is already completed")
    if server_settings.setup_completed:
        verify_setup_token(token or None)

    normalized_url = external_url.strip().rstrip("/")
    if not normalized_url.startswith("https://"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="External address must start with https://")

    server_settings.app_name = app_name.strip()
    server_settings.external_url = normalized_url
    server_settings.allow_registration = allow_registration
    server_settings.setup_completed = True
    db.commit()

    redirect_url = "/setup?message=Settings%20saved"
    if token:
        redirect_url = f"/setup?token={quote(token)}&message=Settings%20saved"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
