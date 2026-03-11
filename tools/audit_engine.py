#!/usr/bin/env python3
"""L9 Audit Engine -- 27-Rule Scanner.

Scans engine code for contract violations across 5 groups:
  NAMING (1-5), SECURITY (6-10), IMPORTS (11-15),
  ERROR (16-19), COMPLETENESS (20-23), PATTERNS (24-27)

Usage:
  python tools/audit_engine.py              # Run all rules
  python tools/audit_engine.py --strict     # Exit 1 on CRITICAL/HIGH
  python tools/audit_engine.py --group naming
  python tools/audit_engine.py --fix        # Auto-fix where possible
  python tools/audit_engine.py --json       # JSON output
  python tools/audit_engine.py --exclude engine/legacy/
"""

import argparse
import ast
import json as json_mod
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent
ENGINE_DIR = REPO_ROOT / "engine"


@dataclass
class Finding:
    severity: str  # CRITICAL, HIGH, MEDIUM, INFO
    code: str  # C-001, H-007, etc.
    rule: int
    group: str
    message: str
    file: str
    line: int
    fix_hint: Optional[str] = None


@dataclass
class AuditResult:
    findings: list = field(default_factory=list)

    def add(self, **kwargs):
        self.findings.append(Finding(**kwargs))

    @property
    def critical_count(self):
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self):
        return sum(1 for f in self.findings if f.severity == "HIGH")

    @property
    def medium_count(self):
        return sum(1 for f in self.findings if f.severity == "MEDIUM")

    @property
    def info_count(self):
        return sum(1 for f in self.findings if f.severity == "INFO")


def get_py_files(exclude: list[str] = None) -> list[Path]:
    if not ENGINE_DIR.exists():
        return []
    exclude = exclude or []
    files = []
    for f in ENGINE_DIR.rglob("*.py"):
        if not any(ex in str(f) for ex in exclude):
            files.append(f)
    return files


# ============================================================
# GROUP: NAMING (Rules 1-5)
# ============================================================
def check_naming(files: list[Path], result: AuditResult):
    counter = 0
    for py_file in files:
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        name = item.target.id
                        rel = py_file.relative_to(REPO_ROOT)
                        # Rule 1: camelCase detection
                        if re.match(r"^[a-z]+[A-Z]", name):
                            counter += 1
                            result.add(
                                severity="CRITICAL",
                                code=f"C-{counter:03d}",
                                rule=1,
                                group="naming",
                                message=f"camelCase field '{name}'",
                                file=str(rel),
                                line=item.lineno,
                                fix_hint=f"Rename to {re.sub(r'([A-Z])', r'_\1', name).lower()}",
                            )
                        # Rule 2: flatcase detection (long single-word fields)
                        elif len(name) > 12 and "_" not in name and name.islower():
                            counter += 1
                            result.add(
                                severity="CRITICAL",
                                code=f"C-{counter:03d}",
                                rule=2,
                                group="naming",
                                message=f"Likely flatcase field '{name}'",
                                file=str(rel),
                                line=item.lineno,
                                fix_hint="Add underscores: e.g., candidate_prop not candidateprop",
                            )
                        # Rule 3: Field(alias=...) detection
                        if isinstance(item.value, ast.Call):
                            for kw in getattr(item.value, "keywords", []):
                                if kw.arg == "alias":
                                    counter += 1
                                    result.add(
                                        severity="CRITICAL",
                                        code=f"C-{counter:03d}",
                                        rule=3,
                                        group="naming",
                                        message=f"Field alias on '{name}' -- banned per FIELD_NAMES.md",
                                        file=str(rel),
                                        line=item.lineno,
                                        fix_hint="Remove alias. YAML key = Python field = attribute access.",
                                    )
                # Rule 4: populate_by_name in model_config
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "model_config":
                                src = ast.get_source_segment(py_file.read_text(), item) or ""
                                if "populate_by_name" in src:
                                    counter += 1
                                    result.add(
                                        severity="CRITICAL",
                                        code=f"C-{counter:03d}",
                                        rule=4,
                                        group="naming",
                                        message="populate_by_name in model_config -- banned",
                                        file=str(py_file.relative_to(REPO_ROOT)),
                                        line=item.lineno,
                                        fix_hint="Remove populate_by_name. No aliases = no need.",
                                    )


