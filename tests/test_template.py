"""The copier template renders into a repository that follows custom/rules/repo.md."""

from __future__ import annotations

from pathlib import Path

import pytest

copier = pytest.importorskip("copier")

REPO = Path(__file__).resolve().parent.parent

ANSWERS = {
    "project_name": "demo",
    "description": "Turns a list of things into a report",
    "author": "Example Author",
}


def render(dest: Path, **answers: object) -> Path:
    # vcs_ref HEAD includes uncommitted template changes, so the test sees the working tree.
    copier.run_copy(
        str(REPO),
        dest,
        data={**ANSWERS, **answers},
        defaults=True,
        vcs_ref="HEAD",
        quiet=True,
    )
    return dest


@pytest.mark.filterwarnings("ignore::Warning")
class TestTemplate:
    def test_python_repo_has_the_key_files(self, tmp_path):
        # Act
        out = render(tmp_path / "demo")

        # Assert
        for name in [
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "README.md",
            "Makefile",
            ".pre-commit-config.yaml",
            ".github/workflows/ci.yml",
            ".github/workflows/pr-description.yml",
            "CHANGELOG.md",
            "LICENSE",
            "NOTICE",
            ".gitignore",
            "docs/ARCHITECTURE.md",
            "pyproject.toml",
            "src/demo/__init__.py",
            "tests/test_smoke.py",
        ]:
            assert (out / name).is_file(), name

    def test_claude_and_gemini_only_point_at_agents_md(self, tmp_path):
        # Act
        out = render(tmp_path / "demo")

        # Assert
        for name in ["CLAUDE.md", "GEMINI.md"]:
            lines = [ln for ln in (out / name).read_text().splitlines() if ln.strip()]
            assert lines[0] == "@AGENTS.md"
            assert len(lines) == 2

    def test_no_empty_ledgers_and_no_unrendered_jinja(self, tmp_path):
        # Act
        out = render(tmp_path / "demo")

        # Assert
        assert not (out / ".agent").exists()
        for path in out.rglob("*"):
            assert "{%" not in path.name and "{{" not in path.name, path
            if path.is_file() and path.name != "LICENSE":
                assert "{%" not in path.read_text(), path

    def test_harness_hooks_are_pinned_to_the_requested_tag(self, tmp_path):
        # Act
        out = render(tmp_path / "demo", harness_rev="v9.9.9")

        # Assert
        config = (out / ".pre-commit-config.yaml").read_text()
        assert (
            "repo: https://github.com/danielvogler/agent-harness-config\n    rev: v9.9.9" in config
        )
        for hook in [
            "no-ai-attribution",
            "no-commit-emoji",
            "no-service-account-key",
            "repo-conformance",
        ]:
            assert f"id: {hook}" in config

    def test_plain_repo_without_licence_has_no_python_files(self, tmp_path):
        # Act
        out = render(tmp_path / "plain", python=False, licence="none")

        # Assert
        for name in ["pyproject.toml", ".python-version", "src", "tests", "LICENSE", "NOTICE"]:
            assert not (out / name).exists(), name
        assert "uv run" not in (out / "Makefile").read_text()
