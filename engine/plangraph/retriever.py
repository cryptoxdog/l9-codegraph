# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [plangraph, retriever, topology]
# status: active
# --- /L9_META ---
"""PlanGraph retriever — service search and topological build order.

Pure Cypher only, no APOC.
"""

from __future__ import annotations

from collections import deque

import structlog
from neo4j import GraphDatabase

logger = structlog.get_logger()


class PlanGraphRetriever:
    """Query PlanGraph for service neighborhoods and build order.

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

    def search_service(self, service: str, constellation: str) -> dict:
        """Return service node + neighbors (DEPENDS_ON, FLOWS_TO, FEEDS_BACK_TO).

        Args:
            service: Service name
            constellation: Constellation identifier

        Returns:
            {service, nodes, edges, flat_text}
        """
        with self.driver.session() as s:
            center_rec = s.run(
                "MATCH (n:PlanService {name: $svc, constellation: $c}) RETURN n LIMIT 1",
                svc=service,
                c=constellation,
            ).single()
            if not center_rec:
                msg = f"Service '{service}' not found in constellation '{constellation}'"
                return {"service": service, "nodes": [], "edges": [], "flat_text": msg}
            center = dict(center_rec["n"])

            dep_result = s.run(
                """
                MATCH (a:PlanService {name: $svc, constellation: $c})
                      -[r:DEPENDS_ON|FLOWS_TO|FEEDS_BACK_TO]-
                      (b:PlanService {constellation: $c})
                RETURN b, type(r) AS rel_type,
                       startNode(r).name AS rel_from,
                       endNode(r).name AS rel_to
                """,
                svc=service,
                c=constellation,
            )
            neighbor_nodes = []
            edge_list = []
            seen_names: set[str] = {center["name"]}
            for rec in dep_result:
                n = dict(rec["b"])
                if n["name"] not in seen_names:
                    neighbor_nodes.append(n)
                    seen_names.add(n["name"])
                edge_list.append(
                    {
                        "from": rec["rel_from"],
                        "to": rec["rel_to"],
                        "type": rec["rel_type"],
                    }
                )

            nodes = [center] + neighbor_nodes
            flat_text = self._flatten_service(center, nodes, edge_list)
            return {"service": service, "nodes": nodes, "edges": edge_list, "flat_text": flat_text}

    def build_order(self, constellation: str) -> dict:
        """Compute topological build order for a constellation.

        Returns:
            {constellation, topological_order, parallel_groups, flat_text}
        """
        with self.driver.session() as s:
            services_rec = s.run(
                "MATCH (n:PlanService {constellation: $c}) RETURN n",
                c=constellation,
            )
            services = [dict(r["n"]) for r in services_rec]

            deps_rec = s.run(
                """
                MATCH (a:PlanService {constellation: $c})
                      -[:DEPENDS_ON]->
                      (b:PlanService {constellation: $c})
                RETURN a.name AS dependent, b.name AS dependency
                """,
                c=constellation,
            )
            dep_map: dict[str, list[str]] = {svc["name"]: [] for svc in services}
            for rec in deps_rec:
                dep_map[rec["dependent"]].append(rec["dependency"])

        topo, groups = self._topological_sort(dep_map)
        flat_text = self._flatten_build_order(constellation, topo, groups)
        return {
            "constellation": constellation,
            "topological_order": topo,
            "parallel_groups": groups,
            "flat_text": flat_text,
        }

    def _topological_sort(self, dep_map: dict[str, list[str]]) -> tuple[list[str], list[list[str]]]:
        """Kahn's algorithm — returns (flat order, parallel groups).

        dep_map: {service_name: [dependencies]}
        """
        # in_degree = number of unresolved dependencies per node
        in_degree = {n: len(deps) for n, deps in dep_map.items()}
        dependents = self._build_dependents(dep_map)
        queue: deque[str] = deque(sorted(n for n, d in in_degree.items() if d == 0))
        topo: list[str] = []
        groups: list[list[str]] = []

        while queue:
            level = list(queue)
            queue.clear()
            groups.append(sorted(level))
            topo.extend(sorted(level))
            for node in level:
                for dep_node in dependents.get(node, []):
                    in_degree[dep_node] -= 1
                    if in_degree[dep_node] == 0:
                        queue.append(dep_node)

        remaining = sorted(n for n in in_degree if n not in topo)
        if remaining:
            logger.warning("plangraph.cycle_detected", nodes=remaining)
            topo.extend(remaining)
            groups.append(remaining)

        return topo, groups

    def _build_dependents(self, dep_map: dict[str, list[str]]) -> dict[str, list[str]]:
        """Build reverse mapping: node -> list of nodes that depend on it."""
        dependents: dict[str, list[str]] = {n: [] for n in dep_map}
        for node, deps in dep_map.items():
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = []
                dependents[dep].append(node)
        return dependents

    def _flatten_service(self, center: dict, nodes: list[dict], edges: list[dict]) -> str:
        lines = [f"# PlanGraph: service '{center['name']}' ({center.get('status', '?')})"]
        lines.append(f"Neighbors ({len(nodes) - 1}):")
        for n in nodes[1:]:
            lines.append(f"  - {n['name']} [{n.get('status', '?')}]")
        lines.append(f"Edges ({len(edges)}):")
        for e in edges:
            lines.append(f"  - {e['from']} -[{e['type']}]-> {e['to']}")
        return "\n".join(lines)

    def _flatten_build_order(
        self, constellation: str, topo: list[str], groups: list[list[str]]
    ) -> str:
        lines = [f"# Build order for constellation '{constellation}'"]
        for i, group in enumerate(groups, 1):
            lines.append(f"Wave {i} (parallel): {', '.join(group)}")
        lines.append(f"Full order: {' -> '.join(topo)}")
        return "\n".join(lines)
