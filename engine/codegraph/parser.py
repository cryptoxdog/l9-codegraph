# --- L9_META ---
# l9_schema: 1
# layer: [engine]
# tags: [codegraph, parser, tree-sitter, ast]
# status: active
# --- /L9_META ---
"""Multi-language tree-sitter parser for CodeGraph.

Supports: .py, .ts, .tsx, .js, .jsx
Extracts: function/class definitions and call references.
Skips: .git, node_modules, __pycache__, dist, build
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".venv",
        "venv",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)

_BUILTINS = frozenset(
    {
        "print",
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "list",
        "dict",
        "set",
        "tuple",
        "str",
        "int",
        "float",
        "bool",
        "type",
        "isinstance",
        "issubclass",
        "hasattr",
        "getattr",
        "setattr",
        "delattr",
        "callable",
        "iter",
        "next",
        "open",
        "input",
        "super",
        "object",
        "property",
        "staticmethod",
        "classmethod",
        "abs",
        "all",
        "any",
        "bin",
        "chr",
        "dir",
        "divmod",
        "format",
        "frozenset",
        "hash",
        "hex",
        "id",
        "max",
        "min",
        "oct",
        "ord",
        "pow",
        "repr",
        "reversed",
        "round",
        "sorted",
        "sum",
        "vars",
        "NotImplemented",
        "Ellipsis",
        "None",
        "True",
        "False",
        "Exception",
        "ValueError",
        "TypeError",
        "KeyError",
        "IndexError",
        "AttributeError",
        "RuntimeError",
        "StopIteration",
        "GeneratorExit",
        "ImportError",
        "OSError",
        "IOError",
        "FileNotFoundError",
        "PermissionError",
        "TimeoutError",
        "NotImplementedError",
    }
)

# Lazy language map — populated on first import attempt
LANGUAGE_MAP: dict[str, Any] = {}


def _init_languages() -> None:
    """Lazily initialize tree-sitter language parsers."""
    global LANGUAGE_MAP
    if LANGUAGE_MAP:
        return

    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language

        LANGUAGE_MAP["python"] = Language(tspython.language())
    except Exception as e:
        logger.warning("tree-sitter-python unavailable", error=str(e))

    try:
        import tree_sitter_typescript as tstypescript
        from tree_sitter import Language

        LANGUAGE_MAP["typescript"] = Language(tstypescript.language_typescript())
        LANGUAGE_MAP["tsx"] = Language(tstypescript.language_tsx())
    except Exception as e:
        logger.warning("tree-sitter-typescript unavailable", error=str(e))

    try:
        import tree_sitter_javascript as tsjavascript
        from tree_sitter import Language

        LANGUAGE_MAP["javascript"] = Language(tsjavascript.language())
    except Exception as e:
        logger.warning("tree-sitter-javascript unavailable", error=str(e))


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
}


def _lang_for_file(path: Path) -> str | None:
    return _EXT_TO_LANG.get(path.suffix.lower())


def _extract_python_regex(source: str) -> tuple[list[str], list[str]]:
    """Fallback regex extraction for Python when tree-sitter is unavailable."""
    defs: list[str] = []
    refs: list[str] = []
    def_pattern = re.compile(r"^(?:async\s+)?def\s+(\w+)|^class\s+(\w+)", re.MULTILINE)
    call_pattern = re.compile(r"\b(\w+)\s*\(")
    for m in def_pattern.finditer(source):
        name = m.group(1) or m.group(2)
        if name:
            defs.append(name)
    def_set = set(defs)
    for m in call_pattern.finditer(source):
        name = m.group(1)
        if name and name not in _BUILTINS and name not in def_set:
            refs.append(name)
    return defs, refs


class CodeLineParser:
    """Parse source files and extract CodeDef + CodeRef data."""

    def __init__(self, repo_root: str) -> None:
        self.repo_root = Path(repo_root).resolve()
        _init_languages()

    def find_files(self) -> list[Path]:
        """Walk repo_root and return all parseable source files."""
        results: list[Path] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            # Skip ignored dirs
            parts = path.relative_to(self.repo_root).parts
            if any(part in _SKIP_DIRS for part in parts):
                continue
            if _lang_for_file(path) is not None:
                results.append(path)
        return results

    def parse_file(self, filepath: Path) -> dict[str, Any]:
        """Parse a single file. Returns {file, language, definitions, references}."""
        lang_key = _lang_for_file(filepath)
        if lang_key is None:
            return {"file": str(filepath), "language": None, "definitions": [], "references": []}

        rel_path = str(filepath.relative_to(self.repo_root))

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning("read_error", file=rel_path, error=str(e))
            return {"file": rel_path, "language": lang_key, "definitions": [], "references": []}

        # Use tree-sitter if available for this language
        if lang_key in LANGUAGE_MAP:
            defs, refs = self._parse_with_treesitter(source, lang_key, filepath)
        elif lang_key == "python":
            defs, refs = _extract_python_regex(source)
        else:
            defs, refs = [], []

        return {
            "file": rel_path,
            "language": lang_key,
            "definitions": defs,
            "references": refs,
        }

    def _parse_with_treesitter(
        self, source: str, lang_key: str, filepath: Path
    ) -> tuple[list[str], list[str]]:
        """Use tree-sitter AST to extract definitions and call references."""
        try:
            from tree_sitter import Parser

            language = LANGUAGE_MAP[lang_key]
            parser = Parser(language)
            tree = parser.parse(source.encode("utf-8", errors="replace"))
            root = tree.root_node

            defs: list[str] = []
            refs: list[str] = []
            def_set: set[str] = set()

            self._walk(root, source, defs, refs, def_set, lang_key)

            # Deduplicate, filter builtins from refs
            unique_defs = list(dict.fromkeys(defs))
            unique_refs = list(
                dict.fromkeys(r for r in refs if r not in _BUILTINS and r not in def_set)
            )
            return unique_defs, unique_refs
        except Exception as e:
            logger.warning("treesitter_parse_error", file=str(filepath), error=str(e))
            if lang_key == "python":
                return _extract_python_regex(source)
            return [], []

    def _walk(
        self,
        node: Any,
        source: str,
        defs: list[str],
        refs: list[str],
        def_set: set[str],
        lang_key: str,
    ) -> None:
        """Recursively walk AST, collect definitions and call references."""
        self._collect_def(node, source, defs, def_set)
        self._collect_ref(node, source, refs)
        for child in node.children:
            self._walk(child, source, defs, refs, def_set, lang_key)

    def _collect_def(self, node: Any, source: str, defs: list[str], def_set: set[str]) -> None:
        """Extract definition name from AST node if applicable."""
        node_type = node.type
        named_def_types = {
            "function_definition",
            "async_function_definition",
            "class_definition",
            "function_declaration",
            "generator_function_declaration",
            "method_definition",
            "arrow_function",
            "class_declaration",
        }
        if node_type in named_def_types:
            name_node = node.child_by_field_name("name")
            if name_node:
                name = source[name_node.start_byte : name_node.end_byte]
                defs.append(name)
                def_set.add(name)
        elif node_type == "lexical_declaration":
            self._collect_lexical_def(node, source, defs, def_set)

    def _collect_lexical_def(
        self, node: Any, source: str, defs: list[str], def_set: set[str]
    ) -> None:
        """Handle const foo = () => {} style declarations."""
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                val_node = child.child_by_field_name("value")
                if (
                    name_node
                    and val_node
                    and val_node.type
                    in (
                        "arrow_function",
                        "function",
                        "function_expression",
                    )
                ):
                    name = source[name_node.start_byte : name_node.end_byte]
                    defs.append(name)
                    def_set.add(name)

    def _collect_ref(self, node: Any, source: str, refs: list[str]) -> None:
        """Extract call reference from AST node if applicable."""
        node_type = node.type
        if node_type in ("call", "call_expression"):
            func_node = node.child_by_field_name("function")
            if func_node:
                name = self._extract_call_name(func_node, source)
                if name:
                    refs.append(name)

    def _extract_call_name(self, node: Any, source: str) -> str | None:
        """Extract a clean name from a call's function node."""
        node_type = node.type
        if node_type == "identifier":
            return source[node.start_byte : node.end_byte]
        if node_type == "attribute":
            # foo.bar(...) — return just "bar"
            attr = node.child_by_field_name("attribute")
            if attr:
                return source[attr.start_byte : attr.end_byte]
        if node_type == "member_expression":
            prop = node.child_by_field_name("property")
            if prop:
                return source[prop.start_byte : prop.end_byte]
        return None
