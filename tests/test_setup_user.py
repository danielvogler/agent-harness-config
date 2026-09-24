"""tools/setup-user.py: the settings it writes into ~/.claude/settings.json."""

from __future__ import annotations

from pathlib import Path

from conftest import read_json, write_json


def settings_path(home: Path) -> Path:
    return home / ".claude" / "settings.json"


class TestAttribution:
    def test_turns_attribution_off_when_it_is_unset(self, setup_user, tmp_path):
        # Arrange
        write_json(settings_path(tmp_path), {"permissions": {"allow": []}})

        # Act
        setup_user.setup_attribution(dry=False)

        # Assert
        settings = read_json(settings_path(tmp_path))
        assert settings["attribution"] == {"commit": "", "pr": ""}
        assert settings["permissions"] == {"allow": []}
        assert "attribution: turned off for commits and PRs" in setup_user.changes

    def test_leaves_an_explicit_choice_alone(self, setup_user, tmp_path):
        # Arrange
        chosen = {"commit": "Co-Authored-By: someone", "pr": ""}
        write_json(settings_path(tmp_path), {"attribution": chosen})

        # Act
        setup_user.setup_attribution(dry=False)

        # Assert
        assert read_json(settings_path(tmp_path))["attribution"] == chosen
        assert setup_user.changes == []

    def test_reports_nothing_to_do_when_already_off(self, setup_user, tmp_path):
        # Arrange
        write_json(settings_path(tmp_path), {"attribution": {"commit": "", "pr": ""}})

        # Act
        setup_user.setup_attribution(dry=False)

        # Assert
        assert setup_user.changes == []
        assert "attribution: already off" in setup_user.skipped

    def test_dry_run_writes_nothing(self, setup_user, tmp_path):
        # Arrange
        write_json(settings_path(tmp_path), {})

        # Act
        setup_user.setup_attribution(dry=True)

        # Assert
        assert "attribution" not in read_json(settings_path(tmp_path))
        assert "attribution: turned off for commits and PRs" in setup_user.changes

    def test_creates_settings_when_none_exist(self, setup_user, tmp_path):
        # Act
        setup_user.setup_attribution(dry=False)

        # Assert
        assert read_json(settings_path(tmp_path)) == {"attribution": {"commit": "", "pr": ""}}
