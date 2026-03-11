# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [codegraph, retriever, ego-graph]
# status: active
# --- /L9_META ---
"""EgoGraphRetriever — pure Cypher, no APOC.

Returns ego-graphs (1–2 hop neighborhoods) for a given term + repo.
"""

from __future__ import annotations

import structlog
from neo4j import GraphDatabase

logger = structlog.get_logger()


class EgoGraphRetriever:
    """Retrieve ego-graphs from CodeDef/INVOKES graph.

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

    def search(self, term: str, repo: str, hops: int = 1) -> dict:
        """Return ego-graph for `term` in `repo` with up to `hops` traversals.

        Args:
            term: Function or class name to look up
            repo: Repo identifier (e.g. "owner/name")
            hops: 1 or 2 (clamped)

        Returns:
            {nodes, edges, flat_text}
        """
        hops = min(max(hops, 1), 2)
        with self.driver.session() as s:
            center = s.run(
                "MATCH (c:CodeDef {name: $t, repo: $r}) RETURN c LIMIT 1",
                t=term,
                r=repo,
            ).single()
            if not center:
                return {
                    "nodes": [],
                    "edges": [],
                    "flat_text": f"No results for '{term}' in '{repo}'",
                }
            center_node = dict(center["c"])

            neighbors_result = s.run(
                "MATCH (c:CodeDef {name: $t, repo: $r})-[:INVOKES*1..$h]-(n:CodeDef {repo: $r})"
                " RETURN DISTINCT n",
                t=term,
                r=repo,
                h=hops,
            )
            neighbor_nodes = [dict(r["n"]) for r in neighbors_result]

            all_names = {center_node["name"]} | {n["name"] for n in neighbor_nodes}
            edges_result = s.run(
                "MATCH (a:CodeDef {repo: $r})-[:INVOKES]->(b:CodeDef {repo: $r})"
                " WHERE a.name IN $names AND b.name IN $names"
                " RETURN DISTINCT a.name AS fn, b.name AS tn",
                r=repo,
                names=list(all_names),
            )
            edge_list = [{"from": e["fn"], "to": e["tn"], "type": "INVOKES"} for e in edges_result]

            nodes = [center_node] + neighbor_nodes
            return {
                "nodes": nodes,
                "edges": edge_list,
                "flat_text": self._flatten(nodes, edge_list, term, repo),
            }

    def _flatten(
        self,
        nodes: list[dict],
        edges: list[dict],
        term: str,
        repo: str,
    ) -> str:
        """Produce a token-efficient text representation of the ego-graph."""
        lines = [f"# CodeGraph ego-graph: '{term}' in '{repo}'"]
        lines.append(f"Nodes ({len(nodes)}):")
        for n in nodes:
            marker = " [CENTER]" if n.get("name") == term else ""
            lang = n.get("language", "?")
            file_ = n.get("file", "?")
            lines.append(f"  - {n['name']} ({lang}) @ {file_}{marker}")
        lines.append(f"Edges ({len(edges)}):")
        for e in edges:
            lines.append(f"  - {e['from']} -> {e['to']}")
        return "\n".join(lines)
