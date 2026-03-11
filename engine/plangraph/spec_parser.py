# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [plangraph, spec, yaml, parser]
# status: active
# --- /L9_META ---
"""SpecParser — reads constellation YAML specs into normalized dicts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class SpecParser:
    """Parse constellation YAML specification files.

    Args:
        spec_dir: Directory containing spec YAML files
    """

    def __init__(self, spec_dir: str) -> None:
        self.spec_dir = Path(spec_dir)

    def parse(self, filename: str) -> dict[str, Any]:
        """Parse a YAML spec file.

        Returns:
            {services: [...], interfaces: [...], flows: [...]}
        """
        path = self.spec_dir / filename
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.error("spec_not_found", path=str(path))
            return {"services": [], "interfaces": [], "flows": []}
        except yaml.YAMLError as e:
            logger.error("spec_parse_error", path=str(path), error=str(e))
            return {"services": [], "interfaces": [], "flows": []}

        services = self._extract_services(raw)
        interfaces = self._extract_interfaces(raw)
        flows = self._extract_flows(raw)

        return {"services": services, "interfaces": interfaces, "flows": flows}

    def _extract_services(self, raw: dict) -> list[dict]:
        """Extract service definitions from raw YAML."""
        raw_services = raw.get("services", {})
        if isinstance(raw_services, dict):
            result = []
            for name, data in raw_services.items():
                if data is None:
                    data = {}
                svc = {
                    "name": name,
                    "status": data.get("status", "planned"),
                    "description": data.get("description", ""),
                    "depends_on": data.get("depends_on", []),
                    "metadata": data.get("metadata", {}),
                }
                result.append(svc)
            return result
        if isinstance(raw_services, list):
            return [
                {
                    "name": s.get("name", ""),
                    "status": s.get("status", "planned"),
                    "description": s.get("description", ""),
                    "depends_on": s.get("depends_on", []),
                    "metadata": s.get("metadata", {}),
                }
                for s in raw_services
                if isinstance(s, dict)
            ]
        return []

    def _extract_interfaces(self, raw: dict) -> list[dict]:
        """Extract interface definitions from raw YAML."""
        raw_ifaces = raw.get("interfaces", [])
        if isinstance(raw_ifaces, list):
            return [
                {
                    "name": i.get("name", ""),
                    "service": i.get("service", ""),
                    "direction": i.get("direction", "inbound"),
                    "protocol": i.get("protocol", "http"),
                    "description": i.get("description", ""),
                }
                for i in raw_ifaces
                if isinstance(i, dict)
            ]
        # Dict keyed by service name
        if isinstance(raw_ifaces, dict):
            result = []
            for svc_name, iface_list in raw_ifaces.items():
                if not isinstance(iface_list, list):
                    continue
                for iface in iface_list:
                    result.append(
                        {
                            "name": iface.get("name", ""),
                            "service": svc_name,
                            "direction": iface.get("direction", "inbound"),
                            "protocol": iface.get("protocol", "http"),
                            "description": iface.get("description", ""),
                        }
                    )
            return result
        return []

    def _extract_flows(self, raw: dict) -> list[dict]:
        """Extract data flow edges from raw YAML."""
        raw_flows = raw.get("flows", [])
        if not isinstance(raw_flows, list):
            return []
        return [
            {
                "from": f.get("from", ""),
                "to": f.get("to", ""),
                "label": f.get("label", ""),
                "feedback": f.get("feedback", False),
            }
            for f in raw_flows
            if isinstance(f, dict)
        ]