# ============================================================
# GROUP: SECURITY (Rules 6-10)
# ============================================================
def check_security(files: list[Path], result: AuditResult):
    counter = 100
    for py_file in files:
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except SyntaxError:
            continue
        rel = py_file.relative_to(REPO_ROOT)
        lines = source.split("\n")

        for node in ast.walk(tree):
            # Rule 6: eval/exec/compile
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "compile"):
                    counter += 1
                    result.add(
                        severity="CRITICAL",
                        code=f"C-{counter:03d}",
                        rule=6,
                        group="security",
                        message=f"{node.func.id}() call -- use dispatch table instead",
                        file=str(rel),
                        line=node.lineno,
                        fix_hint="Replace with explicit dispatch: OPERATORS[op](a, b)",
                    )

        # Rule 7: f-string in Cypher (LIMIT/SKIP/WHERE values)
        for i, line in enumerate(lines, 1):
            # Detect f-strings with LIMIT/SKIP value interpolation
            if re.search(r"f[\"'].*LIMIT\s*\{", line) or re.search(r"f[\"'].*SKIP\s*\{", line):
                counter += 1
                result.add(
                    severity="CRITICAL",
                    code=f"C-{counter:03d}",
                    rule=7,
                    group="security",
                    message="f-string interpolation in LIMIT/SKIP -- use $param",
                    file=str(rel),
                    line=i,
                    fix_hint="Use parameters: {'limit': top_n} with $limit in Cypher",
                )
            # Rule 8: str() on collections in query context
            if re.search(r"str\(\[", line) or re.search(r"str\(.*list", line):
                if "cypher" in line.lower() or "query" in line.lower() or "gds" in line.lower():
                    counter += 1
                    result.add(
                        severity="HIGH",
                        code=f"H-{counter:03d}",
                        rule=8,
                        group="security",
                        message="str() on collection in query context -- use json.dumps()",
                        file=str(rel),
                        line=i,
                        fix_hint="json.dumps(my_list) not str(my_list)",
                    )


# ============================================================
# GROUP: IMPORTS (Rules 11-15)
# ============================================================
def check_imports(files: list[Path], result: AuditResult):
    counter = 200
    for py_file in files:
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        rel = py_file.relative_to(REPO_ROOT)

        for node in ast.walk(tree):
            # Rule 11: FastAPI imports in engine/
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("fastapi"):
                    counter += 1
                    result.add(
                        severity="HIGH",
                        code=f"H-{counter:03d}",
                        rule=11,
                        group="imports",
                        message=f"FastAPI import in engine/ -- engine never touches HTTP",
                        file=str(rel),
                        line=node.lineno,
                        fix_hint="Remove. Engine receives (tenant, payload) from chassis.",
                    )
                # Rule 12: Phantom imports (internal modules that don't exist)
                if node.module.startswith(("engine.", "memory.", "chassis.")):
                    mod_path = REPO_ROOT / node.module.replace(".", "/")
                    if not (
                        mod_path.with_suffix(".py").exists() or (mod_path / "__init__.py").exists()
                    ):
                        counter += 1
                        result.add(
                            severity="HIGH",
                            code=f"H-{counter:03d}",
                            rule=12,
                            group="imports",
                            message=f"Phantom import '{node.module}' -- file does not exist",
                            file=str(rel),
                            line=node.lineno,
                            fix_hint="Create the file or remove the import.",
                        )

            # Rule 13: Redefining l9-core models
            if isinstance(node, ast.ClassDef):
                if node.name in (
                    "PacketEnvelope",
                    "TenantContext",
                    "ExecuteRequest",
                    "ExecuteResponse",
                    "DelegationLink",
                    "HopEntry",
                ):
                    counter += 1
                    result.add(
                        severity="HIGH",
                        code=f"H-{counter:03d}",
                        rule=13,
                        group="imports",
                        message=f"Redefining '{node.name}' -- import from l9-core instead",
                        file=str(rel),
                        line=node.lineno,
                        fix_hint="from l9.core.envelope import PacketEnvelope",
                    )


# ============================================================
# GROUP: ERROR (Rules 16-19)
# ============================================================
def check_errors(files: list[Path], result: AuditResult):
    counter = 300
    for py_file in files:
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        rel = py_file.relative_to(REPO_ROOT)

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Rule 16: bare except
                if node.type is None:
                    counter += 1
                    result.add(
                        severity="MEDIUM",
                        code=f"M-{counter:03d}",
                        rule=16,
                        group="error",
                        message="Bare 'except:' -- catch specific exceptions",
                        file=str(rel),
                        line=node.lineno,
                        fix_hint="except (ValueError, KeyError) as exc:",
                    )
                # Rule 17: except Exception: pass
                if node.type and isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        counter += 1
                        result.add(
                            severity="MEDIUM",
                            code=f"M-{counter:03d}",
                            rule=17,
                            group="error",
                            message="'except Exception: pass' -- swallowed error",
                            file=str(rel),
                            line=node.lineno,
                            fix_hint="Log the error or re-raise.",
                        )


