import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import ClientOperation, ListInvite, ListMember, ShoppingItem, ShoppingList, User
from ..rate_limit import check_rate_limit
from ..security import get_current_user, hash_password
from ..services.diagnostics_service import APP_START_TIME, recent_events, record_event, uptime_seconds
from ..services.migration_service import migration_status
from ..setup import get_server_settings
from .api import APP_VERSION


router = APIRouter()


class AdminSetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


def require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступно только администратору")


def active_admins_count(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).where(User.is_admin.is_(True), User.is_active.is_(True))) or 0


def get_target_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


def get_target_list(db: Session, list_id: int) -> ShoppingList:
    shopping_list = db.get(ShoppingList, list_id)
    if shopping_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список не найден")
    return shopping_list


def token_preview(token: str) -> str:
    return f"...{token[-6:]}" if len(token) > 6 else "..."


def count_or_zero(db: Session, query) -> int:
    return db.scalar(query) or 0


def db_ping(db: Session) -> str:
    db.execute(text("SELECT 1"))
    return "ok"


@router.get("/health/live")
def health_live():
    return {"status": "ok", "version": APP_VERSION, "timestamp": datetime.utcnow()}


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db_status = db_ping(db)
        migrations = migration_status()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready") from exc
    return {
        "status": "ok",
        "version": APP_VERSION,
        "timestamp": datetime.utcnow(),
        "database": db_status,
        "migration": migrations["status"],
    }


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db_ping(db)
    except Exception:
        return {"status": "error", "version": APP_VERSION, "timestamp": datetime.utcnow()}
    return {"status": "ok", "version": APP_VERSION, "timestamp": datetime.utcnow()}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return {
        "version": APP_VERSION,
        "users_total": count_or_zero(db, select(func.count(User.id))),
        "lists_total": count_or_zero(db, select(func.count(ShoppingList.id))),
        "items_total": count_or_zero(db, select(func.count(ShoppingItem.id))),
        "invites_active": count_or_zero(
            db,
            select(func.count(ListInvite.id)).where(
                ListInvite.used_at.is_(None),
                ListInvite.revoked_at.is_(None),
                (ListInvite.expires_at.is_(None)) | (ListInvite.expires_at >= now),
            ),
        ),
        "client_operations_total": count_or_zero(db, select(func.count(ClientOperation.id))),
        "app_uptime_seconds": uptime_seconds(),
        "db_status": db_ping(db),
    }


