# --- L9_META ---
# l9_schema: 1
# layer: [test]
# tags: [codegraph, unit, parser]
# status: active
# --- /L9_META ---
"""CodeGraph unit tests — no Neo4j required."""

from __future__ import annotations

import tempfile
from pathlib import Path

from engine.codegraph.parser import _SKIP_DIRS, CodeLineParser


class TestParserFindsPyFiles:
    def test_parser_finds_py_files(self) -> None:
        """Parser should discover .py files in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create some Python files
            (root / "module_a.py").write_text("def foo(): pass\n")
            (root / "module_b.py").write_text("class Bar: pass\n")
            # Non-Python file — should NOT be found
            (root / "readme.txt").write_text("hello\n")

            parser = CodeLineParser(str(root))
            files = parser.find_files()
            py_files = [f for f in files if f.suffix == ".py"]

            assert len(py_files) == 2
            names = {f.name for f in py_files}
            assert "module_a.py" in names
            assert "module_b.py" in names

    def test_parser_finds_js_and_ts_files(self) -> None:
        """Parser should discover .ts and .js files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "index.ts").write_text("function hello() {}\n")
            (root / "util.js").write_text("const x = () => {};\n")

            parser = CodeLineParser(str(root))
            files = parser.find_files()
            exts = {f.suffix for f in files}

            assert ".ts" in exts
            assert ".js" in exts


class TestParserExtractsDefinitions:
    def test_parser_extracts_function_definition(self) -> None:
        """Parser should extract function definitions from Python source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = "def my_function(x, y):\n    return x + y\n"
            (root / "funcs.py").write_text(src)

            parser = CodeLineParser(str(root))
            result = parser.parse_file(root / "funcs.py")

            assert "my_function" in result["definitions"]

    def test_parser_extracts_class_definition(self) -> None:
        """Parser should extract class definitions from Python source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = "class MyClass:\n    def method(self):\n        pass\n"
            (root / "classes.py").write_text(src)

            parser = CodeLineParser(str(root))
            result = parser.parse_file(root / "classes.py")

            assert "MyClass" in result["definitions"]

    def test_parser_extracts_both_function_and_class(self) -> None:
        """Parser should extract both function and class defs in same file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = "class ServiceA:\n    pass\n\ndef process_data(records):\n    return records\n"
            (root / "mixed.py").write_text(src)

            parser = CodeLineParser(str(root))
            result = parser.parse_file(root / "mixed.py")

            assert "ServiceA" in result["definitions"]
            assert "process_data" in result["definitions"]


class TestParserSkipsGitDir:
    def test_parser_skips_git_dir(self) -> None:
        """Parser should skip files inside .git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            git_dir = root / ".git"
            git_dir.mkdir()
            (git_dir / "hooks.py").write_text("def hook(): pass\n")
            (root / "real.py").write_text("def real_func(): pass\n")

            parser = CodeLineParser(str(root))
            files = parser.find_files()
            file_parts = [str(f.relative_to(root)) for f in files]

            assert not any(".git" in p for p in file_parts), (
                f"Should not include .git files, got: {file_parts}"
            )
            assert any("real.py" in p for p in file_parts)

    def test_parser_skips_node_modules(self) -> None:
        """Parser should skip node_modules directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nm = root / "node_modules" / "some-lib"
            nm.mkdir(parents=True)
            (nm / "index.js").write_text("function lib() {}\n")
            (root / "app.js").write_text("function app() {}\n")

            parser = CodeLineParser(str(root))
            files = parser.find_files()
            file_parts = [str(f.relative_to(root)) for f in files]

            assert not any("node_modules" in p for p in file_parts)
            assert any("app.js" in p for p in file_parts)

    def test_skip_dirs_contains_expected(self) -> None:
        """_SKIP_DIRS frozenset should contain standard ignore dirs."""
        for d in (".git", "node_modules", "__pycache__", "dist", "build"):
            assert d in _SKIP_DIRS, f"Expected '{d}' in _SKIP_DIRS"
