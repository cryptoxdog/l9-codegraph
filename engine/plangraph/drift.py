# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [plangraph, drift, validation]
# status: active
# --- /L9_META ---
"""DriftDetector — compares planned service graph vs actual CodeDef nodes."""

from __future__ import annotations

import structlog
from neo4j import GraphDatabase

logger = structlog.get_logger()


class DriftDetector:
    """Detect drift between planned constellation and implemented code.

    Args:
        neo4j_uri: Bolt URI
        neo4j_password: Neo4j password
        neo4j_user: Neo4j username (default: neo4j)
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_password: str,
        neo4j_user: str = "neo4j",
    ) -> None:
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def close(self) -> None:
        self.driver.close()

    def check_service(self, service: str, constellation: str, repo: str) -> dict:
        """Check drift for a single service.

        Uses explicit `repo` param for CodeDef lookup — no fragile filename inference.

        Args:
            service: Service name in the constellation
            constellation: Constellation identifier
            repo: Repo identifier for CodeDef lookup (e.g. "owner/name")

        Returns:
            DriftResult-like dict
        """
        with self.driver.session() as s:
            # Get planned status
            svc_rec = s.run(
                "MATCH (n:PlanService {name: $svc, constellation: $c}) RETURN n LIMIT 1",
                svc=service,
                c=constellation,
            ).single()

            if not svc_rec:
                return {
                    "service": service,
                    "constellation": constellation,
                    "repo": repo,
                    "planned_status": "unknown",
                    "implemented_functions": [],
                    "is_implemented": False,
                    "drift_score": 1.0,
                    "notes": f"Service '{service}' not found in constellation '{constellation}'",
                }

            svc_node = dict(svc_rec["n"])
            planned_status = svc_node.get("status", "planned")

            # Look for CodeDef nodes in the repo that match this service name
            # Strategy: look for defs whose name contains the service name (case-insensitive)
            # and who belong to the specified repo
            service_lower = service.lower()
            code_rec = s.run(
                """
                MATCH (n:CodeDef {repo: $repo})
                WHERE toLower(n.name) CONTAINS $svc_lower
                   OR toLower(n.file) CONTAINS $svc_lower
                RETURN n.name AS name, n.file AS file
                LIMIT 50
                """,
                repo=repo,
                svc_lower=service_lower,
            )
            implemented_functions = [r["name"] for r in code_rec]
            is_implemented = len(implemented_functions) > 0

            # Drift score: 0.0 = perfect alignment, 1.0 = total drift
            if planned_status in ("built", "deployed"):
                drift_score = 0.0 if is_implemented else 0.8
            elif planned_status == "in_progress":
                drift_score = 0.0 if is_implemented else 0.4
            else:
                # planned — not implemented yet is expected
                drift_score = 0.0

            notes = ""
            if planned_status in ("built", "deployed") and not is_implemented:
                notes = (
                    f"Service marked '{planned_status}' but no matching "
                    f"CodeDef found in repo '{repo}'"
                )
            elif is_implemented:
                notes = f"Found {len(implemented_functions)} matching function(s) in repo"

            return {
                "service": service,
                "constellation": constellation,
                "repo": repo,
                "planned_status": planned_status,
                "implemented_functions": implemented_functions,
                "is_implemented": is_implemented,
                "drift_score": drift_score,
                "notes": notes,
            }

    def check_all(self, constellation: str, repo: str) -> dict:
        """Check drift for all services in a constellation.

        Args:
            constellation: Constellation identifier
            repo: Repo identifier for CodeDef lookup

        Returns:
            {constellation, repo, results: [...], summary: {...}}
        """
        with self.driver.session() as s:
            services_rec = s.run(
                "MATCH (n:PlanService {constellation: $c}) RETURN n.name AS name",
                c=constellation,
            )
            service_names = [r["name"] for r in services_rec]

        results = [self.check_service(svc, constellation, repo) for svc in service_names]

        drifted = [r for r in results if r["drift_score"] > 0.0]
        avg_drift = sum(r["drift_score"] for r in results) / len(results) if results else 0.0

        logger.info(
            "plangraph.drift_check",
            constellation=constellation,
            repo=repo,
            services=len(results),
            drifted=len(drifted),
            avg_drift=round(avg_drift, 3),
        )

        return {
            "constellation": constellation,
            "repo": repo,
            "results": results,
            "summary": {
                "total": len(results),
                "drifted": len(drifted),
                "clean": len(results) - len(drifted),
                "avg_drift_score": round(avg_drift, 3),
            },
        }
