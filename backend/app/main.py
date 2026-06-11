import secrets
from html import escape
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from alembic.runtime.migration import MigrationContext
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import engine, get_db
from .models import ActivityLog, ListInvite, ListMember, ShoppingItem, ShoppingList, User
from .schemas import (
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
from .security import create_access_token, get_current_user, hash_password, verify_password
from .setup import get_server_settings, router as setup_router


APP_VERSION = "1.3.1"

app = FastAPI(title="API синхронизации списка покупок", version=APP_VERSION)
app.include_router(setup_router)


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
        .where(ShoppingList.id == list_id, ListMember.user_id == user.id)
    )
    if shopping_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список не найден")
    return shopping_list


def require_list_owner(db: Session, user: User, list_id: int) -> ShoppingList:
    shopping_list = db.scalar(select(ShoppingList).where(ShoppingList.id == list_id, ShoppingList.owner_id == user.id))
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
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


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


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "version": APP_VERSION,
        "database": "ok",
        "migration": current_migration(),
        "server_time": datetime.utcnow(),
    }


@app.get("/admin/status", response_model=AdminStatusResponse)
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
        "invites_active_count": db.scalar(
            select(func.count(ListInvite.id)).where(ListInvite.used_at.is_(None), (ListInvite.expires_at.is_(None)) | (ListInvite.expires_at >= now))
        ) or 0,
        "pending_invites_count": db.scalar(select(func.count(ListInvite.id)).where(ListInvite.used_at.is_(None))) or 0,
        "invite_token_hours": settings.invite_token_hours,
        "app_name": server_settings.app_name,
        "external_url": server_settings.external_url,
        "allow_registration": server_settings.allow_registration,
        "setup_completed": server_settings.setup_completed,
    }


@app.get("/server-config", response_model=PublicServerConfig)
def server_config(db: Session = Depends(get_db)):
    return get_server_settings(db)


@app.post("/auth/register", response_model=TokenResponse)
def register(payload: AuthRequest, db: Session = Depends(get_db)):
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


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/sync", response_model=SyncResponse)
def sync(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lists = db.scalars(
        select(ShoppingList)
        .join(ListMember, ListMember.list_id == ShoppingList.id)
        .where(ListMember.user_id == current_user.id)
        .options(selectinload(ShoppingList.items))
        .order_by(ShoppingList.updated_at.desc())
    ).all()
    for shopping_list in lists:
        shopping_list.items = sort_items_for_display(shopping_list.items)
    return {"lists": lists}


@app.post("/lists")
def create_list(payload: ListCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = ShoppingList(name=payload.name, owner_id=current_user.id)
    db.add(shopping_list)
    db.flush()
    db.add(ListMember(list_id=shopping_list.id, user_id=current_user.id))
    write_activity(db, current_user, "list_created", list_id=shopping_list.id, details=shopping_list.name)
    db.commit()
    return {"id": shopping_list.id, "name": shopping_list.name}


@app.patch("/lists/{list_id}")
def update_list(
    list_id: int,
    payload: ListUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shopping_list = require_list_owner(db, current_user, list_id)
    old_name = shopping_list.name
    shopping_list.name = payload.name
    write_activity(db, current_user, "list_renamed", list_id=shopping_list.id, details=f"{old_name} -> {payload.name}")
    db.commit()
    return {"id": shopping_list.id, "name": shopping_list.name}


@app.delete("/lists/{list_id}")
def delete_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    db.commit()
    return {"status": "deleted"}


@app.delete("/lists/{list_id}/items")
def clear_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    items = db.scalars(select(ShoppingItem).where(ShoppingItem.list_id == shopping_list.id)).all()
    for item in items:
        db.delete(item)
    write_activity(db, current_user, "list_cleared", list_id=shopping_list.id, details=f"Удалено позиций: {len(items)}")
    db.commit()
    return {"status": "cleared"}


@app.delete("/lists/{list_id}/items/checked")
def clear_checked_items(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    items = db.scalars(
        select(ShoppingItem).where(ShoppingItem.list_id == shopping_list.id, ShoppingItem.is_checked.is_(True))
    ).all()
    for item in items:
        db.delete(item)
    write_activity(db, current_user, "checked_items_cleared", list_id=shopping_list.id, details=f"Удалено позиций: {len(items)}")
    db.commit()
    return {"status": "cleared"}


@app.patch("/lists/{list_id}/items/checked")
def restore_checked_items(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = require_list_access(db, current_user, list_id)
    items = db.scalars(
        select(ShoppingItem).where(ShoppingItem.list_id == shopping_list.id, ShoppingItem.is_checked.is_(True))
    ).all()
    for item in items:
        item.is_checked = False
    write_activity(db, current_user, "checked_items_restored", list_id=shopping_list.id, details=f"Возвращено позиций: {len(items)}")
    db.commit()
    return {"status": "restored", "count": len(items)}


@app.post("/lists/{list_id}/copy")
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


@app.get("/lists/{list_id}/members", response_model=MembersResponse)
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


@app.get("/lists/{list_id}/activity", response_model=ActivityResponse)
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


@app.post("/lists/{list_id}/share")
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


@app.post("/lists/{list_id}/invite", response_model=InviteResponse)
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


@app.post("/invites/{token}/accept")
def accept_invite(token: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invite = db.scalar(select(ListInvite).where(ListInvite.token == token))
    if invite is None or invite.used_at is not None or invite_is_expired(invite):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
    add_member_if_missing(db, invite.list_id, current_user.id)
    invite.used_at = datetime.utcnow()
    write_activity(db, current_user, "invite_accepted", list_id=invite.list_id)
    db.commit()
    return {"status": "joined", "list_id": invite.list_id}


@app.get("/join/{token}", response_class=HTMLResponse)
def join_page(token: str, db: Session = Depends(get_db)):
    invite = db.scalar(select(ListInvite).where(ListInvite.token == token))
    if invite is None or invite.used_at is not None or invite_is_expired(invite):
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


@app.post("/lists/{list_id}/items")
def create_item(
    list_id: int,
    payload: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_list_access(db, current_user, list_id)
    item = ShoppingItem(list_id=list_id, name=payload.name, quantity=payload.quantity)
    db.add(item)
    db.flush()
    write_activity(db, current_user, "item_created", list_id=list_id, item_id=item.id, item_name=item.name, details=item.quantity)
    db.commit()
    db.refresh(item)
    return item


@app.patch("/items/{item_id}")
def update_item(
    item_id: int,
    payload: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}")
def delete_item(item_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(ShoppingItem).where(ShoppingItem.id == item_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    require_list_access(db, current_user, item.list_id)
    write_activity(db, current_user, "item_deleted", list_id=item.list_id, item_id=item.id, item_name=item.name, details=item.quantity)
    db.delete(item)
    db.commit()
    return {"status": "deleted"}
