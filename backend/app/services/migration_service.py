from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from ..database import engine


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
ALEMBIC_DIR = BACKEND_ROOT / "alembic"


def current_revision() -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def head_revision() -> str | None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return ScriptDirectory.from_config(config).get_current_head()


def migration_status() -> dict[str, str | None]:
    current = current_revision()
    head = head_revision()
    if current == head:
        status = "up-to-date"
    elif current is None:
        status = "pending"
    else:
        status = "pending"
    return {"current": current, "head": head, "status": status}
