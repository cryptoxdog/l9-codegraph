"""Automated enforcement of Rule 2 (METHOD_SIGNATURES.md).
Every import must resolve to an existing file."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def test_all_internal_imports_resolve():
    engine = REPO_ROOT / "engine"
    if not engine.exists():
        return
    violations = []
    for py_file in engine.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(("engine", "memory", "chassis")):
                    mod_path = REPO_ROOT / node.module.replace(".", "/")
                    if not (
                        mod_path.with_suffix(".py").exists() or (mod_path / "__init__.py").exists()
                    ):
                        violations.append(
                            f"{py_file.relative_to(REPO_ROOT)}:{node.lineno} "
                            f"unresolved import '{node.module}'"
                        )
    assert not violations, "Phantom imports:\n" + "\n".join(violations)
