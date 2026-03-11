# --- L9_META ---
# l9_schema: 1
# layer: [api]
# tags: [fastapi, chassis, entrypoint]
# status: active
# --- /L9_META ---
"""l9-codegraph — FastAPI entrypoint. CodeGraph + PlanGraph dual-engine."""

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
    """Primary action endpoint. action + tenant + payload envelope.

    Actions:
        search_codegraph   — ego-graph search for a function/class in a repo
        build_codegraph    — clone repo + rebuild CodeGraph
        search_plangraph   — neighborhood search for a service
        build_order        — topological build order for a constellation
        check_drift        — compare planned vs implemented
        load_constellation — load a YAML spec into PlanGraph
    """
    action = payload.get("action")
    tenant = payload.get("tenant")
    logger.info("execute", action=action, tenant=tenant)

    if action == "search_codegraph":
        from engine.codegraph.handler import handle_search_codegraph

        result = await handle_search_codegraph(payload)
        return JSONResponse({"status": "ok", "action": action, "result": result})

    elif action == "build_codegraph":
        from engine.codegraph.handler import handle_build_codegraph

        result = await handle_build_codegraph(payload)
        return JSONResponse({"status": "ok", "action": action, "result": result})

    elif action == "search_plangraph":
        from engine.plangraph.handler import handle_search_plangraph

        result = await handle_search_plangraph(payload)
        return JSONResponse({"status": "ok", "action": action, "result": result})

    elif action == "build_order":
        from engine.plangraph.handler import handle_build_order

        result = await handle_build_order(payload)
        return JSONResponse({"status": "ok", "action": action, "result": result})

    elif action == "check_drift":
        from engine.plangraph.handler import handle_check_drift

        result = await handle_check_drift(payload)
        return JSONResponse({"status": "ok", "action": action, "result": result})

    elif action == "load_constellation":
        from engine.plangraph.handler import handle_load_constellation

        result = await handle_load_constellation(payload)
        return JSONResponse({"status": "ok", "action": action, "result": result})

    else:
        return JSONResponse(
            {"status": "error", "error": f"Unknown action: '{action}'"},
            status_code=400,
        )
