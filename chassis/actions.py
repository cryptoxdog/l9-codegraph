"""
--- L9_META ---
l9_schema: 1
origin: chassis
engine: "*"
layer: [api]
tags: [chassis, actions, action-router, engine-agnostic]
owner: platform-team
status: active
--- /L9_META ---

chassis/actions.py — Engine-Agnostic Action Router

Receives (action, payload, tenant, trace_id) from chassis/app.py.
Inflates to PacketEnvelope, routes to the engine's registered handler,
deflates the response.

ZERO engine imports. Handlers are registered at startup by the engine's
LifecycleHook via register_handler() / register_handlers().
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# Handler type: async (tenant, payload) -> dict
ActionHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

# Registry — populated by engine at startup
_handlers: dict[str, ActionHandler] = {}

# Optional PacketEnvelope bridge (if the engine uses it)
_inflate_fn: Any = None
_deflate_fn: Any = None

ENGINE_VERSION = "0.0.0"
NODE_NAME = "unknown"


# ── Registration API (called by engine's LifecycleHook.startup) ──────────


def register_handler(action: str, handler: ActionHandler) -> None:
    """Register a single action handler."""
    _handlers[action] = handler
    logger.debug("Registered handler: %s → %s", action, handler.__name__)


def register_handlers(mapping: dict[str, ActionHandler]) -> None:
    """Register multiple action handlers at once."""
    _handlers.update(mapping)
    logger.info("Registered %d action handlers: %s", len(mapping), ", ".join(sorted(mapping)))


def set_packet_bridge(
    inflate: Any,
    deflate: Any,
    *,
    engine_version: str = "0.0.0",
    node_name: str = "engine",
) -> None:
    """
    Optional: wire PacketEnvelope inflate/deflate functions.
    If not called, execute_action still works — it just skips
    the PacketEnvelope layer and calls handlers directly.
    """
    global _inflate_fn, _deflate_fn, ENGINE_VERSION, NODE_NAME
    _inflate_fn = inflate
    _deflate_fn = deflate
    ENGINE_VERSION = engine_version
    NODE_NAME = node_name
    logger.info(
        "Packet bridge wired: inflate=%s, deflate=%s, node=%s",
        inflate.__name__,
        deflate.__name__,
        node_name,
    )


def clear_handlers() -> None:
    """Reset all handlers (for testing)."""
    _handlers.clear()


def list_actions() -> list[str]:
    """Return registered action names (for admin introspection)."""
    return sorted(_handlers.keys())


# ── Execution ────────────────────────────────────────────────────────────


async def execute_action(
    action: str,
    payload: dict[str, Any],
    tenant: str,
    trace_id: str,
) -> dict[str, Any]:
    """
    Chassis entrypoint: POST /v1/execute

    1. (Optional) Inflate → PacketEnvelope
    2. Route to registered handler by action name
    3. Execute handler
    4. (Optional) Deflate → PacketEnvelope
    5. Return canonical response dict
    """
    start_time = time.time()

    # ── Optional: PacketEnvelope inflate ──
    request_packet = None
    if _inflate_fn is not None:
        request_packet = _inflate_fn(
            action=action,
            payload=payload,
            tenant=tenant,
            trace_id=trace_id,
            source_node="chassis",
        )

    # ── Route ──
    handler = _handlers.get(action)
    if not handler:
        available = ", ".join(sorted(_handlers)) or "(none)"
        raise ValueError(f"Unknown action: {action!r}. Available: {available}")

    # ── Execute ──
    try:
        engine_data = await handler(tenant, payload)
        status = "success"
    except Exception as exc:
        logger.exception("Handler %s failed for tenant=%s", action, tenant)
        engine_data = {"error": str(exc)}
        status = "failed"

    # ── Optional: PacketEnvelope deflate ──
    processing_ms = (time.time() - start_time) * 1000
    if _deflate_fn is not None and request_packet is not None:
        _deflate_fn(
            request=request_packet,
            engine_data=engine_data,
            status=status,
            processing_ms=processing_ms,
            engine_version=ENGINE_VERSION,
            responding_node=NODE_NAME,
        )

    return {
        "status": status,
        "action": action,
        "tenant": tenant,
        "data": engine_data,
        "meta": {
            "trace_id": trace_id,
            "execution_ms": processing_ms,
            "version": ENGINE_VERSION,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
