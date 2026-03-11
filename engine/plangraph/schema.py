# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [plangraph, schema, pydantic]
# status: active
# --- /L9_META ---
"""PlanGraph Pydantic v2 models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ServiceStatus(StrEnum):
    planned = "planned"
    in_progress = "in_progress"
    built = "built"
    deployed = "deployed"


class InterfaceDirection(StrEnum):
    inbound = "inbound"
    outbound = "outbound"


class PlanServiceNode(BaseModel):
    name: str
    constellation: str
    status: ServiceStatus = ServiceStatus.planned
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanInterfaceNode(BaseModel):
    name: str
    constellation: str
    service: str
    direction: InterfaceDirection
    protocol: str = "http"
    description: str = ""


class PlanDataFlowEdge(BaseModel):
    from_service: str
    to_service: str
    constellation: str
    label: str = ""
    feedback: bool = False


class DriftResult(BaseModel):
    service: str
    constellation: str
    repo: str
    planned_status: ServiceStatus
    implemented_functions: list[str] = Field(default_factory=list)
    is_implemented: bool = False
    drift_score: float = 0.0
    notes: str = ""
