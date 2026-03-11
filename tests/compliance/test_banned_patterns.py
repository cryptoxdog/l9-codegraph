"""Automated enforcement of Rules 3, 4, 5 (CYPHER_SAFETY.md, BANNED_PATTERNS.md)."""
import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _get_engine_py_files():
    engine = REPO_ROOT / "engine"
    if not engine.exists():
        return []
    return list(engine.rglob("*.py"))


def test_no_eval_exec_compile():
    violations = []
    for py_file in _get_engine_py_files():
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "compile"):
                    violations.append(
                        f"{py_file.relative_to(REPO_ROOT)}:{node.lineno} "
                        f"{node.func.id}() call"
                    )
    assert not violations, "Banned function calls:\n" + "\n".join(violations)


def test_no_fstring_cypher_limit_skip():
    violations = []
    for py_file in _get_engine_py_files():
        lines = py_file.read_text().split("\n")
        for i, line in enumerate(lines, 1):
            if re.search(r'f["\'\'].*LIMIT\s*\{', line) or \
               re.search(r'f["\'\'].*SKIP\s*\{', line):
                violations.append(
                    f"{py_file.relative_to(REPO_ROOT)}:{i} "
                    f"f-string LIMIT/SKIP interpolation"
                )
    assert not violations, "Cypher injection vectors:\n" + "\n".join(violations)


def test_no_bare_except():
    violations = []
    for py_file in _get_engine_py_files():
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                violations.append(
                    f"{py_file.relative_to(REPO_ROOT)}:{node.lineno} "
                    f"bare except:"
                )
    assert not violations, "Bare except handlers:\n" + "\n".join(violations)


def test_no_fastapi_in_engine():
    violations = []
    for py_file in _get_engine_py_files():
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("fastapi"):
                    violations.append(
                        f"{py_file.relative_to(REPO_ROOT)}:{node.lineno} "
                        f"FastAPI import in engine/"
                    )
    assert not violations, "FastAPI imports in engine:\n" + "\n".join(violations)
