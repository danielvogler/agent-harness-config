""".pre-commit-hooks.yaml: the hooks other repos reference by tag.

This repo runs the same hooks as local ones in .pre-commit-config.yaml. pygrep hooks
carry their logic in the pattern itself, so the pattern exists in both files; these
tests are what keeps the two from drifting apart the way hand-made copies did.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PUBLISHED = (REPO / ".pre-commit-hooks.yaml").read_text()
LOCAL = (REPO / ".pre-commit-config.yaml").read_text()
PUBLISHED_IDS = [
    "no-ai-attribution",
    "no-commit-emoji",
    "no-service-account-key",
    "repo-conformance",
]
FIELDS = ("language", "entry", "stages", "args", "types")


def hook(config: str, hook_id: str) -> dict[str, str]:
    """The scalar fields of one hook, read line by line; no YAML parser is installed."""
    block = re.search(rf"- id: {hook_id}\n(.*?)(?=\n\s*(?:#[^\n]*\n\s*)*- id:|\Z)", config, re.S)
    assert block is not None, hook_id
    fields = re.findall(r"^\s+(\w+): (.+)$", block.group(1), re.M)
    return {key: value.strip() for key, value in fields if key in FIELDS}


def test_publishes_exactly_the_shared_hooks():
    # Act
    ids = re.findall(r"^- id: (\S+)", PUBLISHED, re.M)

    # Assert
    assert ids == PUBLISHED_IDS


@pytest.mark.parametrize(
    "hook_id", ["no-ai-attribution", "no-commit-emoji", "no-service-account-key"]
)
def test_local_pygrep_hook_matches_the_published_one(hook_id):
    # Act
    published, local = hook(PUBLISHED, hook_id), hook(LOCAL, hook_id)

    # Assert
    assert published["language"] == "pygrep"
    assert published == local


def test_repo_conformance_runs_the_same_module_both_ways():
    # Arrange
    pyproject = (REPO / "pyproject.toml").read_text()

    # Act
    published, local = hook(PUBLISHED, "repo-conformance"), hook(LOCAL, "repo-conformance")

    # Assert
    assert published["entry"] == "repo-conformance"
    assert 'repo-conformance = "repo_conformance:main"' in pyproject
    assert local["entry"] == "python3 tools/repo_conformance.py"


@pytest.mark.parametrize(
    ("message", "blocked"),
    [
        ("fix: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n", True),
        ("docs: x\n\nGenerated with [Claude Code](https://claude.com)\n", True),
        ("fix: x\n\nCo-Authored-By: Ann Example <ann@example.com>\n", False),
        ("fix: x\n\nCo-Authored-By: Ann <ann@example.com>\n- mention claude.md\n", False),
    ],
)
def test_attribution_pattern(message, blocked):
    # Arrange
    pattern = re.compile(hook(PUBLISHED, "no-ai-attribution")["entry"].strip("'"), re.I)

    # Act
    hit = any(pattern.search(line) for line in message.splitlines())

    # Assert
    assert hit is blocked
