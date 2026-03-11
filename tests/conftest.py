# tests/conftest.py
# CRITICAL: All paths via Path(__file__).parent.parent
# This alone caused entire test suite failure in Audit 2 (H-12)

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def domains_dir(repo_root):
    d = repo_root / "domains"
    assert d.exists(), f"domains/ not found at {d}"
    return d


@pytest.fixture
def contracts_dir(repo_root):
    d = repo_root / "docs" / "contracts"
    assert d.exists(), f"docs/contracts/ not found at {d}"
    return d


@pytest.fixture
def engine_dir(repo_root):
    d = repo_root / "engine"
    assert d.exists(), f"engine/ not found at {d}"
    return d
