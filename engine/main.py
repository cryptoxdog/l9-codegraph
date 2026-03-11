# --- L9_META ---
# l9_schema: 1
# layer: [api]
# tags: [fastapi, chassis, entrypoint]
# status: active
# --- /L9_META ---
"""L9 Golden Repo — FastAPI entrypoint. Replace APP_NAME and wire your engine."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from engine.settings import Settings

logger = structlog.get_logger()
settings = Settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": settings.app_name})


@app.post("/v1/execute")
async def execute(payload: dict) -> JSONResponse:
    """Primary action endpoint. action + tenant + payload envelope."""
    action = payload.get("action")
    tenant = payload.get("tenant")
    logger.info("execute", action=action, tenant=tenant)
    # TODO: route to your engine handler
    return JSONResponse({"status": "ok", "action": action, "tenant": tenant})
