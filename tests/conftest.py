"""Shared fixtures: load the hyphenated scripts in tools/ as modules.

The scripts are standalone files, not a package, and several keep their findings in
module-level lists. Each fixture therefore loads a fresh copy per test, so one test's
errors never leak into the next.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def load_tool(filename: str) -> ModuleType:
    name = "tool_" + filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture
def materialize() -> ModuleType:
    return load_tool("materialize.py")


@pytest.fixture
def validate() -> ModuleType:
    return load_tool("validate-manifests.py")


@pytest.fixture
def doctor() -> ModuleType:
    return load_tool("doctor.py")


@pytest.fixture
def setup_user(tmp_path: Path, monkeypatch) -> ModuleType:
    """setup-user.py with HOME pointed at a temp directory, never the real one."""
    module = load_tool("setup-user.py")
    monkeypatch.setattr(module, "HOME", tmp_path)
    return module


@pytest.fixture
def mcp_setup() -> ModuleType:
    return load_tool("mcp-setup.py")


@pytest.fixture
def context_cost() -> ModuleType:
    return load_tool("context-cost.py")


@pytest.fixture
def conventions() -> ModuleType:
    return load_tool("build-conventions-skill.py")
