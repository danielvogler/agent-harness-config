"""tools/setup-user.py: the settings it writes into ~/.claude/settings.json."""

from __future__ import annotations

from pathlib import Path

from conftest import read_json, write_json


def settings_path(home: Path) -> Path:
    return home / ".claude" / "settings.json"


def install_state_path(home: Path) -> Path:
    return home / ".claude" / "ecc" / "install-state.json"


def operation(kind: str, destination: Path) -> dict:
    return {
        "kind": kind,
        "moduleId": "some-module",
        "sourceRelativePath": "skills/some-module/SKILL.md",
        "destinationPath": str(destination),
        "strategy": "overwrite",
        "ownership": "managed",
        "scaffoldOnly": False,
    }


def install_state(operations: list[dict]) -> dict:
    return {
        "schemaVersion": "ecc.install.v1",
        "installedAt": "2026-09-01T12:00:00Z",
        "target": {"id": "claude-home", "target": "claude", "kind": "home"},
        "request": {
            "profile": "custom",
            "modules": [],
            "includeComponents": [],
            "excludeComponents": [],
            "legacyLanguages": [],
            "legacyMode": False,
        },
        "resolution": {"selectedModules": [], "skippedModules": []},
        "source": {"repoCommit": "a" * 40, "manifestVersion": 1},
        "operations": operations,
    }


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


class TestPermissions:
    def test_no_rule_mixes_a_wildcard_with_the_legacy_prefix_suffix(self, setup_user):
        # Claude Code reads `Bash(a * b:*)` as the literal prefix "a * b", so it never matches.
        mixed = [
            rule
            for rule in setup_user.ALLOW + setup_user.DENY
            if rule.endswith(":*)") and "*" in rule[: -len(":*)")]
        ]

        assert mixed == []

    def test_denies_gcloud_delete_with_a_wildcard(self, setup_user):
        assert "Bash(gcloud * delete*)" in setup_user.DENY

    def test_replaces_a_retired_rule_left_by_an_earlier_run(self, setup_user, tmp_path):
        # Arrange
        write_json(
            settings_path(tmp_path),
            {"permissions": {"deny": ["Bash(gcloud * delete:*)", "Bash(my-own:*)"]}},
        )

        # Act
        setup_user.setup_permissions(dry=False)

        # Assert
        deny = read_json(settings_path(tmp_path))["permissions"]["deny"]
        assert "Bash(gcloud * delete:*)" not in deny
        assert "Bash(gcloud * delete*)" in deny
        assert "Bash(my-own:*)" in deny
        assert "permissions.deny: -1 retired entries" in setup_user.changes

    def test_dry_run_reports_a_retired_rule_but_writes_nothing(self, setup_user, tmp_path):
        # Arrange
        before = {"permissions": {"deny": ["Bash(gcloud * delete:*)"]}}
        write_json(settings_path(tmp_path), before)

        # Act
        setup_user.setup_permissions(dry=True)

        # Assert
        assert read_json(settings_path(tmp_path)) == before
        assert "permissions.deny: -1 retired entries" in setup_user.changes


