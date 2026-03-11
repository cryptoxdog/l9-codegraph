"""
--- L9_META ---
l9_schema: 1
origin: chassis
engine: "*"
layer: [api]
tags: [chassis, engine-agnostic]
owner: platform-team
status: active
--- /L9_META ---

L9 Chassis — Engine-Agnostic Integration Layer.

Bridges the HTTP boundary to any L9 constellation engine
via the LifecycleHook + action router pattern.
"""

from chassis.actions import execute_action, register_handler, register_handlers
from chassis.app import LifecycleHook, create_app
from chassis.errors import (
    AuthorizationError,
    ChassisError,
    ExecutionError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from chassis.health import HealthAggregator

__all__ = [
    # App factory
    "create_app",
    "LifecycleHook",
    # Action routing
    "execute_action",
    "register_handler",
    "register_handlers",
    # Health
    "HealthAggregator",
    # Errors
    "ChassisError",
    "ValidationError",
    "NotFoundError",
    "AuthorizationError",
    "RateLimitError",
    "ExecutionError",
]
