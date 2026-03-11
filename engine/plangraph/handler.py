# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [plangraph, handler, api]
# status: active
# --- /L9_META ---
"""PlanGraph action handlers — wired into engine/main.py."""

from __future__ import annotations

from pathlib import Path

import structlog

from engine.settings import Settings

logger = structlog.get_logger()
_settings = Settings()

# Domains directory (relative to repo root)
_DOMAINS_DIR = Path(__file__).parent.parent.parent / "domains"


async def handle_search_plangraph(payload: dict) -> dict:
    """Search PlanGraph for a service in a constellation.

    Payload:
        service (str, required): Service name
        constellation (str, required): Constellation identifier
    """
    service = payload.get("service")
    constellation = payload.get("constellation")
    if not service or not constellation:
        return {"error": "search_plangraph requires 'service' and 'constellation'"}

    if not _settings.plangraph_enabled:
        return {"error": "PlanGraph engine is disabled (L9_PLANGRAPH_ENABLED=false)"}

    from .retriever import PlanGraphRetriever

    retriever = PlanGraphRetriever(
        neo4j_uri=_settings.neo4j_uri,
        neo4j_password=_settings.neo4j_password,
        neo4j_user=_settings.neo4j_user,
    )
    try:
        result = retriever.search_service(service=service, constellation=constellation)
        logger.info("plangraph.search", service=service, constellation=constellation)
        return result
    finally:
        retriever.close()


async def handle_build_order(payload: dict) -> dict:
    """Get topological build order for a constellation.

    Payload:
        constellation (str, required): Constellation identifier
    """
    constellation = payload.get("constellation")
    if not constellation:
        return {"error": "build_order requires 'constellation'"}

    if not _settings.plangraph_enabled:
        return {"error": "PlanGraph engine is disabled (L9_PLANGRAPH_ENABLED=false)"}

    from .retriever import PlanGraphRetriever

    retriever = PlanGraphRetriever(
        neo4j_uri=_settings.neo4j_uri,
        neo4j_password=_settings.neo4j_password,
        neo4j_user=_settings.neo4j_user,
    )
    try:
        result = retriever.build_order(constellation=constellation)
        logger.info("plangraph.build_order", constellation=constellation)
        return result
    finally:
        retriever.close()


async def handle_check_drift(payload: dict) -> dict:
    """Check drift between planned constellation and implemented code.

    Payload:
        constellation (str, required): Constellation identifier
        repo (str, required): Repo identifier (owner/name)
        service (str, optional): Single service (omit for all services)
    """
    constellation = payload.get("constellation")
    repo = payload.get("repo")
    if not constellation or not repo:
        return {"error": "check_drift requires 'constellation' and 'repo'"}

    if not _settings.plangraph_enabled:
        return {"error": "PlanGraph engine is disabled (L9_PLANGRAPH_ENABLED=false)"}

    from .drift import DriftDetector

    detector = DriftDetector(
        neo4j_uri=_settings.neo4j_uri,
        neo4j_password=_settings.neo4j_password,
        neo4j_user=_settings.neo4j_user,
    )
    try:
        service = payload.get("service")
        if service:
            result = detector.check_service(service=service, constellation=constellation, repo=repo)
        else:
            result = detector.check_all(constellation=constellation, repo=repo)
        return result
    finally:
        detector.close()


async def handle_load_constellation(payload: dict) -> dict:
    """Load a constellation spec from a YAML file into Neo4j.

    Payload:
        constellation (str, required): Constellation identifier
        spec_file (str, required): YAML filename (relative to domains/<constellation>/)
        spec_dir (str, optional): Override directory path
    """
    constellation = payload.get("constellation")
    spec_file = payload.get("spec_file")
    if not constellation or not spec_file:
        return {"error": "load_constellation requires 'constellation' and 'spec_file'"}

    if not _settings.plangraph_enabled:
        return {"error": "PlanGraph engine is disabled (L9_PLANGRAPH_ENABLED=false)"}

    spec_dir = payload.get("spec_dir") or str(_DOMAINS_DIR / constellation)

    from .builder import PlanGraphBuilder
    from .spec_parser import SpecParser

    parser = SpecParser(spec_dir=spec_dir)
    spec = parser.parse(spec_file)

    if not spec.get("services"):
        return {"error": f"No services found in spec '{spec_file}' at '{spec_dir}'"}

    builder = PlanGraphBuilder(
        neo4j_uri=_settings.neo4j_uri,
        neo4j_password=_settings.neo4j_password,
        constellation=constellation,
        neo4j_user=_settings.neo4j_user,
    )
    try:
        result = builder.load(spec)
        logger.info("plangraph.loaded", constellation=constellation, spec_file=spec_file)
        return {"status": "loaded", **result}
    finally:
        builder.close()
