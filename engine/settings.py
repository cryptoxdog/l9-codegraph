# --- L9_META ---
# l9_schema: 1
# layer: [config]
# tags: [settings, config, neo4j]
# status: active
# --- /L9_META ---
"""l9-codegraph settings — all env-driven."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "l9-codegraph"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    port: int = int(os.getenv("PORT", "8002"))
    neo4j_uri: str = os.getenv("NEO4J_BOLT_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    codegraph_enabled: bool = os.getenv("L9_CODEGRAPH_ENABLED", "true").lower() == "true"
    plangraph_enabled: bool = os.getenv("L9_PLANGRAPH_ENABLED", "true").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"
