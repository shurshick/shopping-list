import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select

from .database import SessionLocal
from .models import ActivityLog, ListInvite, ListMember, ServerSetting, ShoppingItem, ShoppingList, User
from .services.diagnostics_service import record_event
from .services.migration_service import migration_status


def dt(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def count_rows(db, model) -> int:
    return db.scalar(select(func.count(model.id))) or 0


def build_backup(include_auth_hashes: bool = False) -> dict[str, Any]:
    with SessionLocal() as db:
        users = []
        for user in db.scalars(select(User).order_by(User.id)).all():
            row = {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "last_login_at": dt(user.last_login_at),
                "created_at": dt(user.created_at),
            }
            if include_auth_hashes:
                row["password_hash"] = user.password_hash
            users.append(row)

        return {
            "format": "shopping-list-backup-v1",
            "created_at": datetime.utcnow().isoformat(),
            "contains_auth_hashes": include_auth_hashes,
            "users": users,
            "server_settings": [
                {
                    "id": setting.id,
                    "app_name": setting.app_name,
                    "external_url": setting.external_url,
                    "allow_registration": setting.allow_registration,
                    "setup_completed": setting.setup_completed,
                    "updated_at": dt(setting.updated_at),
                }
                for setting in db.scalars(select(ServerSetting).order_by(ServerSetting.id)).all()
            ],
            "lists": [
                {
                    "id": item.id,
                    "name": item.name,
                    "owner_id": item.owner_id,
                    "updated_at": dt(item.updated_at),
                    "archived_at": dt(item.archived_at),
                }
                for item in db.scalars(select(ShoppingList).order_by(ShoppingList.id)).all()
            ],
            "memberships": [
                {"id": member.id, "list_id": member.list_id, "user_id": member.user_id}
                for member in db.scalars(select(ListMember).order_by(ListMember.id)).all()
            ],
            "items": [
                {
                    "id": item.id,
                    "list_id": item.list_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "is_checked": item.is_checked,
                    "updated_at": dt(item.updated_at),
                }
                for item in db.scalars(select(ShoppingItem).order_by(ShoppingItem.id)).all()
            ],
            "invites": [
                {
                    "id": invite.id,
                    "list_id": invite.list_id,
                    "created_by_id": invite.created_by_id,
                    "created_at": dt(invite.created_at),
                    "expires_at": dt(invite.expires_at),
                    "used_at": dt(invite.used_at),
                    "revoked_at": dt(invite.revoked_at),
                    "token_preview": f"...{invite.token[-6:]}",
                }
                for invite in db.scalars(select(ListInvite).order_by(ListInvite.id)).all()
            ],
        }


def write_backup(output: Path, include_auth_hashes: bool = False) -> None:
    data = build_backup(include_auth_hashes=include_auth_hashes)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    record_event("backup created", str(output))


def restore_backup(input_path: Path, force: bool = False) -> None:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if data.get("format") != "shopping-list-backup-v1":
        raise SystemExit("Unsupported backup format")

    with SessionLocal() as db:
        has_data = any(count_rows(db, model) for model in (User, ShoppingList, ShoppingItem, ListMember, ServerSetting))
        if has_data and not force:
            raise SystemExit("Database is not empty. Use --force only after making a separate backup.")

        if force:
            for model in (ActivityLog, ListInvite, ShoppingItem, ListMember, ShoppingList, ServerSetting, User):
                db.execute(delete(model))

        for row in data.get("users", []):
            db.add(
                User(
                    id=row["id"],
                    email=row["email"],
                    password_hash=row.get("password_hash", "disabled$backup$no-auth-hash"),
                    is_admin=row.get("is_admin", False),
                    is_active=row.get("is_active", True),
                    last_login_at=parse_dt(row.get("last_login_at")),
                    created_at=parse_dt(row.get("created_at")) or datetime.utcnow(),
                )
            )
        for row in data.get("server_settings", []):
            db.add(
                ServerSetting(
                    id=row["id"],
                    app_name=row.get("app_name", "Список покупок"),
                    external_url=row.get("external_url", ""),
                    allow_registration=row.get("allow_registration", True),
                    setup_completed=row.get("setup_completed", False),
                    updated_at=parse_dt(row.get("updated_at")) or datetime.utcnow(),
                )
            )
        for row in data.get("lists", []):
            db.add(
                ShoppingList(
                    id=row["id"],
                    name=row["name"],
                    owner_id=row["owner_id"],
                    updated_at=parse_dt(row.get("updated_at")) or datetime.utcnow(),
                    archived_at=parse_dt(row.get("archived_at")),
                )
            )
        for row in data.get("memberships", []):
            db.add(ListMember(id=row["id"], list_id=row["list_id"], user_id=row["user_id"]))
        for row in data.get("items", []):
            db.add(
                ShoppingItem(
                    id=row["id"],
                    list_id=row["list_id"],
                    name=row["name"],
                    quantity=row.get("quantity", ""),
                    is_checked=row.get("is_checked", False),
                    updated_at=parse_dt(row.get("updated_at")) or datetime.utcnow(),
                )
            )
        db.commit()
        record_event("backup restored", str(input_path), "warning")


def print_db_status() -> None:
    print(json.dumps(migration_status(), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subcommands = parser.add_subparsers(dest="command", required=True)

    backup = subcommands.add_parser("backup")
    backup.add_argument("--output", required=True)
    backup.add_argument("--include-auth-hashes", action="store_true")

    restore = subcommands.add_parser("restore")
    restore.add_argument("--input", required=True)
    restore.add_argument("--force", action="store_true")

    subcommands.add_parser("db-status")

    args = parser.parse_args()
    if args.command == "backup":
        write_backup(Path(args.output), include_auth_hashes=args.include_auth_hashes)
    elif args.command == "restore":
        restore_backup(Path(args.input), force=args.force)
    elif args.command == "db-status":
        print_db_status()


if __name__ == "__main__":
    main()