class TestPruneStaleInstallState:
    def test_drops_a_copy_file_record_whose_destination_is_gone(self, setup_user, tmp_path):
        # Arrange
        gone = tmp_path / ".claude" / "commands" / "dropped.md"
        state_path = install_state_path(tmp_path)
        write_json(state_path, install_state([operation("copy-file", gone)]))

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert read_json(state_path)["operations"] == []
        assert any("pruned 1 stale record" in c for c in setup_user.changes)
        assert "dropped.md" in setup_user.changes[0]

    def test_keeps_a_record_whose_destination_still_exists(self, setup_user, tmp_path):
        # Arrange
        still_there = tmp_path / ".claude" / "commands" / "kept.md"
        still_there.parent.mkdir(parents=True)
        still_there.write_text("x\n")
        state_path = install_state_path(tmp_path)
        original = install_state([operation("copy-file", still_there)])
        write_json(state_path, original)

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert read_json(state_path) == original
        assert setup_user.changes == []

    def test_never_prunes_a_remove_operation_for_its_missing_destination(
        self, setup_user, tmp_path
    ):
        # Arrange — a 'remove' operation records something that should NOT exist;
        # a missing destination there is success, not staleness.
        gone = tmp_path / ".claude" / "legacy-file"
        state_path = install_state_path(tmp_path)
        original = install_state([operation("remove", gone)])
        write_json(state_path, original)

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert read_json(state_path) == original
        assert setup_user.changes == []

    def test_never_prunes_merge_json_operations_for_their_missing_destination(
        self, setup_user, tmp_path
    ):
        # Arrange — merge-json/update-claude-settings target a shared file that is
        # expected to always exist; only copy-file/render-template are prunable.
        missing = tmp_path / ".claude" / "settings.json"
        state_path = install_state_path(tmp_path)
        original = install_state([operation("merge-json", missing)])
        write_json(state_path, original)

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert read_json(state_path) == original
        assert setup_user.changes == []

    def test_dry_run_reports_but_writes_nothing(self, setup_user, tmp_path):
        # Arrange
        gone = tmp_path / ".claude" / "commands" / "dropped.md"
        state_path = install_state_path(tmp_path)
        original = install_state([operation("copy-file", gone)])
        write_json(state_path, original)

        # Act
        setup_user.prune_stale_install_state(dry=True)

        # Assert
        assert read_json(state_path) == original
        assert any("pruned 1 stale record" in c for c in setup_user.changes)

    def test_backs_up_before_writing(self, setup_user, tmp_path):
        # Arrange
        gone = tmp_path / ".claude" / "commands" / "dropped.md"
        state_path = install_state_path(tmp_path)
        write_json(state_path, install_state([operation("copy-file", gone)]))

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert state_path.with_suffix(".json.bak").exists()

    def test_missing_install_state_file_is_skipped_without_error(self, setup_user, tmp_path):
        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert setup_user.changes == []
        assert setup_user.skipped == []

    def test_invalid_json_is_left_alone_and_reported(self, setup_user, tmp_path):
        # Arrange
        state_path = install_state_path(tmp_path)
        state_path.parent.mkdir(parents=True)
        state_path.write_text("{not json")

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert state_path.read_text() == "{not json"
        assert any("is not valid JSON" in s for s in setup_user.skipped)

    def test_covers_every_home_target_install_state_file(self, setup_user, tmp_path):
        # Arrange
        codex_gone = tmp_path / ".codex" / "commands" / "dropped.md"
        codex_state = tmp_path / ".codex" / "ecc-install-state.json"
        write_json(codex_state, install_state([operation("copy-file", codex_gone)]))

        # Act
        setup_user.prune_stale_install_state(dry=False)

        # Assert
        assert read_json(codex_state)["operations"] == []


class TestHooks:
    def install_ecc_scripts(self, home: Path) -> None:
        hooks = home / ".claude" / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "block-no-verify.js").write_text("// stub\n")

    def test_wires_the_three_guards(self, setup_user, tmp_path):
        # Arrange
        self.install_ecc_scripts(tmp_path)

        # Act
        setup_user.setup_hooks(dry=False)

        # Assert
        commands = [
            h["command"]
            for matcher in read_json(settings_path(tmp_path))["hooks"]["PreToolUse"]
            for h in matcher["hooks"]
        ]
        assert any("block-no-verify.js" in c for c in commands)
        assert any("config-protection.js" in c for c in commands)
        assert any("block-commit-emoji.py" in c for c in commands)

    def test_copies_the_emoji_guard_next_to_the_ecc_scripts(self, setup_user, tmp_path):
        # Arrange
        self.install_ecc_scripts(tmp_path)

        # Act
        setup_user.setup_hooks(dry=False)

        # Assert
        copied = tmp_path / ".claude" / "scripts" / "hooks" / "block-commit-emoji.py"
        source = setup_user.REPO / "tools" / "hooks" / "block-commit-emoji.py"
        assert copied.read_text() == source.read_text()

    def test_dry_run_copies_nothing(self, setup_user, tmp_path):
        # Arrange
        self.install_ecc_scripts(tmp_path)

        # Act
        setup_user.setup_hooks(dry=True)

        # Assert
        assert not (tmp_path / ".claude" / "scripts" / "hooks" / "block-commit-emoji.py").exists()
