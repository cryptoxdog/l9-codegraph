"""Automated enforcement of Rule 1 (FIELD_NAMES.md).
Catches C-1 through C-5 at test time."""
import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _get_engine_py_files():
    engine = REPO_ROOT / "engine"
    if not engine.exists():
        return []
    return list(engine.rglob("*.py"))


def test_no_camelcase_pydantic_fields():
    violations = []
    for py_file in _get_engine_py_files():
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(
                        item.target, ast.Name
                    ):
                        name = item.target.id
                        if re.match(r"^[a-z]+[A-Z]", name):
                            violations.append(
                                f"{py_file.relative_to(REPO_ROOT)}:{item.lineno} "
                                f"camelCase field '{name}'"
                            )
    assert not violations, "camelCase fields found:\n" + "\n".join(violations)


def test_no_flatcase_pydantic_fields():
    violations = []
    for py_file in _get_engine_py_files():
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(
                        item.target, ast.Name
                    ):
                        name = item.target.id
                        if len(name) > 12 and "_" not in name and name.islower():
                            violations.append(
                                f"{py_file.relative_to(REPO_ROOT)}:{item.lineno} "
                                f"flatcase field '{name}'"
                            )
    assert not violations, "flatcase fields found:\n" + "\n".join(violations)


def test_no_field_aliases():
    violations = []
    for py_file in _get_engine_py_files():
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.value, ast.Call):
                        for kw in getattr(item.value, "keywords", []):
                            if kw.arg == "alias":
                                name = item.target.id if isinstance(item.target, ast.Name) else "?"
                                violations.append(
                                    f"{py_file.relative_to(REPO_ROOT)}:{item.lineno} "
                                    f"Field alias on '{name}'"
                                )
    assert not violations, "Field aliases found:\n" + "\n".join(violations)