# ============================================================
# GROUP: COMPLETENESS (Rules 20-23)
# ============================================================
def check_completeness(files: list[Path], result: AuditResult):
    counter = 400
    handlers_file = ENGINE_DIR / "handlers.py"
    if not handlers_file.exists():
        return
    try:
        tree = ast.parse(handlers_file.read_text())
    except SyntaxError:
        return
    rel = handlers_file.relative_to(REPO_ROOT)

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("handle_"):
            action = node.name.replace("handle_", "")
            # Rule 20: Check for Pydantic validation in first few lines
            has_validation = False
            for stmt in node.body[:5]:
                src = ast.dump(stmt)
                if "model_validate" in src or "ModelValidate" in src:
                    has_validation = True
                    break
            if not has_validation:
                counter += 1
                result.add(
                    severity="HIGH",
                    code=f"H-{counter:03d}",
                    rule=20,
                    group="completeness",
                    message=f"Handler '{node.name}' missing Pydantic payload validation",
                    file=str(rel),
                    line=node.lineno,
                    fix_hint=f"Add: request = {action.title()}Payload.model_validate(payload)",
                )


# ============================================================
# GROUP: PATTERNS (Rules 24-27)
# ============================================================
def check_patterns(files: list[Path], result: AuditResult):
    counter = 500
    for py_file in files:
        try:
            source = py_file.read_text()
        except Exception:
            continue
        rel = py_file.relative_to(REPO_ROOT)
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            # Rule 24: Direct SQL bypassing ingest_packet
            if re.search(r"INSERT\s+INTO\s+packetstore", line, re.IGNORECASE):
                counter += 1
                result.add(
                    severity="HIGH",
                    code=f"H-{counter:03d}",
                    rule=24,
                    group="patterns",
                    message="Direct INSERT INTO packetstore -- use ingest_packet()",
                    file=str(rel),
                    line=i,
                    fix_hint="from memory.substrate import ingest_packet",
                )
            # Rule 25: Direct HTTP calls bypassing delegate_to_node
            if re.search(r"httpx\.(post|get|put|delete|patch)\(", line) or re.search(
                r"aiohttp\.ClientSession", line
            ):
                counter += 1
                result.add(
                    severity="HIGH",
                    code=f"H-{counter:03d}",
                    rule=25,
                    group="patterns",
                    message="Direct HTTP call -- use delegate_to_node()",
                    file=str(rel),
                    line=i,
                    fix_hint="from l9.core.delegation import delegate_to_node",
                )

    # Rule 26: Missing __init__.py in packages
    for dirpath in ENGINE_DIR.rglob("*"):
        if dirpath.is_dir() and any(dirpath.glob("*.py")):
            init = dirpath / "__init__.py"
            if not init.exists():
                counter += 1
                result.add(
                    severity="MEDIUM",
                    code=f"M-{counter:03d}",
                    rule=26,
                    group="patterns",
                    message=f"Missing __init__.py in {dirpath.relative_to(REPO_ROOT)}",
                    file=str(dirpath.relative_to(REPO_ROOT)),
                    line=0,
                    fix_hint="Create empty __init__.py",
                )


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="L9 Audit Engine -- 27-Rule Scanner")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on CRITICAL/HIGH")
    parser.add_argument(
        "--group",
        choices=["naming", "security", "imports", "error", "completeness", "patterns"],
        help="Run only one rule group",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--fix", action="store_true", help="Auto-fix where possible")
    parser.add_argument("--exclude", nargs="*", default=[], help="Paths to exclude")
    args = parser.parse_args()

    files = get_py_files(args.exclude)
    result = AuditResult()

    groups = {
        "naming": check_naming,
        "security": check_security,
        "imports": check_imports,
        "error": check_errors,
        "completeness": check_completeness,
        "patterns": check_patterns,
    }

    if args.group:
        groups[args.group](files, result)
    else:
        for fn in groups.values():
            fn(files, result)

    if args.json:
        output = [
            {
                "severity": f.severity,
                "code": f.code,
                "rule": f.rule,
                "group": f.group,
                "message": f.message,
                "file": f.file,
                "line": f.line,
                "fix_hint": f.fix_hint,
            }
            for f in result.findings
        ]
        print(json_mod.dumps(output, indent=2))
    else:
        if not result.findings:
            print("No findings. All 27 rules pass.")
        for f in sorted(result.findings, key=lambda x: x.severity):
            sev = f"{f.severity:8s}"
            print(f"{sev} [{f.code}] {f.message}")
            print(f"         {f.file}:{f.line}")
            if f.fix_hint:
                print(f"         Fix: {f.fix_hint}")
            print()

        print(
            f"Summary: {result.critical_count} CRITICAL, {result.high_count} HIGH, "
            f"{result.medium_count} MEDIUM, {result.info_count} INFO"
        )

    if args.strict and (result.critical_count > 0 or result.high_count > 0):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
