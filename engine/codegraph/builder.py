# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [codegraph, builder, neo4j]
# status: active
# --- /L9_META ---
"""CodeGraph builder — parses repo AST and writes CodeDef/CodeRef graph to Neo4j."""

from __future__ import annotations

import structlog
from neo4j import GraphDatabase

from .parser import CodeLineParser

logger = structlog.get_logger()


class CodeGraphBuilder:
    """Parse a local repo and persist structural graph to Neo4j.

    Args:
        neo4j_uri: Bolt URI, e.g. bolt://localhost:7687
        neo4j_password: Neo4j password
        repo_root: Absolute or relative path to the repo on disk
        repo: Repo identifier string, e.g. "owner/name" (used as isolation key)
        neo4j_user: Neo4j username (default: neo4j)
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_password: str,
        repo_root: str,
        repo: str,
        neo4j_user: str = "neo4j",
    ) -> None:
        self.repo = repo
        self.repo_root = repo_root
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.parser = CodeLineParser(repo_root)

    def close(self) -> None:
        self.driver.close()

    def build(self) -> dict:
        """Clear existing graph for this repo and rebuild from source.

        Returns:
            {repo, files, definitions, references}
        """
        self._ensure_indexes()
        self._clear()

        files = self.parser.find_files()
        total_defs = 0
        total_refs = 0

        with self.driver.session() as session:
            for filepath in files:
                parsed = self.parser.parse_file(filepath)
                rel_file = parsed["file"]
                defs = parsed["definitions"]
                refs = parsed["references"]

                # Write CodeDef nodes
                if defs:
                    session.run(
                        """
                        UNWIND $defs AS d
                        MERGE (n:CodeDef {name: d, repo: $repo})
                        SET n.file = $file, n.language = $lang, n.updated = timestamp()
                        """,
                        defs=defs,
                        repo=self.repo,
                        file=rel_file,
                        lang=parsed.get("language", "unknown"),
                    )
                    total_defs += len(defs)

                # Write CodeRef nodes and INVOKES edges
                if defs and refs:
                    for ref_name in refs:
                        # For each ref in this file, create an INVOKES edge from
                        # any def in this file that could call it.
                        # Simplified: link the first def in this file to the ref target.
                        # More accurate: all defs in this file may reference it.
                        session.run(
                            """
                            UNWIND $defs AS caller
                            MATCH (a:CodeDef {name: caller, repo: $repo})
                            MERGE (b:CodeDef {name: $ref, repo: $repo})
                            ON CREATE SET b.file = 'unknown', b.language = $lang,
                                          b.updated = timestamp(), b.synthetic = true
                            MERGE (a)-[:INVOKES]->(b)
                            """,
                            defs=defs,
                            ref=ref_name,
                            repo=self.repo,
                            lang=parsed.get("language", "unknown"),
                        )
                    total_refs += len(refs)

                logger.debug(
                    "codegraph.parsed",
                    file=rel_file,
                    defs=len(defs),
                    refs=len(refs),
                )

        logger.info(
            "codegraph.built",
            repo=self.repo,
            files=len(files),
            definitions=total_defs,
            references=total_refs,
        )
        return {
            "repo": self.repo,
            "files": len(files),
            "definitions": total_defs,
            "references": total_refs,
        }

    def _clear(self) -> None:
        """Delete all CodeDef nodes for this repo only (scoped delete)."""
        with self.driver.session() as session:
            session.run(
                "MATCH (n:CodeDef {repo: $repo}) DETACH DELETE n",
                repo=self.repo,
            )
        logger.info("codegraph.cleared", repo=self.repo)

    def _ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        with self.driver.session() as session:
            try:
                session.run(
                    "CREATE INDEX codedef_repo_name IF NOT EXISTS "
                    "FOR (n:CodeDef) ON (n.repo, n.name)"
                )
            except Exception as e:
                logger.debug("index_creation_skipped", error=str(e))
