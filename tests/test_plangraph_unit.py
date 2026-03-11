# --- L9_META ---
# l9_schema: 1
# layer: [test]
# tags: [plangraph, unit, spec-parser, topology]
# status: active
# --- /L9_META ---
"""PlanGraph unit tests — no Neo4j required."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from engine.plangraph.retriever import PlanGraphRetriever
from engine.plangraph.spec_parser import SpecParser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SPEC = {
    "constellation": "testcon",
    "services": {
        "ALPHA": {
            "status": "built",
            "description": "First service",
            "depends_on": [],
        },
        "BETA": {
            "status": "planned",
            "description": "Second service",
            "depends_on": ["ALPHA"],
        },
        "GAMMA": {
            "status": "planned",
            "description": "Third service",
            "depends_on": ["ALPHA"],
        },
        "DELTA": {
            "status": "planned",
            "description": "Fourth service",
            "depends_on": ["BETA", "GAMMA"],
        },
    },
    "interfaces": [
        {"name": "alpha_in", "service": "ALPHA", "direction": "inbound", "protocol": "http"},
        {"name": "alpha_out", "service": "ALPHA", "direction": "outbound", "protocol": "http"},
        {"name": "beta_in", "service": "BETA", "direction": "inbound", "protocol": "http"},
    ],
    "flows": [
        {"from": "ALPHA", "to": "BETA", "label": "data"},
        {"from": "ALPHA", "to": "GAMMA", "label": "context"},
        {"from": "BETA", "to": "DELTA", "label": "processed", "feedback": False},
        {"from": "DELTA", "to": "ALPHA", "label": "feedback", "feedback": True},
    ],
}


@pytest.fixture()
def spec_dir_with_yaml():
    """Create a temp dir with a sample constellation.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "constellation.yaml"
        path.write_text(yaml.dump(SAMPLE_SPEC), encoding="utf-8")
        yield tmpdir


# ---------------------------------------------------------------------------
# test_spec_parser_extracts_services
# ---------------------------------------------------------------------------


class TestSpecParserExtractsServices:
    def test_spec_parser_extracts_services(self, spec_dir_with_yaml: str) -> None:
        """SpecParser should return all 4 services from the YAML."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        services = result["services"]
        assert len(services) == 4

        names = {s["name"] for s in services}
        assert names == {"ALPHA", "BETA", "GAMMA", "DELTA"}

    def test_spec_parser_extracts_service_status(self, spec_dir_with_yaml: str) -> None:
        """SpecParser should preserve service status."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        by_name = {s["name"]: s for s in result["services"]}
        assert by_name["ALPHA"]["status"] == "built"
        assert by_name["BETA"]["status"] == "planned"

    def test_spec_parser_extracts_depends_on(self, spec_dir_with_yaml: str) -> None:
        """SpecParser should extract depends_on lists."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        by_name = {s["name"]: s for s in result["services"]}
        assert by_name["ALPHA"]["depends_on"] == []
        assert "ALPHA" in by_name["BETA"]["depends_on"]
        assert set(by_name["DELTA"]["depends_on"]) == {"BETA", "GAMMA"}


# ---------------------------------------------------------------------------
# test_spec_parser_extracts_interfaces
# ---------------------------------------------------------------------------


class TestSpecParserExtractsInterfaces:
    def test_spec_parser_extracts_interfaces(self, spec_dir_with_yaml: str) -> None:
        """SpecParser should return all interface definitions."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        interfaces = result["interfaces"]
        assert len(interfaces) == 3

        names = {i["name"] for i in interfaces}
        assert "alpha_in" in names
        assert "alpha_out" in names
        assert "beta_in" in names

    def test_spec_parser_interface_has_direction(self, spec_dir_with_yaml: str) -> None:
        """Each interface should have a direction field."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        for iface in result["interfaces"]:
            assert "direction" in iface
            assert iface["direction"] in ("inbound", "outbound")

    def test_spec_parser_interface_has_service(self, spec_dir_with_yaml: str) -> None:
        """Each interface should reference its parent service."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        by_name = {i["name"]: i for i in result["interfaces"]}
        assert by_name["alpha_in"]["service"] == "ALPHA"
        assert by_name["beta_in"]["service"] == "BETA"


