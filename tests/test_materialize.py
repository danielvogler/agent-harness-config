"""tools/materialize.py: placing custom/ into .ecc/ and patching upstream's manifests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import read_json, write_json


def custom_module(**overrides) -> dict:
    module = {
        "id": "custom-skills",
        "kind": "skills",
        "description": "ours",
        "paths": [],
        "targets": ["claude"],
        "dependencies": [],
        "defaultInstall": False,
        "cost": "light",
        "stability": "stable",
        "$source": {"from": "custom/skills", "into": "skills"},
    }
    module.update(overrides)
    return module


def make_overlay(**overrides) -> dict:
    overlay = {
        "removeModules": {"$comment": "doc", "docs-xx": "translation"},
        "addModules": [custom_module()],
        "addProfiles": {
            "custom": {"description": "ours", "modules": ["rules-core", "custom-skills"]}
        },
        "removeMcpServers": {"$comment": "doc", "dropme": "not ours"},
        "addMcpServers": {"ours": {"command": "ours-mcp"}},
        "activateMcpServers": {"ids": ["keep", "ours"]},
        "removeFiles": {"rules/README.md": "context cost"},
    }
    overlay.update(overrides)
    return overlay


@pytest.fixture
def ecc(tmp_path: Path) -> Path:
    """A minimal stand-in for upstream's tree at the pin."""
    root = tmp_path / ".ecc"
    write_json(
        root / "manifests" / "install-modules.json",
        {
            "modules": [
                {"id": "rules-core", "dependencies": []},
                {"id": "docs-xx", "dependencies": []},
                {"id": "skills-a", "dependencies": ["rules-core", "docs-xx"]},
            ]
        },
    )
    write_json(
        root / "manifests" / "install-profiles.json",
        {
            "profiles": {
                "core": {"modules": ["rules-core", "docs-xx"]},
                "docs-only": {"modules": ["docs-xx"]},
            }
        },
    )
    write_json(
        root / "manifests" / "install-components.json",
        {
            "components": [
                {"id": "docs", "modules": ["docs-xx"]},
                {"id": "mixed", "modules": ["rules-core", "docs-xx"]},
            ]
        },
    )
    write_json(
        root / "mcp-configs" / "mcp-servers.json",
        {
            "mcpServers": {"keep": {"command": "k"}, "dropme": {"command": "d"}},
            "_comments": {"dropme-note": "about dropme", "keep-note": "about keep"},
        },
    )
    (root / "rules").mkdir()
    (root / "rules" / "README.md").write_text("upstream readme\n")
    return root


GENERATED = {"custom-skills": ["skills/custom-one"]}


