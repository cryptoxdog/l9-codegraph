# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [codegraph, handler, api]
# status: active
# --- /L9_META ---
"""CodeGraph action handlers — wired into engine/main.py."""

from __future__ import annotations

import tempfile
from pathlib import Path

import structlog

from engine.settings import Settings

logger = structlog.get_logger()
_settings = Settings()


async def handle_search_codegraph(payload: dict) -> dict:
    """Search CodeGraph for a term in a repo.

    Payload:
        term (str, required): Function or class name
        repo (str, required): "owner/name" repo identifier
        hops (int, optional): 1 or 2 (default: 1)
    """
    term = payload.get("term")
    repo = payload.get("repo")
    if not term or not repo:
        return {"error": "search_codegraph requires 'term' and 'repo'"}

    hops = int(payload.get("hops", 1))

    if not _settings.codegraph_enabled:
        return {"error": "CodeGraph engine is disabled (L9_CODEGRAPH_ENABLED=false)"}

    from .retriever import EgoGraphRetriever

    retriever = EgoGraphRetriever(
        neo4j_uri=_settings.neo4j_uri,
        neo4j_password=_settings.neo4j_password,
        neo4j_user=_settings.neo4j_user,
    )
    try:
        result = retriever.search(term=term, repo=repo, hops=hops)
        logger.info("codegraph.search", term=term, repo=repo, hops=hops, nodes=len(result["nodes"]))
        return result
    finally:
        retriever.close()


async def handle_build_codegraph(payload: dict) -> dict:
    """Clone a GitHub repo and build its CodeGraph.

    Payload:
        repo (str, required): "owner/name" format
        branch (str, optional): branch to clone (default: main)
    """
    repo = payload.get("repo")
    if not repo:
        return {"error": "build_codegraph requires 'repo' (format: owner/name)"}

    branch = payload.get("branch", "main")

    if not _settings.codegraph_enabled:
        return {"error": "CodeGraph engine is disabled (L9_CODEGRAPH_ENABLED=false)"}

    from .builder import CodeGraphBuilder

    token = _settings.github_token
    if token:
        clone_url = f"https://{token}@github.com/{repo}.git"
    else:
        clone_url = f"https://github.com/{repo}.git"

    with tempfile.TemporaryDirectory(prefix="l9-codegraph-") as tmpdir:
        clone_path = Path(tmpdir) / "repo"
        try:
            import git

            logger.info("codegraph.clone", repo=repo, branch=branch)
            git.Repo.clone_from(clone_url, str(clone_path), branch=branch, depth=1)
        except Exception as e:
            logger.error("codegraph.clone_failed", repo=repo, error=str(e))
            return {"error": f"Clone failed: {e}"}

        builder = CodeGraphBuilder(
            neo4j_uri=_settings.neo4j_uri,
            neo4j_password=_settings.neo4j_password,
            repo_root=str(clone_path),
            repo=repo,
            neo4j_user=_settings.neo4j_user,
        )
        try:
            result = builder.build()
        except Exception as e:
            logger.error("codegraph.build_failed", repo=repo, error=str(e))
            return {"error": f"Build failed: {e}"}
        finally:
            builder.close()

    return {"status": "built", **result}
