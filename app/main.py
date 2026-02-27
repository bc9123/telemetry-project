from fastapi import FastAPI, Depends

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import configure_logging

from app.api.deps import get_db

from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.org import router as orgs_router
from app.api.routes.project import router as projects_router
from app.api.routes.device import router as devices_router
from app.api.routes.api_key import router as api_keys_router
from app.api.routes.rule import router as rules_router
from app.api.routes.alert import router as alerts_router
from app.api.routes.webhook import router as webhook_router
from app.api.routes.webhook_delivery import router as webhook_delivery_router
from app.middlewares.logging import RequestLoggingMiddleware

configure_logging()

# Initialize FastAPI app
app = FastAPI(
    title="Telemetry Platform",
    version="0.1.0",
)

# Middlewares
app.add_middleware(RequestLoggingMiddleware)

# Routers
app.include_router(telemetry_router)
app.include_router(orgs_router)
app.include_router(projects_router)
app.include_router(devices_router)
app.include_router(rules_router)
app.include_router(alerts_router)
app.include_router(api_keys_router)
app.include_router(webhook_router)
app.include_router(webhook_delivery_router)

# Health check endpoints
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}