"""tools/doctor.py: drift between this checkout and what is installed in ~."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import load_tool, write_json

PIN = "a" * 40
OTHER = "b" * 40


def state(
    target: str = "claude",
    commit: str | None = PIN,
    profile: str = "custom",
    installed_at: str | None = "2026-09-01T12:00:00Z",
    root: Path | None = None,
) -> dict:
    doc: dict = {
        "target": {"id": f"{target}-home", "target": target},
        "source": {"repoCommit": commit} if commit else {},
        "request": {"profile": profile},
    }
    if installed_at:
        doc["installedAt"] = installed_at
    if root:
        doc["target"]["root"] = str(root)
    return doc


def statuses(doctor) -> list[str]:
    return [s for s, _, _ in doctor.findings]


def headlines(doctor) -> str:
    return "\n".join(h for _, h, _ in doctor.findings)


@pytest.fixture(autouse=True)
def no_install_plan(doctor, monkeypatch):
    """planned_paths shells out to the real installer; tests opt in to a plan explicitly."""
    monkeypatch.setattr(doctor, "planned_paths", lambda target: None, raising=False)


class TestCheckPin:
    def test_reports_ok_when_installed_commit_matches_pin(self, doctor):
        # Act
        doctor.check_pin([(Path("s.json"), state())], PIN)

        # Assert
        assert statuses(doctor) == [doctor.OK]

    def test_reports_error_and_make_update_when_installed_commit_differs(self, doctor):
        # Act
        doctor.check_pin([(Path("s.json"), state(commit=OTHER))], PIN)

        # Assert
        [(status, headline, advice)] = doctor.findings
        assert status == doctor.ERR
        assert headline == "claude-home: installed upstream bbbbbbbb, pin says aaaaaaaa"
        assert "make update" in advice

    def test_warns_when_install_state_records_no_commit(self, doctor):
        # Act
        doctor.check_pin([(Path("s.json"), state(commit=None))], PIN)

        # Assert
        assert statuses(doctor) == [doctor.WARN]

    def test_warns_when_installed_with_another_profile(self, doctor):
        # Act
        doctor.check_pin([(Path("s.json"), state(profile="full"))], PIN)

        # Assert
        assert statuses(doctor) == [doctor.OK, doctor.WARN]
        assert "profile 'full'" in headlines(doctor)


@pytest.fixture
def repo(doctor, tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    (root / "custom" / "skills" / "one").mkdir(parents=True)
    (root / "overlay").mkdir()
    monkeypatch.setattr(doctor, "REPO", root)
    monkeypatch.setattr(doctor, "ECC", root / ".ecc")
    return root


def touch(path: Path, when: datetime) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n")
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp))
    return path


INSTALLED = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
BEFORE = datetime(2026, 8, 30, tzinfo=UTC)
AFTER = datetime(2026, 9, 2, tzinfo=UTC)


class TestContentDrift:
    def test_newest_mtime_picks_latest_watched_file_and_skips_ds_store(self, doctor, repo):
        # Arrange
        touch(repo / "overlay" / "manifest-overlay.json", BEFORE)
        newest = touch(repo / "custom" / "skills" / "one" / "SKILL.md", AFTER)
        touch(repo / "custom" / ".DS_Store", datetime(2026, 9, 9, tzinfo=UTC))
        touch(repo / "README.md", datetime(2026, 9, 9, tzinfo=UTC))

        # Act
        mtime, where = doctor.newest_mtime(doctor.WATCHED)

        # Assert
        assert where == newest
        assert mtime == AFTER.timestamp()

    def test_reports_error_when_custom_changed_after_install(self, doctor, repo):
        # Arrange
        touch(repo / "custom" / "skills" / "one" / "SKILL.md", AFTER)

        # Act
        doctor.check_content([(Path("s.json"), state())])

        # Assert
        [(status, headline, advice)] = doctor.findings
        assert status == doctor.ERR
        assert headline == "claude-home: custom/skills/one/SKILL.md changed after the last install"
        assert "make update" in advice

    def test_reports_ok_when_install_is_newer_than_every_change(self, doctor, repo):
        # Arrange
        touch(repo / "upstream.json", BEFORE)

        # Act
        doctor.check_content([(Path("s.json"), state())])

        # Assert
        assert statuses(doctor) == [doctor.OK]

    @pytest.mark.parametrize("installed_at", [None, "not a date"])
    def test_skips_state_without_a_usable_install_time(self, doctor, repo, installed_at):
        # Arrange
        touch(repo / "upstream.json", AFTER)

        # Act
        doctor.check_content([(Path("s.json"), state(installed_at=installed_at))])

        # Assert
        assert doctor.findings == []


def fake_git(answers: dict[tuple[str, ...], str | None]):
    return lambda *args: answers.get(args)


CLEAN_REPO = {
    ("rev-parse", "--git-dir"): ".git",
    ("status", "--porcelain"): "",
    ("describe", "--tags", "--always"): "v1.0.0",
    ("describe", "--tags", "--abbrev=0"): "v1.0.0",
    ("rev-list", "--left-right", "--count", "HEAD...origin/main"): "0\t0",
    ("log", "-1", "--format=%cr", "origin/main"): "2 days ago",
}


class TestRepoStaleness:
    def test_reports_error_when_behind_origin_main(self, doctor, monkeypatch):
        # Arrange
        answers = {
            **CLEAN_REPO,
            ("rev-list", "--left-right", "--count", "HEAD...origin/main"): "0\t3",
        }
        monkeypatch.setattr(doctor, "git", fake_git(answers))

        # Act
        doctor.check_repo()

        # Assert
        errors = [(h, a) for s, h, a in doctor.findings if s == doctor.ERR]
        assert errors == [("3 commit(s) behind origin/main", "run `make update`")]

    def test_reports_ok_when_only_ahead_of_origin_main(self, doctor, monkeypatch):
        # Arrange
        answers = {
            **CLEAN_REPO,
            ("rev-list", "--left-right", "--count", "HEAD...origin/main"): "2\t0",
        }
        monkeypatch.setattr(doctor, "git", fake_git(answers))

        # Act
        doctor.check_repo()

        # Assert
        assert doctor.ERR not in statuses(doctor)
        assert "2 local commit(s) ahead" in headlines(doctor)

    def test_warns_about_uncommitted_changes_and_missing_tags(self, doctor, monkeypatch):
        # Arrange
        answers = {
            **CLEAN_REPO,
            ("status", "--porcelain"): " M README.md",
            ("describe", "--tags", "--abbrev=0"): None,
        }
        monkeypatch.setattr(doctor, "git", fake_git(answers))

        # Act
        doctor.check_repo()

        # Assert
        assert "working tree has uncommitted changes" in headlines(doctor)
        assert "no release tags in this checkout" in headlines(doctor)

    def test_warns_without_origin_main_instead_of_guessing(self, doctor, monkeypatch):
        # Arrange
        answers = {
            **CLEAN_REPO,
            ("rev-list", "--left-right", "--count", "HEAD...origin/main"): None,
        }
        monkeypatch.setattr(doctor, "git", fake_git(answers))

        # Act
        doctor.check_repo()

        # Assert
        assert statuses(doctor)[-1] == doctor.WARN
        assert "no origin/main ref" in headlines(doctor)

    def test_warns_when_not_a_git_checkout(self, doctor, monkeypatch):
        # Arrange
        monkeypatch.setattr(doctor, "git", fake_git({}))

        # Act
        doctor.check_repo()

        # Assert
        assert doctor.findings == [(doctor.WARN, "not a git checkout — cannot check staleness", "")]

    @pytest.mark.parametrize(
        "outcome",
        [
            OSError("git missing"),
            SimpleNamespace(returncode=128, stdout="fatal\n"),
        ],
    )
    def test_git_returns_none_instead_of_raising(self, doctor, monkeypatch, outcome):
        # Arrange
        def run(*args, **kwargs):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(subprocess, "run", run)

        # Act
        result = doctor.git("rev-parse", "HEAD")

        # Assert
        assert result is None


class TestUpstreamDoctorAndStatePaths:
    def test_upstream_doctor_is_none_before_ecc_is_materialized(self, doctor, repo):
        # Act / Assert
        assert doctor.upstream_doctor() is None

    @pytest.mark.parametrize(
        "stdout, expected",
        [
            ('{"results": []}', {"results": []}),
            ("not json", None),
        ],
    )
    def test_upstream_doctor_parses_json_or_gives_up(
        self, doctor, repo, monkeypatch, stdout, expected
    ):
        # Arrange
        script = repo / ".ecc" / "scripts" / "doctor.js"
        script.parent.mkdir(parents=True)
        script.write_text("")
        done = SimpleNamespace(returncode=0, stdout=stdout)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: done)

        # Act
        report = doctor.upstream_doctor()

        # Assert
        assert report == expected

    def test_state_paths_come_from_upstream_report_when_available(self, doctor):
        # Arrange
        report = {"results": [{"installStatePath": "/x/claude.json"}]}

        # Act
        paths = doctor.state_paths(report)

        # Assert
        assert paths == [Path("/x/claude.json")]

    def test_state_paths_fall_back_to_known_locations_that_exist(
        self, doctor, tmp_path, monkeypatch
    ):
        # Arrange
        present = tmp_path / "present.json"
        present.write_text("{}")
        monkeypatch.setattr(doctor, "KNOWN_STATE_PATHS", (present, tmp_path / "absent.json"))

        # Act
        paths = doctor.state_paths(None)

        # Assert
        assert paths == [present]


class TestCheckHooks:
    @pytest.fixture
    def claude_root(self, tmp_path: Path) -> Path:
        root = tmp_path / ".claude"
        write_json(root / "hooks" / "hooks.json", {"hooks": {"PreToolUse": [{}, {}], "Stop": [{}]}})
        return root

    def test_reports_installed_but_unwired_hooks_as_inert(self, doctor, claude_root):
        # Act
        doctor.check_hooks([(Path("s.json"), state(root=claude_root))])

        # Assert
        [(status, headline, _)] = doctor.findings
        assert status == doctor.ERR
        assert headline == "claude-home: 3 hook matcher(s) installed but INERT"

    def test_reports_ok_when_settings_declare_hooks(self, doctor, claude_root):
        # Arrange
        write_json(claude_root / "settings.json", {"hooks": {"PreToolUse": [{}]}})

        # Act
        doctor.check_hooks([(Path("s.json"), state(root=claude_root))])

        # Assert
        assert statuses(doctor) == [doctor.OK]

    def test_reports_ok_from_settings_when_no_registry_file_is_installed(self, doctor, tmp_path):
        # Arrange
        root = tmp_path / ".claude"
        write_json(root / "settings.json", {"hooks": {"PreToolUse": [{}, {}]}})

        # Act
        doctor.check_hooks([(Path("s.json"), state(root=root))])

        # Assert
        assert doctor.findings == [(doctor.OK, "claude-home: hooks wired into settings", "")]

    def test_warns_when_neither_registry_nor_settings_declare_hooks(self, doctor, tmp_path):
        # Arrange
        root = tmp_path / ".claude"
        write_json(root / "settings.json", {"permissions": {}})

        # Act
        doctor.check_hooks([(Path("s.json"), state(root=root))])

        # Assert
        [(status, headline, advice)] = doctor.findings
        assert status == doctor.WARN
        assert headline == "claude-home: no hooks declared in settings"
        assert "make setup-user" in advice

    def test_ignores_targets_other_than_claude(self, doctor, claude_root):
        # Act
        doctor.check_hooks([(Path("s.json"), state(target="codex", root=claude_root))])

        # Assert
        assert doctor.findings == []


class TestCheckFiles:
    def test_warns_when_upstream_doctor_is_unavailable(self, doctor):
        # Act
        doctor.check_files(None)

        # Assert
        assert statuses(doctor) == [doctor.WARN]

    def test_maps_issue_severity_to_status(self, doctor):
        # Arrange
        report = {
            "results": [
                {
                    "adapter": {"id": "claude-home"},
                    "issues": [
                        {"severity": "error", "message": "rules/x.md modified"},
                        {"severity": "warning", "message": "rules/y.md extra"},
                    ],
                },
                {"adapter": {"id": "codex-home"}, "issues": []},
            ]
        }

        # Act
        doctor.check_files(report)

        # Assert
        assert doctor.findings == [
            (doctor.ERR, "claude-home: rules/x.md modified", ""),
            (doctor.WARN, "claude-home: rules/y.md extra", ""),
            (doctor.OK, "codex-home: managed files intact", ""),
        ]


class TestSetupUserDrift:
    @pytest.fixture
    def report(self, tmp_path: Path) -> dict:
        home = tmp_path / "home"
        return {
            "results": [
                {
                    "adapter": {"id": "claude-home"},
                    "issues": [
                        {
                            "severity": "error",
                            "code": "missing-managed-files",
                            "message": "1 managed file(s) are missing",
                            "paths": [str(home / ".claude" / "settings.json")],
                        },
                        {
                            "severity": "warning",
                            "code": "drifted-managed-files",
                            "message": "1 managed file(s) differ from the source repo",
                            "paths": [str(home / ".claude" / "hooks" / "hooks.json")],
                        },
                    ],
                },
                {
                    "adapter": {"id": "codex-home"},
                    "issues": [
                        {
                            "severity": "warning",
                            "code": "drifted-managed-files",
                            "message": "1 managed file(s) differ from the source repo",
                            "paths": [str(home / ".codex" / "AGENTS.md")],
                        }
                    ],
                },
            ]
        }

    def test_reports_setup_user_edits_as_expected_when_it_has_been_applied(
        self, doctor, report, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(doctor, "setup_user_applied", lambda: True)

        # Act
        doctor.check_files(report)

        # Assert
        assert doctor.findings == [
            (doctor.OK, "claude-home: settings.json changed by setup-user.py, as intended", ""),
            (doctor.WARN, "claude-home: 1 managed file(s) differ from the source repo", ""),
            (doctor.OK, "codex-home: AGENTS.md changed by setup-user.py, as intended", ""),
        ]

    def test_keeps_upstream_findings_when_setup_user_has_not_been_applied(
        self, doctor, report, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(doctor, "setup_user_applied", lambda: False)

        # Act
        doctor.check_files(report)

        # Assert
        assert statuses(doctor) == [doctor.ERR, doctor.WARN, doctor.WARN]

    def test_reports_only_the_other_paths_when_an_issue_mixes_both(
        self, doctor, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(doctor, "setup_user_applied", lambda: True)
        home = tmp_path / "home"
        report = {
            "results": [
                {
                    "adapter": {"id": "codex-home"},
                    "issues": [
                        {
                            "severity": "warning",
                            "code": "drifted-managed-files",
                            "message": "2 managed file(s) differ from the source repo",
                            "paths": [
                                str(home / ".codex" / "AGENTS.md"),
                                str(home / ".codex" / "rules" / "x.md"),
                            ],
                        }
                    ],
                }
            ]
        }

        # Act
        doctor.check_files(report)

        # Assert
        assert doctor.findings == [
            (doctor.OK, "codex-home: AGENTS.md changed by setup-user.py, as intended", ""),
            (doctor.WARN, "codex-home: 1 managed file(s) differ from the source repo: x.md", ""),
        ]


class TestStaleRecords:
    @pytest.fixture
    def report(self, tmp_path: Path) -> dict:
        home = tmp_path / "home"
        return {
            "results": [
                {
                    "adapter": {"id": "claude-home", "target": "claude"},
                    "issues": [
                        {
                            "severity": "error",
                            "code": "missing-managed-files",
                            "message": "1 managed file(s) are missing",
                            "paths": [str(home / ".claude" / "hooks" / "hooks.json")],
                        },
                        {
                            "severity": "error",
                            "code": "missing-source-files",
                            "message": "1 source file(s) referenced by install-state are missing",
                            "paths": [
                                str(tmp_path / ".ecc" / "scripts" / "lib" / "cost-estimate.js")
                            ],
                        },
                    ],
                }
            ]
        }

    def test_reports_records_the_current_plan_no_longer_contains_as_stale(
        self, doctor, report, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(doctor, "planned_paths", lambda target: {"/somewhere/else.md"})

        # Act
        doctor.check_files(report)

        # Assert
        assert doctor.findings == [
            (doctor.OK, "claude-home: stale install-state record ignored: hooks.json", ""),
            (doctor.OK, "claude-home: stale install-state record ignored: cost-estimate.js", ""),
        ]

    def test_keeps_findings_for_paths_the_current_plan_still_installs(
        self, doctor, report, tmp_path, monkeypatch
    ):
        # Arrange
        hooks = str(tmp_path / "home" / ".claude" / "hooks" / "hooks.json")
        monkeypatch.setattr(doctor, "planned_paths", lambda target: {hooks})

        # Act
        doctor.check_files(report)

        # Assert
        assert statuses(doctor) == [doctor.ERR, doctor.OK]

    def test_keeps_upstream_findings_when_the_plan_is_unavailable(self, doctor, report):
        # Act
        doctor.check_files(report)

        # Assert
        assert statuses(doctor) == [doctor.ERR, doctor.ERR]

    def test_asks_the_installer_once_per_target(self, doctor, report, monkeypatch):
        # Arrange
        calls = []

        def plan(target):
            calls.append(target)
            return set()

        monkeypatch.setattr(doctor, "planned_paths", plan)

        # Act
        doctor.check_files(report)

        # Assert
        assert calls == ["claude"]

    @pytest.fixture
    def real_doctor(self, tmp_path: Path, monkeypatch):
        """A fresh copy of doctor.py, without the autouse planned_paths stub."""
        module = load_tool("doctor.py")
        ecc = tmp_path / ".ecc"
        ecc.mkdir()
        (ecc / "install.sh").write_text("")
        monkeypatch.setattr(module, "ECC", ecc)
        return module

    def test_planned_paths_collects_sources_and_destinations(self, real_doctor, monkeypatch):
        # Arrange
        out = {
            "plan": {
                "plannedOperations": [
                    {"sourcePath": "/src/a.md", "destinationPath": "/dst/a.md"},
                    {"destinationPath": "/dst/settings.json"},
                ]
            }
        }
        monkeypatch.setattr(
            real_doctor.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(out)),
        )

        # Act
        paths = real_doctor.planned_paths("claude")

        # Assert
        assert paths == {"/src/a.md", "/dst/a.md", "/dst/settings.json"}

    def test_planned_paths_is_none_when_the_installer_output_is_unusable(
        self, real_doctor, monkeypatch
    ):
        # Arrange
        monkeypatch.setattr(
            real_doctor.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="")
        )

        # Act
        paths = real_doctor.planned_paths("claude")

        # Assert
        assert paths is None


class TestLegacyOpencodeState:
    def test_drops_legacy_state_and_warns_when_a_current_one_exists(
        self, doctor, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setenv("HOME", str(tmp_path))
        legacy = tmp_path / ".opencode" / "ecc-install-state.json"
        current = tmp_path / ".config" / "opencode" / "ecc-install-state.json"
        states = [
            (current, state(target="opencode")),
            (legacy, state(target="opencode", commit=OTHER)),
        ]

        # Act
        kept = doctor.drop_legacy_opencode(states)

        # Assert
        assert kept == [states[0]]
        [(status, headline, advice)] = doctor.findings
        assert status == doctor.WARN
        assert "~/.opencode" in headline
        assert "move ~/.opencode/ecc-install-state.json aside" in advice

    def test_keeps_legacy_state_when_it_is_the_only_opencode_install(
        self, doctor, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setenv("HOME", str(tmp_path))
        legacy = tmp_path / ".opencode" / "ecc-install-state.json"
        states = [(legacy, state(target="opencode"))]

        # Act
        kept = doctor.drop_legacy_opencode(states)

        # Assert
        assert kept == states
        assert doctor.findings == []

    def test_known_state_paths_include_the_current_opencode_location(self, doctor):
        # Assert
        assert Path.home() / ".config" / "opencode" / "ecc-install-state.json" in (
            doctor.KNOWN_STATE_PATHS
        )


class TestMcp:
    def test_health_parses_connected_and_failed_servers(self, doctor, monkeypatch):
        # Arrange
        listing = (
            "Checking MCP server health...\n\n"
            "context7: npx -y @upstash/context7-mcp - ✓ Connected\n"
            "bigquery: uvx bq-mcp - ✗ Failed to connect\n"
            "  continuation: line\n"
        )
        monkeypatch.setattr(doctor.shutil, "which", lambda name: "/bin/claude")
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=listing)
        )

        # Act
        health = doctor.mcp_health()

        # Assert
        assert health == {"context7": True, "bigquery": False}

    def test_health_is_unknown_without_the_claude_cli(self, doctor, monkeypatch):
        # Arrange
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

        # Act / Assert
        assert doctor.mcp_health() is None

    @pytest.fixture
    def home(self, tmp_path: Path, monkeypatch) -> Path:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        return home

    def test_warns_when_agreed_servers_are_not_active(self, doctor, repo, home):
        # Arrange
        write_json(
            repo / "overlay" / "manifest-overlay.json",
            {"activateMcpServers": {"ids": ["context7", "bigquery"]}},
        )
        write_json(home / ".claude.json", {"mcpServers": {"context7": {}}})

        # Act
        doctor.check_mcp()

        # Assert
        [(status, headline, _)] = doctor.findings
        assert status == doctor.WARN
        assert headline == "mcp: 1 of 2 agreed server(s) not active (bigquery)"

    def test_reports_error_when_active_server_does_not_connect(
        self, doctor, repo, home, monkeypatch
    ):
        # Arrange
        write_json(
            repo / "overlay" / "manifest-overlay.json",
            {"activateMcpServers": {"ids": ["context7", "bigquery"]}},
        )
        write_json(home / ".claude.json", {"mcpServers": {"context7": {}, "bigquery": {}}})
        monkeypatch.setattr(doctor, "mcp_health", lambda: {"context7": True, "bigquery": False})

        # Act
        doctor.check_mcp()

        # Assert
        [(status, headline, _)] = doctor.findings
        assert status == doctor.ERR
        assert "(bigquery)" in headline


class TestMain:
    @pytest.fixture
    def installed(self, doctor, repo, tmp_path, monkeypatch) -> Path:
        write_json(repo / "upstream.json", {"upstream": {"sha": PIN}})
        state_file = write_json(tmp_path / "state.json", state(commit=OTHER))
        monkeypatch.setattr(doctor, "upstream_doctor", lambda: None)
        monkeypatch.setattr(doctor, "KNOWN_STATE_PATHS", (state_file,))
        monkeypatch.setattr(doctor, "git", fake_git(CLEAN_REPO))
        monkeypatch.setattr(doctor, "check_mcp", lambda: None)
        # check_hooks falls back to ~/.claude; keep it off the real home directory.
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        return state_file

    def test_strict_mode_exits_one_on_pin_drift(self, doctor, installed, monkeypatch, capsys):
        # Arrange
        monkeypatch.setattr(sys, "argv", ["doctor.py", "--strict"])

        # Act
        code = doctor.main()

        # Assert
        assert code == 1
        assert "installed upstream bbbbbbbb, pin says aaaaaaaa" in capsys.readouterr().out

    def test_default_mode_reports_but_exits_zero(self, doctor, installed, monkeypatch):
        # Arrange
        monkeypatch.setattr(sys, "argv", ["doctor.py"])

        # Act
        code = doctor.main()

        # Assert
        assert code == 0

    def test_suggests_make_update_only_when_an_error_advises_it(
        self, doctor, installed, monkeypatch, capsys
    ):
        # Arrange
        monkeypatch.setattr(sys, "argv", ["doctor.py"])

        # Act
        doctor.main()

        # Assert
        assert "fixed by `make update`" in capsys.readouterr().out

    def test_does_not_suggest_make_update_for_errors_it_cannot_fix(
        self, doctor, repo, tmp_path, monkeypatch, capsys
    ):
        # Arrange
        write_json(repo / "upstream.json", {"upstream": {"sha": PIN}})
        state_file = write_json(tmp_path / "state.json", state())
        monkeypatch.setattr(doctor, "upstream_doctor", lambda: None)
        monkeypatch.setattr(doctor, "KNOWN_STATE_PATHS", (state_file,))
        monkeypatch.setattr(doctor, "git", fake_git(CLEAN_REPO))
        monkeypatch.setattr(doctor, "check_content", lambda states: None)
        monkeypatch.setattr(
            doctor, "check_mcp", lambda: doctor.note(doctor.ERR, "mcp: bigquery down")
        )
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setattr(sys, "argv", ["doctor.py"])

        # Act
        doctor.main()

        # Assert
        out = capsys.readouterr().out
        assert "mcp: bigquery down" in out
        assert "make update" not in out.split("checks,")[-1]

    def test_says_nothing_is_installed_when_no_state_exists(
        self, doctor, repo, tmp_path, monkeypatch, capsys
    ):
        # Arrange
        write_json(repo / "upstream.json", {"upstream": {"sha": PIN}})
        monkeypatch.setattr(doctor, "upstream_doctor", lambda: None)
        monkeypatch.setattr(doctor, "KNOWN_STATE_PATHS", (tmp_path / "absent.json",))
        monkeypatch.setattr(sys, "argv", ["doctor.py", "--strict"])

        # Act
        code = doctor.main()

        # Assert
        assert code == 1
        assert "Nothing is installed" in capsys.readouterr().out
