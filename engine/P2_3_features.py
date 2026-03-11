"""
Feature Flags System — engine/features.py
P2-3 Implementation | Impact: Deployment 40% -> 50%

Usage:
    from engine.features import flags, feature_flag

    # Programmatic check
    if flags.is_enabled("ai_query", user_id="user123"):
        return ai_powered_query(query)

    # Decorator for FastAPI endpoints
    @router.post("/v1/experimental/ai-query")
    @feature_flag("ai_query")
    async def ai_query_endpoint(query: str, user_id: str):
        ...
"""

import json
import hashlib
import os
from pathlib import Path
from typing import Optional, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("FEATURE_FLAGS_PATH", "config/features.json")
        self._flags: dict[str, Any] = self._load()
        logger.info("Loaded %d feature flags from %s", len(self._flags), self.config_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        path = Path(self.config_path)
        if not path.exists():
            logger.warning("Feature flags file not found: %s", self.config_path)
            return {}
        try:
            with open(path) as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load feature flags: %s", exc)
            return {}

    def reload(self) -> None:
        """Hot-reload flags from disk (no restart needed)."""
        self._flags = self._load()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def is_enabled(
        self,
        name: str,
        *,
        user_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        default: bool = False,
    ) -> bool:
        """
        Check whether *name* is enabled for the given user / context.

        Evaluation order:
        1. Flag exists and ``enabled`` is True
        2. Environment restriction (optional)
        3. User blocklist
        4. User allowlist (overrides percentage)
        5. Percentage rollout (deterministic hash)
        6. Context-based rules
        """
        cfg = self._flags.get(name)
        if cfg is None:
            return default

        if not cfg.get("enabled", False):
            return False

        # Environment gate
        envs = cfg.get("environments")
        if envs and os.getenv("ENVIRONMENT", "production") not in envs:
            return False

        # Blocklist
        if user_id and user_id in cfg.get("blocked_users", []):
            return False

        # Allowlist (bypass percentage)
        if "allowed_users" in cfg:
            if user_id and user_id in cfg["allowed_users"]:
                return True
            if user_id:
                return False  # not in allowlist -> off

        # Percentage rollout
        pct = cfg.get("rollout_percentage", 100)
        if pct < 100 and user_id:
            bucket = (
                int.from_bytes(hashlib.sha256(f"{name}:{user_id}".encode()).digest()[:4], "big")
                % 100
            )
            if bucket >= pct:
                return False

        # Context rules
        if context and "rules" in cfg:
            return self._eval_rules(cfg["rules"], context)

        return True

    # ------------------------------------------------------------------
    # Rule engine
    # ------------------------------------------------------------------

    _OPS = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "in": lambda a, b: a in b,
    }

    def _eval_rules(self, rules: list[dict], ctx: dict) -> bool:
        for rule in rules:
            field = rule.get("field", "")
            if field not in ctx:
                return False
            op_fn = self._OPS.get(rule.get("operator", ""))
            if op_fn is None or not op_fn(ctx[field], rule.get("value")):
                return False
        return True

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------

    def all_flags(self) -> dict[str, Any]:
        return self._flags.copy()


# Global singleton
flags = FeatureFlags()


def feature_flag(name: str, *, user_field: str = "user_id"):
    """FastAPI decorator — returns 404 when flag is off."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            uid = kwargs.get(user_field)
            if not flags.is_enabled(name, user_id=uid):
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="Feature not available")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