@router.get("/admin/system")
def admin_system(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    server_settings = get_server_settings(db)
    migrations = migration_status()
    return {
        "version": APP_VERSION,
        "database": db_ping(db),
        "migration": migrations,
        "uptime_seconds": uptime_seconds(),
        "environment": os.getenv("APP_ENV", "production"),
        "registration_enabled": server_settings.allow_registration,
        "rate_limit": "in-memory",
        "docker_image_version": os.getenv("IMAGE_VERSION", APP_VERSION),
        "app_start_time": APP_START_TIME,
        "server_time": datetime.utcnow(),
    }


@router.get("/admin/diagnostics")
def admin_diagnostics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    return {
        "version": APP_VERSION,
        "health": {"database": db_ping(db), "ready": "ok"},
        "migration": migration_status(),
        "counts": {
            "users": count_or_zero(db, select(func.count(User.id))),
            "lists": count_or_zero(db, select(func.count(ShoppingList.id))),
            "items": count_or_zero(db, select(func.count(ShoppingItem.id))),
            "invites": count_or_zero(db, select(func.count(ListInvite.id))),
            "client_operations": count_or_zero(db, select(func.count(ClientOperation.id))),
        },
        "last_events": recent_events(20),
    }


@router.get("/admin/logs")
def admin_logs(current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    return {"events": recent_events(300)}


@router.get("/admin/users")
def admin_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    rows = []
    for user in users:
        rows.append(
            {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login_at": user.last_login_at,
                "last_client_app": user.last_client_app,
                "last_client_version": user.last_client_version,
                "last_client_version_code": user.last_client_version_code,
                "last_client_platform": user.last_client_platform,
                "last_client_os_version": user.last_client_os_version,
                "last_client_seen_at": user.last_client_seen_at,
                "lists_count": count_or_zero(db, select(func.count(ListMember.id)).where(ListMember.user_id == user.id)),
            }
        )
    return {"users": rows}


@router.post("/admin/users/{user_id}/disable")
def disable_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    user = get_target_user(db, user_id)
    if user.is_admin and user.is_active and active_admins_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя отключить последнего активного администратора")
    user.is_active = False
    record_event("user disabled", f"user_id={user.id}", "warning")
    db.commit()
    return {"status": "ok", "user_id": user.id, "is_active": user.is_active}


@router.post("/admin/users/{user_id}/enable")
def enable_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    user = get_target_user(db, user_id)
    user.is_active = True
    record_event("user enabled", f"user_id={user.id}")
    db.commit()
    return {"status": "ok", "user_id": user.id, "is_active": user.is_active}


@router.post("/admin/users/{user_id}/set-password")
def set_user_password(
    user_id: int,
    payload: AdminSetPasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    check_rate_limit(request, "admin_set_password", str(user_id), limit=8, window_seconds=60)
    user = get_target_user(db, user_id)
    user.password_hash = hash_password(payload.password)
    record_event("user password reset", f"user_id={user.id}", "warning")
    db.commit()
    return {"status": "ok", "user_id": user.id}


@router.get("/admin/lists")
def admin_lists(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    lists = db.scalars(select(ShoppingList).order_by(ShoppingList.updated_at.desc(), ShoppingList.id.desc())).all()
    rows = []
    for shopping_list in lists:
        owner = db.get(User, shopping_list.owner_id)
        rows.append(
            {
                "id": shopping_list.id,
                "name": shopping_list.name,
                "owner_id": shopping_list.owner_id,
                "owner_email": owner.email if owner else None,
                "items_count": count_or_zero(db, select(func.count(ShoppingItem.id)).where(ShoppingItem.list_id == shopping_list.id)),
                "members_count": count_or_zero(db, select(func.count(ListMember.id)).where(ListMember.list_id == shopping_list.id)),
                "updated_at": shopping_list.updated_at,
                "archived_at": shopping_list.archived_at,
                "is_archived": shopping_list.archived_at is not None,
            }
        )
    return {"lists": rows}


@router.get("/admin/lists/{list_id}")
def admin_list_details(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    shopping_list = get_target_list(db, list_id)
    return {
        "id": shopping_list.id,
        "name": shopping_list.name,
        "owner_id": shopping_list.owner_id,
        "updated_at": shopping_list.updated_at,
        "archived_at": shopping_list.archived_at,
        "items": [
            {"id": item.id, "name": item.name, "quantity": item.quantity, "is_checked": item.is_checked}
            for item in db.scalars(select(ShoppingItem).where(ShoppingItem.list_id == list_id).order_by(ShoppingItem.id)).all()
        ],
        "members": [
            {"user_id": member.user_id}
            for member in db.scalars(select(ListMember).where(ListMember.list_id == list_id).order_by(ListMember.id)).all()
        ],
    }


@router.post("/admin/lists/{list_id}/archive")
def archive_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    shopping_list = get_target_list(db, list_id)
    if shopping_list.archived_at is None:
        shopping_list.archived_at = datetime.utcnow()
    record_event("list archived", f"list_id={shopping_list.id}", "warning")
    db.commit()
    return {"status": "ok", "list_id": shopping_list.id, "archived_at": shopping_list.archived_at}


@router.post("/admin/lists/{list_id}/restore")
def restore_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    shopping_list = get_target_list(db, list_id)
    shopping_list.archived_at = None
    record_event("list restored", f"list_id={shopping_list.id}")
    db.commit()
    return {"status": "ok", "list_id": shopping_list.id, "archived_at": None}


@router.get("/admin/invites")
def admin_invites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    invites = db.scalars(select(ListInvite).order_by(ListInvite.created_at.desc(), ListInvite.id.desc())).all()
    rows = []
    for invite in invites:
        shopping_list = db.get(ShoppingList, invite.list_id)
        creator = db.get(User, invite.created_by_id)
        rows.append(
            {
                "id": invite.id,
                "list_id": invite.list_id,
                "list_name": shopping_list.name if shopping_list else None,
                "created_by": creator.email if creator else None,
                "created_at": invite.created_at,
                "expires_at": invite.expires_at,
                "used_at": invite.used_at,
                "revoked_at": invite.revoked_at,
                "token_preview": token_preview(invite.token),
            }
        )
    return {"invites": rows}


@router.post("/admin/invites/{invite_id}/revoke")
def revoke_invite(invite_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current_user)
    invite = db.get(ListInvite, invite_id)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
    if invite.revoked_at is None:
        invite.revoked_at = datetime.utcnow()
    record_event("invite revoked", f"invite_id={invite.id}", "warning")
    db.commit()
    return {"status": "ok", "invite_id": invite.id, "revoked_at": invite.revoked_at}