class TestApplyOverlayModules:
    def test_removes_listed_modules_and_prunes_them_from_dependencies(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        modules = read_json(ecc / "manifests" / "install-modules.json")["modules"]
        by_id = {m["id"]: m for m in modules}
        assert "docs-xx" not in by_id
        assert by_id["skills-a"]["dependencies"] == ["rules-core"]

    def test_added_module_uses_generated_paths_and_drops_dollar_keys(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        modules = read_json(ecc / "manifests" / "install-modules.json")["modules"]
        added = next(m for m in modules if m["id"] == "custom-skills")
        assert added["paths"] == ["skills/custom-one"]
        assert not any(key.startswith("$") for key in added)

    def test_rejects_stale_remove_list_naming_module_upstream_dropped(self, materialize, ecc):
        # Arrange
        overlay = make_overlay(removeModules={"docs-xx": "x", "gone-upstream": "y"})

        # Act / Assert
        with pytest.raises(SystemExit, match="overlay is stale.*gone-upstream"):
            materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

    def test_rejects_added_module_reusing_an_upstream_id(self, materialize, ecc):
        # Arrange
        overlay = make_overlay(addModules=[custom_module(id="rules-core")])

        # Act / Assert
        with pytest.raises(SystemExit, match="re-uses existing module ids: rules-core"):
            materialize.apply_overlay(ecc, overlay, {"rules-core": ["skills/x"]}, check=False)

    def test_rejects_added_module_that_resolved_to_no_paths(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act / Assert
        with pytest.raises(SystemExit, match="resolved to no paths"):
            materialize.apply_overlay(ecc, overlay, {"custom-skills": []}, check=False)

    def test_second_run_without_restore_fails_as_stale(self, materialize, ecc):
        # The overlay is a patch against pristine upstream. Applying it twice is what
        # restore_pristine exists to prevent; this pins down why.
        # Arrange
        overlay = make_overlay()
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)
        (ecc / "rules" / "README.md").write_text("back again\n")

        # Act / Assert
        with pytest.raises(SystemExit, match="overlay is stale.*docs-xx"):
            materialize.apply_overlay(ecc, overlay, GENERATED, check=False)


class TestApplyOverlayProfilesAndComponents:
    def test_adds_overlay_profiles(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        profiles = read_json(ecc / "manifests" / "install-profiles.json")["profiles"]
        assert profiles["custom"]["modules"] == ["rules-core", "custom-skills"]

    def test_prunes_removed_modules_from_existing_profiles(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        profiles = read_json(ecc / "manifests" / "install-profiles.json")["profiles"]
        assert profiles["core"]["modules"] == ["rules-core"]

    def test_profile_left_empty_falls_back_to_rules_core(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        profiles = read_json(ecc / "manifests" / "install-profiles.json")["profiles"]
        assert profiles["docs-only"]["modules"] == ["rules-core"]

    def test_drops_components_left_with_no_modules(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        components = read_json(ecc / "manifests" / "install-components.json")["components"]
        assert components == [{"id": "mixed", "modules": ["rules-core"]}]


class TestApplyOverlayFilesAndMcp:
    def test_deletes_files_listed_in_remove_files(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        assert not (ecc / "rules" / "README.md").exists()

    def test_rejects_remove_files_entry_missing_from_tree(self, materialize, ecc):
        # Arrange
        overlay = make_overlay(removeFiles={"rules/moved.md": "gone"})

        # Act / Assert
        with pytest.raises(SystemExit, match="not in the materialized tree: rules/moved.md"):
            materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

    def test_removes_and_adds_mcp_servers_and_their_comments(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

        # Assert
        doc = read_json(ecc / "mcp-configs" / "mcp-servers.json")
        assert set(doc["mcpServers"]) == {"keep", "ours"}
        assert set(doc["_comments"]) == {"keep-note"}

    def test_rejects_added_mcp_server_that_shadows_upstream(self, materialize, ecc):
        # Arrange
        overlay = make_overlay(addMcpServers={"keep": {"command": "mine"}})

        # Act / Assert
        with pytest.raises(SystemExit, match="re-uses existing server ids: keep"):
            materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

    def test_rejects_activation_of_server_not_in_merged_catalog(self, materialize, ecc):
        # Arrange
        overlay = make_overlay(activateMcpServers={"ids": ["keep", "typo"]})

        # Act / Assert
        with pytest.raises(SystemExit, match="not in the merged catalog: typo"):
            materialize.apply_overlay(ecc, overlay, GENERATED, check=False)

    def test_check_mode_writes_nothing(self, materialize, ecc):
        # Arrange
        overlay = make_overlay()
        before = {p: p.read_text() for p in ecc.rglob("*") if p.is_file()}

        # Act
        materialize.apply_overlay(ecc, overlay, GENERATED, check=True)

        # Assert
        after = {p: p.read_text() for p in ecc.rglob("*") if p.is_file()}
        assert after == before


class TestPlaceCustom:
    @pytest.fixture
    def repo(self, materialize, tmp_path: Path, monkeypatch) -> Path:
        root = tmp_path / "repo"
        skills = root / "custom" / "skills"
        (skills / "custom-one").mkdir(parents=True)
        (skills / "custom-one" / "SKILL.md").write_text("---\nname: custom-one\n---\n")
        (skills / "custom-one" / ".DS_Store").write_text("")
        (skills / "skills-lock.json").write_text("{}\n")
        (skills / ".DS_Store").write_text("")
        monkeypatch.setattr(materialize, "REPO", root)
        return root

    def test_copies_entries_and_returns_their_manifest_paths(self, materialize, repo, ecc):
        # Arrange
        overlay = make_overlay(
            addModules=[
                custom_module(
                    **{
                        "$source": {
                            "from": "custom/skills",
                            "into": "skills",
                            "ignore": ["skills-lock.json"],
                        }
                    }
                )
            ]
        )

        # Act
        generated = materialize.place_custom(ecc, overlay, check=False)

        # Assert
        assert generated == {"custom-skills": ["skills/custom-one"]}
        assert (ecc / "skills" / "custom-one" / "SKILL.md").exists()
        assert not (ecc / "skills" / "custom-one" / ".DS_Store").exists()
        assert not (ecc / "skills" / "skills-lock.json").exists()

    def test_refuses_to_overwrite_upstream_entry_with_same_name(self, materialize, repo, ecc):
        # Arrange
        (ecc / "skills" / "custom-one").mkdir(parents=True)
        overlay = make_overlay()

        # Act / Assert
        with pytest.raises(SystemExit, match="refusing to overwrite upstream skills/custom-one"):
            materialize.place_custom(ecc, overlay, check=False)

    def test_cherry_pick_module_declares_paths_without_copying(self, materialize, repo, ecc):
        # Arrange
        pick = custom_module(id="custom-pick", paths=["skills/upstream-a"])
        del pick["$source"]
        overlay = make_overlay(addModules=[pick])

        # Act
        generated = materialize.place_custom(ecc, overlay, check=False)

        # Assert
        assert generated == {"custom-pick": ["skills/upstream-a"]}
        assert not (ecc / "skills").exists()

    def test_check_mode_reports_paths_but_copies_nothing(self, materialize, repo, ecc):
        # Arrange
        overlay = make_overlay()

        # Act
        generated = materialize.place_custom(ecc, overlay, check=True)

        # Assert
        assert "skills/custom-one" in generated["custom-skills"]
        assert not (ecc / "skills").exists()


class FakeGit:
    """Records git invocations made through materialize.run and answers rev-parse."""

    def __init__(self, head: str = "") -> None:
        self.head = head
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], cwd: Path | None = None) -> str:
        self.calls.append(cmd)
        return self.head if cmd[:2] == ["git", "rev-parse"] else ""

    def subcommands(self) -> list[str]:
        return [c[1] for c in self.calls]


PIN = "a" * 40


class TestCloneOrUpdate:
    def test_does_nothing_when_checkout_already_at_pin(self, materialize, tmp_path, monkeypatch):
        # Arrange
        (tmp_path / ".git").mkdir()
        fake = FakeGit(head=PIN)
        monkeypatch.setattr(materialize, "run", fake)

        # Act
        materialize.clone_or_update(tmp_path, "https://example.invalid/ecc.git", PIN, check=False)

        # Assert
        assert fake.subcommands() == ["rev-parse"]

    def test_fetches_and_checks_out_pin_when_checkout_is_elsewhere(
        self, materialize, tmp_path, monkeypatch
    ):
        # Arrange
        (tmp_path / ".git").mkdir()
        fake = FakeGit(head="b" * 40)
        monkeypatch.setattr(materialize, "run", fake)

        # Act
        materialize.clone_or_update(tmp_path, "https://example.invalid/ecc.git", PIN, check=False)

        # Assert
        assert fake.subcommands() == ["rev-parse", "fetch", "checkout", "clean"]
        assert fake.calls[1][-1] == PIN and fake.calls[2][-1] == PIN

    def test_check_mode_never_moves_the_checkout(self, materialize, tmp_path, monkeypatch):
        # Arrange
        (tmp_path / ".git").mkdir()
        fake = FakeGit(head="b" * 40)
        monkeypatch.setattr(materialize, "run", fake)

        # Act
        materialize.clone_or_update(tmp_path, "https://example.invalid/ecc.git", PIN, check=True)

        # Assert
        assert fake.subcommands() == ["rev-parse"]

    def test_clones_then_checks_out_pin_when_no_checkout_exists(
        self, materialize, tmp_path, monkeypatch
    ):
        # Arrange
        target = tmp_path / ".ecc"
        fake = FakeGit()
        monkeypatch.setattr(materialize, "run", fake)

        # Act
        materialize.clone_or_update(target, "https://example.invalid/ecc.git", PIN, check=False)

        # Assert
        assert fake.subcommands() == ["clone", "checkout"]
        assert fake.calls[1][-1] == PIN


class TestRestorePristine:
    def test_skips_a_tree_that_is_not_a_git_checkout(self, materialize, tmp_path, monkeypatch):
        # Arrange
        fake = FakeGit()
        monkeypatch.setattr(materialize, "run", fake)

        # Act
        materialize.restore_pristine(tmp_path, check=False)

        # Assert
        assert fake.calls == []

    def test_restores_tracked_content_and_sweeps_copied_files(
        self, materialize, tmp_path, monkeypatch
    ):
        # Arrange
        (tmp_path / ".git").mkdir()
        fake = FakeGit()
        monkeypatch.setattr(materialize, "run", fake)

        # Act
        materialize.restore_pristine(tmp_path, check=False)

        # Assert
        checkout, clean = fake.calls
        assert checkout[:4] == ["git", "checkout", "--force", "HEAD"]
        assert {"manifests", "mcp-configs", "skills", "commands", "rules"} <= set(checkout)
        assert clean[1] == "clean" and "custom" in clean


class TestRunAndLoadJson:
    def test_run_raises_with_stderr_when_command_fails(self, materialize, monkeypatch):
        # Arrange
        failed = SimpleNamespace(returncode=128, stdout="", stderr="fatal: bad object")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: failed)

        # Act / Assert
        with pytest.raises(SystemExit, match=r"command failed: git fetch\nfatal: bad object"):
            materialize.run(["git", "fetch"])

    def test_run_returns_stripped_stdout_on_success(self, materialize, monkeypatch):
        # Arrange
        ok = SimpleNamespace(returncode=0, stdout="abc\n", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: ok)

        # Act
        out = materialize.run(["git", "rev-parse", "HEAD"])

        # Assert
        assert out == "abc"

    def test_load_json_names_missing_file_relative_to_repo(
        self, materialize, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(materialize, "REPO", tmp_path)

        # Act / Assert
        with pytest.raises(SystemExit, match="missing: upstream.json"):
            materialize.load_json(tmp_path / "upstream.json")

    def test_load_json_rejects_invalid_json(self, materialize, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(materialize, "REPO", tmp_path)
        (tmp_path / "upstream.json").write_text("{not json")

        # Act / Assert
        with pytest.raises(SystemExit, match="invalid JSON in upstream.json"):
            materialize.load_json(tmp_path / "upstream.json")


def fake_repo(root: Path) -> Path:
    write_json(
        root / "upstream.json",
        {
            "upstream": {
                "repo": "https://example.invalid/ecc.git",
                "sha": PIN,
                "pinnedOn": "2026-09-12",
            }
        },
    )
    write_json(root / "overlay" / "manifest-overlay.json", make_overlay())
    skill = root / "custom" / "skills" / "custom-one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: custom-one\n---\n")
    return root


class TestMain:
    def test_skip_clone_run_places_custom_and_patches_manifests(
        self, materialize, ecc, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(materialize, "REPO", fake_repo(tmp_path / "repo"))
        monkeypatch.setattr("sys.argv", ["materialize.py", "--skip-clone", "--ecc-dir", str(ecc)])

        # Act
        code = materialize.main()

        # Assert
        assert code == 0
        assert (ecc / "skills" / "custom-one" / "SKILL.md").exists()
        profiles = read_json(ecc / "manifests" / "install-profiles.json")["profiles"]
        assert profiles["custom"]["modules"] == ["rules-core", "custom-skills"]

    def test_refuses_a_directory_that_is_not_an_ecc_checkout(
        self, materialize, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(materialize, "REPO", fake_repo(tmp_path / "repo"))
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr("sys.argv", ["materialize.py", "--skip-clone", "--ecc-dir", str(empty)])

        # Act / Assert
        with pytest.raises(SystemExit, match="does not look like an ECC checkout"):
            materialize.main()
