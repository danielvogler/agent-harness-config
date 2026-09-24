"""Cheap, high-value checks on the smaller scripts: secret redaction and text transforms."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestMcpSetupRedact:
    @pytest.mark.parametrize(
        "key",
        [
            "JIRA_TOKEN",
            "CLIENT_SECRET",
            "DB_PASSWORD",
            "GCP_CREDENTIALS",
            "LIBRARY_API_KEY",
        ],
    )
    def test_masks_values_of_credential_like_env_keys(self, mcp_setup, key):
        # Arrange
        cmd = ["claude", "mcp", "add", "--env", f"{key}=s3cr3t-value"]  # pragma: allowlist secret

        # Act
        printed = mcp_setup.redact(cmd)

        # Assert
        assert "s3cr3t-value" not in printed
        assert printed.endswith(f"{key}=***")

    def test_leaves_non_secret_arguments_readable(self, mcp_setup):
        # Arrange
        cmd = ["claude", "mcp", "add", "--env", "GCP_PROJECT=my-project", "bigquery"]

        # Act
        printed = mcp_setup.redact(cmd)

        # Assert
        assert printed == "claude mcp add --env GCP_PROJECT=my-project bigquery"


class TestMcpSetupSubstitute:
    def test_replaces_resolved_placeholders(self, mcp_setup):
        # Act
        text, problems = mcp_setup.substitute(
            "--project=YOUR_GCP_PROJECT_HERE", {"YOUR_GCP_PROJECT_HERE": "my-project"}
        )

        # Assert
        assert (text, problems) == ("--project=my-project", [])

    def test_reports_unresolved_placeholder_and_leaves_text(self, mcp_setup):
        # Act
        text, problems = mcp_setup.substitute(
            "--project=YOUR_GCP_PROJECT_HERE", {"YOUR_GCP_PROJECT_HERE": None}
        )

        # Assert
        assert text == "--project=YOUR_GCP_PROJECT_HERE"
        assert len(problems) == 1 and "could not be resolved" in problems[0]


class TestContextCost:
    def test_separates_always_on_rules_from_path_scoped_ones(self, context_cost, tmp_path: Path):
        # Arrange
        (tmp_path / "always.md").write_text("# always\n")
        (tmp_path / "scoped.md").write_text("---\npaths:\n  - '**/*.py'\n---\n# scoped\n")
        (tmp_path / "other-frontmatter.md").write_text("---\ndescription: x\n---\n")

        # Act
        always, scoped = context_cost.scan_rules(tmp_path)

        # Assert
        assert sorted(str(p) for _, p in always) == ["always.md", "other-frontmatter.md"]
        assert [str(p) for _, p in scoped] == ["scoped.md"]

    def test_skill_cost_counts_frontmatter_only(self, context_cost, tmp_path: Path):
        # Arrange
        skill = tmp_path / "one"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: one\n---\n" + "body " * 1000)

        # Act
        found = context_cost.scan_skills(tmp_path)

        # Assert
        assert found == [(len("name: one"), "one")]


class TestConventionsSkill:
    def test_body_strips_frontmatter_and_lead_quote_and_demotes_headings(
        self, conventions, tmp_path: Path
    ):
        # Arrange
        rule = tmp_path / "gcp.md"
        rule.write_text(
            "---\npaths:\n  - '**/*.tf'\n---\n"
            "> Scoping note for maintainers.\n> Second line.\n\n"
            "# GCP\n\n## Credentials\n\nUse ADC.\n\n> A quote in the body stays.\n"
        )

        # Act
        body = conventions.body_of(rule)

        # Assert
        assert body == "## GCP\n\n### Credentials\n\nUse ADC.\n\n> A quote in the body stays."
