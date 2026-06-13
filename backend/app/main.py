from fastapi import FastAPI

from .routers.admin_ops import router as admin_ops_router
from .routers.api import APP_VERSION, router as api_router
from .setup import router as setup_router
from .services.diagnostics_service import record_event
from .services.migration_service import migration_status


app = FastAPI(title="API синхронизации списка покупок", version=APP_VERSION)
app.include_router(setup_router)
app.include_router(api_router)
app.include_router(admin_ops_router)


@app.on_event("startup")
def log_startup_state() -> None:
    try:
        status = migration_status()
        details = f"current={status['current']} head={status['head']} status={status['status']}"
        record_event("migration status", details, "warning" if status["status"] != "up-to-date" else "info")
    except Exception as exc:
        record_event("migration status error", exc.__class__.__name__, "error")
