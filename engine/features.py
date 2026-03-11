"""
Feature Flags System
P2-3 Implementation: Basic JSON-based feature flags with rollout control

Features:
- Global enable/disable per flag
- Percentage rollout (deterministic user hashing)
- User allowlist/blocklist
- Environment-specific flags
- Zero dependencies (stdlib only)

Usage:
    from engine.features import feature_flags, feature_flag

    # Check if feature is enabled for user
    if feature_flags.is_enabled("ai_query", user_id="user123"):
        return ai_powered_query(query)

    # Decorator for API endpoints
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
    """Feature flag manager with rollout controls."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize feature flags from JSON config.

        Args:
            config_path: Path to features.json (default: config/features.json)
        """
        self.config_path = config_path or os.getenv("FEATURE_FLAGS_PATH", "config/features.json")
        self._flags = self._load_flags()
        logger.info(f"Loaded {len(self._flags)} feature flags from {self.config_path}")

    def _load_flags(self) -> dict[str, Any]:
        """Load feature flags from JSON file."""
        try:
            path = Path(self.config_path)
            if not path.exists():
                logger.warning(f"Feature flags file not found: {self.config_path}")
                return {}

            with open(path) as f:
                flags = json.load(f)

            # Validate structure
            for flag_name, config in flags.items():
                if not isinstance(config, dict):
                    logger.error(f"Invalid config for flag '{flag_name}': must be dict")
                    continue

                if "enabled" not in config:
                    logger.warning(f"Flag '{flag_name}' missing 'enabled' field")

            return flags

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse feature flags JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load feature flags: {e}")
            return {}

    def reload(self) -> None:
        """Reload flags from disk (for runtime updates)."""
        self._flags = self._load_flags()
        logger.info("Feature flags reloaded")

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        context: Optional[dict] = None,
        default: bool = False,
    ) -> bool:
        """
        Check if feature is enabled for given user/context.

        Args:
            flag_name: Name of feature flag
            user_id: User identifier (for percentage rollout)
            context: Additional context (e.g., {"org_id": "123", "plan": "enterprise"})
            default: Default value if flag doesn't exist

        Returns:
            True if feature should be enabled

        Example:
            if feature_flags.is_enabled("new_dashboard", user_id="user@example.com"):
                return render_new_dashboard()
        """
        # Check if flag exists
        if flag_name not in self._flags:
            logger.debug(f"Flag '{flag_name}' not found, using default: {default}")
            return default

        flag_config = self._flags[flag_name]

        # 1. Check global enable/disable
        if not flag_config.get("enabled", False):
            return False

        # 2. Check environment restrictions
        current_env = os.getenv("ENVIRONMENT", "production")
        allowed_envs = flag_config.get("environments")
        if allowed_envs and current_env not in allowed_envs:
            logger.debug(
                f"Flag '{flag_name}' not enabled in environment '{current_env}' "
                f"(allowed: {allowed_envs})"
            )
            return False

        # 3. Check user blocklist
        if user_id and "blocked_users" in flag_config:
            if user_id in flag_config["blocked_users"]:
                return False

        # 4. Check user allowlist (overrides everything else)
        if user_id and "allowed_users" in flag_config:
            return user_id in flag_config["allowed_users"]

        # 5. Check percentage rollout (deterministic based on user_id hash)
        rollout_pct = flag_config.get("rollout_percentage", 100)
        if rollout_pct < 100 and user_id:
            user_bucket = self._hash_user_to_bucket(user_id, flag_name)
            if user_bucket >= rollout_pct:
                return False

        # 6. Context-based rules (extensible)
        if context and "rules" in flag_config:
            return self._evaluate_rules(flag_config["rules"], context)

        return True

    def _hash_user_to_bucket(self, user_id: str, flag_name: str) -> int:
        """
        Hash user ID to deterministic bucket 0-99.

        Same user always gets same bucket for same flag (stable rollout).
        Different flags get different buckets (independent experiments).
        """
        # Use flag_name as salt for independent rollouts
        hash_input = f"{flag_name}:{user_id}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        # Take first 4 bytes as int, mod 100
        bucket = int.from_bytes(hash_bytes[:4], "big") % 100
        return bucket

    def _evaluate_rules(self, rules: list[dict], context: dict) -> bool:
        """
        Evaluate context-based rules.

        Example rules:
            [
                {"field": "plan", "operator": "eq", "value": "enterprise"},
                {"field": "org_size", "operator": "gte", "value": 100}
            ]
        """
        for rule in rules:
            field = rule.get("field")
            operator = rule.get("operator")
            expected = rule.get("value")

            if field not in context:
                return False

            actual = context[field]

            if operator == "eq" and actual != expected:
                return False
            elif operator == "ne" and actual == expected:
                return False
            elif operator == "gt" and actual <= expected:
                return False
            elif operator == "gte" and actual < expected:
                return False
            elif operator == "lt" and actual >= expected:
                return False
            elif operator == "lte" and actual > expected:
                return False
            elif operator == "in" and actual not in expected:
                return False

        return True

    def get_all_flags(self) -> dict[str, Any]:
        """Get all flag configurations (for debugging/admin UI)."""
        return self._flags.copy()


# Global instance
feature_flags = FeatureFlags()


# Decorator for FastAPI endpoints
def feature_flag(flag_name: str, user_id_field: str = "user_id"):
    """
    Decorator to protect API endpoints with feature flag.

    Args:
        flag_name: Name of feature flag
        user_id_field: Field name in function args containing user ID

    Usage:
        @router.post("/v1/experimental/ai-query")
        @feature_flag("ai_query")
        async def ai_query_endpoint(query: str, user_id: str):
            return {"result": "..."}

    If flag is disabled, returns 404.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from kwargs
            user_id = kwargs.get(user_id_field)

            if not feature_flags.is_enabled(flag_name, user_id=user_id):
                # Import here to avoid circular dependency
                from fastapi import HTTPException

                logger.info(f"Feature '{flag_name}' disabled for user '{user_id}', returning 404")
                raise HTTPException(status_code=404, detail=f"Feature not available")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Admin endpoint to reload flags without restart
async def reload_feature_flags():
    """
    Reload feature flags from disk.

    Usage in FastAPI:
        @router.post("/admin/features/reload")
        @require_admin
        async def reload_flags():
            from engine.features import reload_feature_flags
            await reload_feature_flags()
            return {"status": "reloaded"}
    """
    feature_flags.reload()
    return {"status": "reloaded", "count": len(feature_flags.get_all_flags())}
