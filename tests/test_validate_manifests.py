"""tools/validate-manifests.py: the pre-commit gate on the pin, the overlay and custom/."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import write_json

VALID_SHA = "0123456789abcdef" * 2 + "01234567"


@pytest.fixture
def repo(validate, tmp_path: Path, monkeypatch) -> Path:
    """A fake checkout with one custom skill, and no materialized .ecc/."""
    root = tmp_path / "repo"
    add_skill(root, "custom-one")
    monkeypatch.setattr(validate, "REPO", root)
    monkeypatch.setattr(validate, "ECC", root / ".ecc")
    # The license check reads THIRD_PARTY_LICENSES/ beside REPO; point it at the fake too.
    monkeypatch.setattr(validate, "LICENSES", root / "THIRD_PARTY_LICENSES", raising=False)
    return root


def add_skill(root: Path, directory: str, frontmatter_name: str | None = None) -> Path:
    skill = root / "custom" / "skills" / directory
    skill.mkdir(parents=True, exist_ok=True)
    name = frontmatter_name or directory
    (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n\nbody\n")
    return skill


def module(**overrides) -> dict:
    entry = {
        "id": "custom-skills",
        "kind": "skills",
        "description": "ours",
        "paths": ["custom/skills"],
        "targets": ["claude", "codex"],
        "dependencies": [],
        "defaultInstall": False,
        "cost": "light",
        "stability": "stable",
        "$source": {"from": "custom/skills", "into": "skills"},
    }
    entry.update(overrides)
    return entry


def overlay(*modules: dict, profile: list[str] | None = None, remove: dict | None = None) -> dict:
    added = list(modules) or [module()]
    return {
        "removeModules": remove if remove is not None else {"$comment": "x", "database": "no"},
        "addModules": added,
        "addProfiles": {
            "custom": {"modules": profile or ["rules-core"] + [m.get("id", "") for m in added]}
        },
    }


class TestCheckPin:
    def test_accepts_full_sha_https_repo_and_date(self, validate):
        # Arrange
        pin = {
            "upstream": {"sha": VALID_SHA, "repo": "https://x/ecc.git", "pinnedOn": "2026-09-12"}
        }

        # Act
        validate.check_pin(pin)

        # Assert
        assert validate.errors == []

    @pytest.mark.parametrize("sha", ["0123456", VALID_SHA.upper(), "main", ""])
    def test_rejects_anything_but_a_full_lowercase_sha(self, validate, sha):
        # Arrange
        pin = {"upstream": {"sha": sha, "repo": "https://x/ecc.git", "pinnedOn": "2026-09-12"}}

        # Act
        validate.check_pin(pin)

        # Assert
        assert any("full 40-character commit hash" in e for e in validate.errors)

    def test_rejects_non_https_repo_and_missing_pinned_on(self, validate):
        # Arrange
        pin = {"upstream": {"sha": VALID_SHA, "repo": "git@github.com:x/ecc.git"}}

        # Act
        validate.check_pin(pin)

        # Assert
        assert len(validate.errors) == 2
        assert any("https clone URL" in e for e in validate.errors)
        assert any("pinnedOn is required" in e for e in validate.errors)


class TestCheckOverlayModuleFields:
    def test_accepts_a_complete_module_with_dollar_keys(self, validate, repo):
        # Arrange
        doc = overlay(module(**{"$comment": "ours"}))

        # Act
        validate.check_overlay(doc)

        # Assert
        assert validate.errors == []

    @pytest.mark.parametrize(
        "field",
        sorted(
            [
                "id",
                "kind",
                "description",
                "paths",
                "targets",
                "dependencies",
                "defaultInstall",
                "cost",
                "stability",
            ]
        ),
    )
    def test_rejects_module_missing_any_of_the_nine_required_fields(self, validate, repo, field):
        # Arrange
        entry = module()
        del entry[field]

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert any(f"missing required field(s): {field}" in e for e in validate.errors)

    def test_rejects_module_with_field_the_upstream_schema_forbids(self, validate, repo):
        # Arrange
        entry = module(owner="someone")

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert any("unknown field(s): owner" in e for e in validate.errors)

    @pytest.mark.parametrize(
        "field, value, message",
        [
            ("kind", "plugins", "invalid kind"),
            ("cost", "free", "invalid cost"),
            ("stability", "alpha", "invalid stability"),
            ("targets", ["claude", "vscode"], "unknown harness 'vscode'"),
            ("targets", [], "declares no targets"),
            ("id", "Custom_Skills", "must match ^[a-z0-9-]+$"),
        ],
    )
    def test_rejects_invalid_enum_and_id_values(self, validate, repo, field, value, message):
        # Arrange
        entry = module(**{field: value})

        # Act
        validate.check_overlay(overlay(entry, profile=["rules-core"]))

        # Assert
        assert any(message in e for e in validate.errors), validate.errors

    def test_rejects_duplicate_module_ids(self, validate, repo):
        # Arrange
        doc = overlay(module(), module())

        # Act
        validate.check_overlay(doc)

        # Assert
        assert any("duplicate module id 'custom-skills'" in e for e in validate.errors)


class TestCheckOverlaySource:
    def test_rejects_source_into_a_directory_no_adapter_remaps(self, validate, repo):
        # Arrange
        entry = module(**{"$source": {"from": "custom/skills", "into": "custom/skills"}})

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert any("must start with" in e for e in validate.errors)

    def test_accepts_namespaced_subdirectory_of_a_content_directory(self, validate, repo):
        # Arrange
        entry = module(**{"$source": {"from": "custom/skills", "into": "rules/custom"}})

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert validate.errors == []

    def test_rejects_source_that_is_not_a_directory(self, validate, repo):
        # Arrange
        entry = module(**{"$source": {"from": "custom/nope", "into": "skills"}})

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert any("'custom/nope' is not a directory" in e for e in validate.errors)

    def test_rejects_source_with_nothing_left_after_ignores(self, validate, repo):
        # Arrange
        entry = module(
            **{"$source": {"from": "custom/skills", "into": "skills", "ignore": ["custom-one"]}}
        )

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert any("'custom/skills' is empty" in e for e in validate.errors)

    def test_rejects_module_with_neither_source_nor_paths(self, validate, repo):
        # Arrange
        entry = module(paths=[])
        del entry["$source"]

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert any("needs either a $source" in e for e in validate.errors)

    def test_cherry_pick_is_only_noted_when_ecc_is_not_materialized(self, validate, repo):
        # Arrange
        entry = module(id="custom-pick", paths=["skills/upstream-a"])
        del entry["$source"]

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert validate.errors == []
        assert any("not verified" in n for n in validate.notes)

    def test_rejects_cherry_pick_of_path_missing_upstream(self, validate, repo):
        # Arrange
        (repo / ".ecc" / "skills" / "upstream-a").mkdir(parents=True)
        entry = module(id="custom-pick", paths=["skills/upstream-a", "skills/renamed"])
        del entry["$source"]

        # Act
        validate.check_overlay(overlay(entry))

        # Assert
        assert validate.errors == [
            "overlay: module 'custom-pick' cherry-picks 'skills/renamed', which does not "
            "exist upstream. Re-check it against the pinned SHA."
        ]


class TestCheckOverlayProfiles:
    def test_rejects_profile_naming_a_module_the_overlay_removes(self, validate, repo):
        # Arrange
        doc = overlay(profile=["rules-core", "database"])

        # Act
        validate.check_overlay(doc)

        # Assert
        assert any("names 'database', which the overlay also removes" in e for e in validate.errors)

    def test_rejects_profile_naming_an_unknown_module(self, validate, repo):
        # Arrange
        doc = overlay(profile=["rules-core", "custom-typo"])

        # Act
        validate.check_overlay(doc)

        # Assert
        assert any("unknown module 'custom-typo'" in e for e in validate.errors)

    def test_rejects_profile_with_no_modules(self, validate, repo):
        # Arrange
        doc = overlay()
        doc["addProfiles"]["empty"] = {"modules": []}

        # Act
        validate.check_overlay(doc)

        # Assert
        assert any("profile 'empty' lists no modules" in e for e in validate.errors)


class TestCheckCustomSkills:
    def test_accepts_skill_whose_name_matches_its_directory(self, validate, repo):
        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == []

    def test_rejects_frontmatter_name_that_differs_from_directory(self, validate, repo):
        # Arrange
        add_skill(repo, "custom-two", frontmatter_name="custom-2")

        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == [
            "custom/skills/custom-two/SKILL.md: frontmatter name is 'custom-2', "
            "which must match the directory name"
        ]

    def test_rejects_skill_directory_without_skill_md(self, validate, repo):
        # Arrange
        (repo / "custom" / "skills" / "empty").mkdir()

        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == ["custom/skills/empty/: no SKILL.md"]

    def test_rejects_skill_md_without_frontmatter(self, validate, repo):
        # Arrange
        skill = repo / "custom" / "skills" / "bare"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# no frontmatter\n")

        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == ["custom/skills/bare/SKILL.md: no YAML frontmatter"]

    def test_rejects_frontmatter_without_name(self, validate, repo):
        # Arrange
        skill = repo / "custom" / "skills" / "nameless"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\ndescription: x\n---\n")

        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == ["custom/skills/nameless/SKILL.md: frontmatter has no `name`"]

    def test_ignores_files_beside_skill_directories(self, validate, repo):
        # Arrange
        (repo / "custom" / "skills" / "skills-lock.json").write_text("{}\n")

        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == []

    def test_reports_missing_skills_directory(self, validate, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(validate, "REPO", tmp_path)

        # Act
        validate.check_custom_skills()

        # Assert
        assert validate.errors == ["custom/skills/ is missing"]


def materialized(repo: Path, module_ids: list[str]) -> Path:
    """A materialized .ecc/ whose manifests pass permissive stand-in schemas."""
    ecc = repo / ".ecc"
    write_json(
        ecc / "manifests" / "install-modules.json", {"modules": [{"id": m} for m in module_ids]}
    )
    write_json(ecc / "manifests" / "install-profiles.json", {"profiles": {}})
    write_json(ecc / "manifests" / "install-components.json", {"components": []})
    for kind in ("modules", "profiles", "components"):
        write_json(ecc / "schemas" / f"install-{kind}.schema.json", {"type": "object"})
    return ecc


def fake_ls_tree(listing: dict[str, list[str]]):
    """Stand-in for `git ls-tree HEAD:<prefix>`; a prefix not listed is a missing tree."""

    def run(cmd, **kwargs):
        prefix = cmd[-1].removeprefix("HEAD:")
        if prefix not in listing:
            raise subprocess.CalledProcessError(128, cmd)
        return SimpleNamespace(stdout="\n".join(listing[prefix]) + "\n")

    return run


class TestCheckAgainstMaterialized:
    def test_only_notes_when_ecc_is_not_materialized(self, validate, repo):
        # Act
        validate.check_against_materialized(overlay())

        # Assert
        assert validate.errors == []
        assert any("not materialized" in n for n in validate.notes)

    def test_rejects_removed_module_still_present_and_added_module_absent(
        self, validate, repo, monkeypatch
    ):
        # Arrange
        materialized(repo, ["rules-core", "database"])
        monkeypatch.setattr(subprocess, "run", fake_ls_tree({}))

        # Act
        validate.check_against_materialized(overlay())

        # Assert
        assert any("'database' should have been removed" in e for e in validate.errors)
        assert any("'custom-skills' should have been added" in e for e in validate.errors)

    def test_rejects_manifest_that_fails_upstream_json_schema(self, validate, repo, monkeypatch):
        # Arrange
        pytest.importorskip("jsonschema")
        ecc = materialized(repo, ["rules-core", "custom-skills"])
        doc = {"modules": [{"id": "rules-core"}, {"id": "custom-skills", "owner": "x"}]}
        write_json(ecc / "manifests" / "install-modules.json", doc)
        write_json(
            ecc / "schemas" / "install-modules.schema.json",
            {
                "type": "object",
                "properties": {
                    "modules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id"],
                            "additionalProperties": False,
                            "properties": {"id": {"type": "string"}},
                        },
                    }
                },
            },
        )
        monkeypatch.setattr(subprocess, "run", fake_ls_tree({}))

        # Act
        validate.check_against_materialized(overlay())

        # Assert
        assert any(
            "install-modules.json: modules/1: Additional properties are not allowed" in e
            for e in validate.errors
        ), validate.errors

    def test_rejects_custom_skill_whose_name_upstream_already_uses(
        self, validate, repo, monkeypatch
    ):
        # Arrange
        add_skill(repo, "tdd-workflow")
        materialized(repo, ["rules-core", "custom-skills"])
        monkeypatch.setattr(subprocess, "run", fake_ls_tree({"skills": ["tdd-workflow", "other"]}))

        # Act
        validate.check_against_materialized(overlay())

        # Assert
        assert len(validate.errors) == 1
        assert (
            "custom/skills/tdd-workflow: collides with upstream skills/tdd-workflow"
            in validate.errors[0]
        )
        assert "rename ours to custom-tdd-workflow" in validate.errors[0]

    def test_custom_prefixed_skill_does_not_collide(self, validate, repo, monkeypatch):
        # Arrange
        materialized(repo, ["rules-core", "custom-skills"])
        monkeypatch.setattr(subprocess, "run", fake_ls_tree({"skills": ["one", "two"]}))

        # Act
        validate.check_against_materialized(overlay())

        # Assert
        assert validate.errors == []

    def test_rejects_collision_with_upstream_agents_skills(self, validate, repo, monkeypatch):
        # Arrange
        materialized(repo, ["rules-core", "custom-skills"])
        monkeypatch.setattr(subprocess, "run", fake_ls_tree({".agents/skills": ["custom-one"]}))

        # Act
        validate.check_against_materialized(overlay())

        # Assert
        assert validate.errors == [
            "custom/skills/custom-one: collides with upstream .agents/skills/custom-one"
        ]

    def test_into_directory_upstream_lacks_is_not_a_collision(self, validate, repo, monkeypatch):
        # Arrange
        materialized(repo, ["rules-core", "custom-skills"])
        entry = module(**{"$source": {"from": "custom/skills", "into": "rules/custom"}})
        monkeypatch.setattr(subprocess, "run", fake_ls_tree({}))

        # Act
        validate.check_against_materialized(overlay(entry))

        # Assert
        assert validate.errors == []


class TestMain:
    def test_returns_zero_for_a_consistent_checkout(self, validate, repo, capsys):
        # Arrange
        write_json(
            repo / "upstream.json",
            {"upstream": {"sha": VALID_SHA, "repo": "https://x/ecc.git", "pinnedOn": "2026-09-12"}},
        )
        write_json(repo / "overlay" / "manifest-overlay.json", overlay())
        write_json(repo / "custom" / "skills" / "skills-lock.json", {"version": 1, "skills": {}})

        # Act
        code = validate.main()

        # Assert
        assert code == 0
        assert (
            "OK — pin 0123456789, 1 modules added, 1 removed, 1 custom skills"
            in capsys.readouterr().out
        )

    def test_returns_one_and_lists_problems_when_invalid(self, validate, repo, capsys):
        # Arrange
        write_json(
            repo / "upstream.json",
            {"upstream": {"sha": "abc", "repo": "https://x/ecc.git", "pinnedOn": "2026-09-12"}},
        )
        write_json(repo / "overlay" / "manifest-overlay.json", overlay())
        write_json(repo / "custom" / "skills" / "skills-lock.json", {"version": 1, "skills": {}})

        # Act
        code = validate.main()

        # Assert
        assert code == 1
        assert "validation failed (1 problem(s))" in capsys.readouterr().err

    def test_returns_one_when_overlay_is_not_json(self, validate, repo, capsys):
        # Arrange
        write_json(repo / "upstream.json", {"upstream": {}})
        (repo / "overlay").mkdir()
        (repo / "overlay" / "manifest-overlay.json").write_text("{oops")

        # Act
        code = validate.main()

        # Assert
        assert code == 1
        assert "manifest-overlay.json: invalid JSON" in capsys.readouterr().err
