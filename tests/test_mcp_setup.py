"""mcp-setup.py: which values end up stored in the Claude config, and which servers are wanted."""

from __future__ import annotations

from pathlib import Path

import pytest

TOKEN_SPEC = {
    "command": "some-server",
    "args": ["stdio"],
    "personalEnv": ["SERVICE_URL", "SERVICE_TOKEN"],
}


@pytest.fixture
def on_path(mcp_setup, monkeypatch):
    """Every command counts as installed unless a test says otherwise."""
    monkeypatch.setattr(mcp_setup.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
    return mcp_setup


class TestSecretsStayInTheShell:
    def test_secret_from_the_shell_is_not_stored_in_the_registration(self, on_path, monkeypatch):
        # Arrange
        monkeypatch.setenv("SERVICE_URL", "https://example.org")
        monkeypatch.setenv("SERVICE_TOKEN", "shell-value")  # pragma: allowlist secret

        # Act
        cmd, problems, _, resolved = on_path.build_command("svc", TOKEN_SPEC, {})

        # Assert
        assert problems == []
        assert "--env" in cmd and "SERVICE_URL=https://example.org" in cmd
        assert not any("SERVICE_TOKEN" in part for part in cmd)
        assert resolved == {"SERVICE_URL"}

    def test_secret_only_in_env_file_is_refused_with_the_fix(self, on_path, monkeypatch):
        # Arrange: loaded from .env by make mcp, so the server would never see it
        monkeypatch.setenv("SERVICE_URL", "https://example.org")
        monkeypatch.setenv("SERVICE_TOKEN", "file-value")  # pragma: allowlist secret

        # Act
        cmd, problems, _, _ = on_path.build_command(
            "svc", TOKEN_SPEC, {}, file_keys=frozenset({"SERVICE_TOKEN"})
        )

        # Assert
        assert len(problems) == 1
        assert "SERVICE_TOKEN" in problems[0] and "shell" in problems[0]
        assert not any("file-value" in part for part in cmd)

    def test_optional_secret_only_in_env_file_is_a_note(self, on_path, monkeypatch):
        # Arrange
        spec = {**TOKEN_SPEC, "optionalEnv": ["SERVICE_TOKEN"]}
        monkeypatch.setenv("SERVICE_URL", "https://example.org")
        monkeypatch.setenv("SERVICE_TOKEN", "file-value")  # pragma: allowlist secret

        # Act
        _, problems, notes, _ = on_path.build_command(
            "svc", spec, {}, file_keys=frozenset({"SERVICE_TOKEN"})
        )

        # Assert
        assert problems == []
        assert len(notes) == 1 and "SERVICE_TOKEN" in notes[0]

    def test_non_secret_from_env_file_is_still_stored(self, on_path, monkeypatch):
        # Arrange
        monkeypatch.setenv("SERVICE_URL", "https://example.org")
        monkeypatch.setenv("SERVICE_TOKEN", "shell-value")  # pragma: allowlist secret

        # Act
        cmd, problems, _, _ = on_path.build_command(
            "svc", TOKEN_SPEC, {}, file_keys=frozenset({"SERVICE_URL"})
        )

        # Assert
        assert problems == []
        assert "SERVICE_URL=https://example.org" in cmd


class TestCommandOnPath:
    def test_missing_command_is_a_problem_naming_how_to_install(self, mcp_setup, monkeypatch):
        # Arrange
        monkeypatch.setattr(mcp_setup.shutil, "which", lambda cmd: None)
        monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "x")  # pragma: allowlist secret
        spec = {
            "command": "github-mcp-server",
            "args": ["stdio"],
            "personalEnv": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        }

        # Act
        _, problems, _, _ = mcp_setup.build_command("github", spec, {})

        # Assert
        assert len(problems) == 1
        assert "github-mcp-server" in problems[0] and "brew install" in problems[0]


class TestDriftNotes:
    def test_flags_a_secret_stored_in_an_existing_registration(self, mcp_setup, monkeypatch):
        # Arrange: the pre-change registration, with the token typed into the config
        monkeypatch.setattr(
            mcp_setup, "registered_env_keys", lambda name: {"SERVICE_URL", "SERVICE_TOKEN"}
        )

        # Act
        notes = mcp_setup.drift_notes("svc", {"SERVICE_URL"})

        # Assert
        assert len(notes) == 1
        assert "SERVICE_TOKEN" in notes[0] and "claude mcp remove svc -s user" in notes[0]

    def test_silent_when_registration_matches(self, mcp_setup, monkeypatch):
        # Arrange
        monkeypatch.setattr(mcp_setup, "registered_env_keys", lambda name: {"SERVICE_URL"})

        # Act
        notes = mcp_setup.drift_notes("svc", {"SERVICE_URL"})

        # Assert
        assert notes == []

    def test_still_reports_a_value_that_now_resolves(self, mcp_setup, monkeypatch):
        # Arrange
        monkeypatch.setattr(mcp_setup, "registered_env_keys", lambda name: {"SERVICE_URL"})

        # Act
        notes = mcp_setup.drift_notes("svc", {"SERVICE_URL", "JIRA_URL"})

        # Assert
        assert len(notes) == 1 and "JIRA_URL" in notes[0]


class TestWantedIds:
    def test_adds_opt_in_servers_after_the_agreed_ones_without_duplicates(self, mcp_setup):
        # Act
        ids = mcp_setup.wanted_ids(["context7", "miro"], ["github,miro", "github"])

        # Assert
        assert ids == ["context7", "miro", "github"]

    def test_agreed_ones_alone_when_nothing_is_added(self, mcp_setup):
        # Act / Assert
        assert mcp_setup.wanted_ids(["context7"], []) == ["context7"]


class TestLoadEnvFile:
    def test_returns_the_keys_it_set_and_never_overrides_the_shell(
        self, mcp_setup, monkeypatch, tmp_path: Path
    ):
        # Arrange
        env = tmp_path / ".env"
        env.write_text("FROM_FILE=a\nALREADY_SET=b\n# comment\nEMPTY=\n")
        monkeypatch.delenv("FROM_FILE", raising=False)
        monkeypatch.setenv("ALREADY_SET", "shell")

        # Act
        keys = mcp_setup.load_env_file(env)

        # Assert
        assert keys == frozenset({"FROM_FILE"})
        assert mcp_setup.os.environ["ALREADY_SET"] == "shell"
