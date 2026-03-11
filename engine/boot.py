# --- L9_META ---
# l9_schema: 1
# layer: [api]
# tags: [chassis, lifecycle, boot]
# status: active
# --- /L9_META ---
"""engine/boot.py — CodegraphLifecycle: chassis LifecycleHook for l9-codegraph."""
from __future__ import annotations

import logging
from typing import Any

from chassis.chassis_app import LifecycleHook
from engine.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class CodegraphLifecycle(LifecycleHook):
    """Wires Neo4j connections for CodeGraph + PlanGraph engines."""

    def __init__(self) -> None:
        self._driver: Any = None

    async def startup(self) -> None:
        logger.info("CodegraphLifecycle.startup — Neo4j: %s", settings.neo4j_uri)
        # Import here to avoid loading neo4j at module level (keeps tests fast)
        from neo4j import AsyncGraphDatabase
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("CodegraphLifecycle.startup complete")

    async def shutdown(self) -> None:
        if self._driver:
            await self._driver.close()
        logger.info("CodegraphLifecycle.shutdown complete")

    async def execute(
        self,
        action: str,
        payload: dict[str, Any],
        tenant: str,
        trace_id: str,
    ) -> dict[str, Any]:
        logger.info("execute action=%s tenant=%s trace_id=%s", action, tenant, trace_id)
        # Inject tenant + trace_id into payload so handlers can log them
        enriched = {**payload, "tenant": tenant, "trace_id": trace_id}

        try:
            if action == "search_codegraph":
                from engine.codegraph.handler import handle_search_codegraph
                data = await handle_search_codegraph(enriched)
            elif action == "build_codegraph":
                from engine.codegraph.handler import handle_build_codegraph
                data = await handle_build_codegraph(enriched)
            elif action == "search_plangraph":
                from engine.plangraph.handler import handle_search_plangraph
                data = await handle_search_plangraph(enriched)
            elif action == "build_order":
                from engine.plangraph.handler import handle_build_order
                data = await handle_build_order(enriched)
            elif action == "check_drift":
                from engine.plangraph.handler import handle_check_drift
                data = await handle_check_drift(enriched)
            elif action == "load_constellation":
                from engine.plangraph.handler import handle_load_constellation
                data = await handle_load_constellation(enriched)
            elif action == "health":
                data = {"status": "healthy", "service": "l9-codegraph"}
            else:
                return {
                    "status": "failed",
                    "action": action,
                    "tenant": tenant,
                    "data": {"error": f"Unknown action: '{action}'"},
                    "meta": {"trace_id": trace_id},
                }
        except Exception as exc:
            logger.exception("Handler failed action=%s: %s", action, exc)
            return {
                "status": "failed",
                "action": action,
                "tenant": tenant,
                "data": {"error": str(exc)},
                "meta": {"trace_id": trace_id},
            }

        return {
            "status": "ok",
            "action": action,
            "tenant": tenant,
            "data": data,
            "meta": {"trace_id": trace_id},
        }