# ---------------------------------------------------------------------------
# test_spec_parser_extracts_flows
# ---------------------------------------------------------------------------


class TestSpecParserExtractsFlows:
    def test_spec_parser_extracts_flows(self, spec_dir_with_yaml: str) -> None:
        """SpecParser should return all flow edges."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        flows = result["flows"]
        assert len(flows) == 4

    def test_spec_parser_flow_has_from_to(self, spec_dir_with_yaml: str) -> None:
        """Each flow should have 'from' and 'to' fields."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        for flow in result["flows"]:
            assert "from" in flow
            assert "to" in flow

    def test_spec_parser_flow_feedback_flag(self, spec_dir_with_yaml: str) -> None:
        """SpecParser should preserve feedback=True flag on flows."""
        parser = SpecParser(spec_dir_with_yaml)
        result = parser.parse("constellation.yaml")

        feedback_flows = [f for f in result["flows"] if f.get("feedback")]
        assert len(feedback_flows) == 1
        assert feedback_flows[0]["from"] == "DELTA"
        assert feedback_flows[0]["to"] == "ALPHA"


# ---------------------------------------------------------------------------
# test_build_order_topological
# ---------------------------------------------------------------------------


class TestBuildOrderTopological:
    """Test _topological_sort directly — no Neo4j connection needed."""

    def _make_retriever(self) -> PlanGraphRetriever:
        """Create a PlanGraphRetriever with mocked Neo4j driver."""
        retriever = PlanGraphRetriever.__new__(PlanGraphRetriever)
        retriever.driver = MagicMock()
        return retriever

    def test_topological_sort_simple_chain(self) -> None:
        """A -> B -> C should sort to [A, B, C]."""
        retriever = self._make_retriever()
        dep_map = {"A": [], "B": ["A"], "C": ["B"]}
        topo, groups = retriever._topological_sort(dep_map)

        assert topo.index("A") < topo.index("B")
        assert topo.index("B") < topo.index("C")

    def test_topological_sort_parallel_groups(self) -> None:
        """B and C both depend on A — should be in the same wave."""
        retriever = self._make_retriever()
        dep_map = {
            "ALPHA": [],
            "BETA": ["ALPHA"],
            "GAMMA": ["ALPHA"],
            "DELTA": ["BETA", "GAMMA"],
        }
        topo, groups = retriever._topological_sort(dep_map)

        # ALPHA must come first
        assert topo[0] == "ALPHA"
        # BETA and GAMMA should be in same wave (wave 2)
        wave2 = groups[1]
        assert set(wave2) == {"BETA", "GAMMA"}
        # DELTA must come last
        assert topo[-1] == "DELTA"

    def test_topological_sort_no_deps(self) -> None:
        """Services with no deps should all be in wave 1."""
        retriever = self._make_retriever()
        dep_map = {"A": [], "B": [], "C": []}
        topo, groups = retriever._topological_sort(dep_map)

        assert len(groups) == 1
        assert set(groups[0]) == {"A", "B", "C"}
        assert set(topo) == {"A", "B", "C"}

    def test_topological_sort_revopsos_shape(self) -> None:
        """Test RevOpsOS topology: ENRICH+GRAPH -> SCORE -> ROUTE/HEALTH -> FORECAST/HANDOFF."""
        retriever = self._make_retriever()
        dep_map = {
            "ENRICH": [],
            "GRAPH": [],
            "SCORE": ["ENRICH", "GRAPH"],
            "ROUTE": ["SCORE", "GRAPH"],
            "FORECAST": ["SCORE", "ROUTE"],
            "SIGNAL": ["ENRICH"],
            "HEALTH": ["SCORE", "ENRICH"],
            "HANDOFF": ["ROUTE", "SCORE"],
        }
        topo, groups = retriever._topological_sort(dep_map)

        # ENRICH and GRAPH must precede SCORE
        assert topo.index("ENRICH") < topo.index("SCORE")
        assert topo.index("GRAPH") < topo.index("SCORE")
        # SCORE must precede ROUTE
        assert topo.index("SCORE") < topo.index("ROUTE")
        # ROUTE must precede FORECAST
        assert topo.index("ROUTE") < topo.index("FORECAST")
        # All services present
        assert set(topo) == set(dep_map.keys())
