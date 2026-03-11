# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [plangraph, builder, neo4j]
# status: active
# --- /L9_META ---
"""PlanGraph builder — writes constellation service graph to Neo4j."""

from __future__ import annotations

import structlog
from neo4j import GraphDatabase

logger = structlog.get_logger()


class PlanGraphBuilder:
    """Build a service constellation graph in Neo4j.

    Args:
        neo4j_uri: Bolt URI
        neo4j_password: Neo4j password
        constellation: Constellation name (isolation key)
        neo4j_user: Neo4j username (default: neo4j)
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_password: str,
        constellation: str,
        neo4j_user: str = "neo4j",
    ) -> None:
        self.constellation = constellation
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def close(self) -> None:
        self.driver.close()

    def load(self, spec: dict) -> dict:
        """Load a parsed spec dict into Neo4j.

        Args:
            spec: {services, interfaces, flows} from SpecParser.parse()

        Returns:
            {constellation, services, interfaces, flows}
        """
        self._ensure_indexes()
        self._clear()

        services = spec.get("services", [])
        interfaces = spec.get("interfaces", [])
        flows = spec.get("flows", [])

        with self.driver.session() as session:
            # Write PlanService nodes
            for svc in services:
                session.run(
                    """
                    MERGE (s:PlanService {name: $name, constellation: $c})
                    SET s.status = $status,
                        s.description = $desc,
                        s.updated = timestamp()
                    """,
                    name=svc["name"],
                    c=self.constellation,
                    status=svc.get("status", "planned"),
                    desc=svc.get("description", ""),
                )

            # Write DEPENDS_ON edges
            for svc in services:
                for dep in svc.get("depends_on", []):
                    session.run(
                        """
                        MATCH (a:PlanService {name: $name, constellation: $c})
                        MERGE (b:PlanService {name: $dep, constellation: $c})
                        ON CREATE SET b.status = 'planned', b.updated = timestamp()
                        MERGE (a)-[:DEPENDS_ON]->(b)
                        """,
                        name=svc["name"],
                        dep=dep,
                        c=self.constellation,
                    )

            # Write PlanInterface nodes + EXPOSES edges
            for iface in interfaces:
                session.run(
                    """
                    MERGE (i:PlanInterface {name: $iname, constellation: $c})
                    SET i.direction = $direction,
                        i.protocol = $protocol,
                        i.description = $desc,
                        i.updated = timestamp()
                    WITH i
                    MATCH (s:PlanService {name: $svc, constellation: $c})
                    MERGE (s)-[:EXPOSES]->(i)
                    """,
                    iname=iface["name"],
                    c=self.constellation,
                    direction=iface.get("direction", "inbound"),
                    protocol=iface.get("protocol", "http"),
                    desc=iface.get("description", ""),
                    svc=iface.get("service", ""),
                )

            # Write FLOWS_TO / FEEDS_BACK_TO edges
            for flow in flows:
                from_svc = flow.get("from", "")
                to_svc = flow.get("to", "")
                label = flow.get("label", "")
                feedback = flow.get("feedback", False)
                rel_type = "FEEDS_BACK_TO" if feedback else "FLOWS_TO"
                session.run(
                    f"""
                    MATCH (a:PlanService {{name: $from_s, constellation: $c}})
                    MATCH (b:PlanService {{name: $to_s, constellation: $c}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r.label = $label
                    """,
                    from_s=from_svc,
                    to_s=to_svc,
                    c=self.constellation,
                    label=label,
                )

        logger.info(
            "plangraph.loaded",
            constellation=self.constellation,
            services=len(services),
            interfaces=len(interfaces),
            flows=len(flows),
        )
        return {
            "constellation": self.constellation,
            "services": len(services),
            "interfaces": len(interfaces),
            "flows": len(flows),
        }

    def _clear(self) -> None:
        """Delete all nodes for this constellation only."""
        with self.driver.session() as session:
            session.run(
                "MATCH (n:PlanService {constellation: $c}) DETACH DELETE n",
                c=self.constellation,
            )
            session.run(
                "MATCH (n:PlanInterface {constellation: $c}) DETACH DELETE n",
                c=self.constellation,
            )
        logger.info("plangraph.cleared", constellation=self.constellation)

    def _ensure_indexes(self) -> None:
        with self.driver.session() as session:
            try:
                session.run(
                    "CREATE INDEX planservice_constellation IF NOT EXISTS "
                    "FOR (n:PlanService) ON (n.constellation, n.name)"
                )
                session.run(
                    "CREATE INDEX planiface_constellation IF NOT EXISTS "
                    "FOR (n:PlanInterface) ON (n.constellation, n.name)"
                )
            except Exception as e:
                logger.debug("plangraph_index_skip", error=str(e))
