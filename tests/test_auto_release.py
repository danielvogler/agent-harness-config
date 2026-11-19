"""tools/auto_release.py: the next version from conventional commits, tagged after a pull."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "auto_release.py"


@pytest.fixture
def ar(monkeypatch):
    # Registered before it runs: its dataclass looks its own module up in sys.modules.
    spec = importlib.util.spec_from_file_location("tool_auto_release", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "tool_auto_release", module)
    spec.loader.exec_module(module)
    return module


def run(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def clone(tmp_path, monkeypatch):
    """A clone of a bare origin, on main, level with origin/main, with no gh on PATH."""
    origin = tmp_path / "origin.git"
    run(tmp_path, "git", "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    run(tmp_path, "git", "clone", "-q", str(origin), str(work))
    for key, value in (
        ("user.name", "Test"),
        ("user.email", "t@example.org"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    ):
        run(work, "git", "config", key, value)
    run(work, "git", "checkout", "-q", "-b", "main")
    monkeypatch.chdir(work)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # no gh: the tag is the release
    monkeypatch.delenv("AUTO_RELEASE", raising=False)
    return work, origin


def commit(work: Path, subject: str, body: str = "") -> None:
    run(
        work, "git", "commit", "-q", "--allow-empty", "-m", subject, *(["-m", body] if body else [])
    )


def publish(work: Path) -> None:
    run(work, "git", "push", "-q", "-u", "origin", "main")


def remote_tags(origin: Path) -> list[str]:
    return run(origin, "git", "tag", "--list").split()


class TestBump:
    def test_feat_is_minor_fix_is_patch_and_others_nothing(self, ar):
        C = ar.Commit
        assert ar.bump_of([C("a", "fix(x): y"), C("b", "feat: z")]) == "minor"
        assert ar.bump_of([C("a", "perf: y")]) == "patch"
        assert ar.bump_of([C("a", "docs: y"), C("b", "chore(ci): z")]) is None

    def test_breaking_change_is_major_but_minor_before_one(self, ar):
        C = ar.Commit
        assert ar.bump_of([C("a", "feat!: y")]) == "major"
        assert ar.bump_of([C("a", "fix: y", "BREAKING CHANGE: gone")]) == "major"
        assert ar.next_tag("v0.4.2", "major") == "v0.5.0"
        assert ar.next_tag("v1.4.2", "major") == "v2.0.0"
        assert ar.next_tag(None, "patch") == "v0.0.1"

    def test_notes_group_subjects_by_kind(self, ar):
        C = ar.Commit
        text = ar.notes(
            [
                C("zzzzzzzz1", "feat(skills): add x"),
                C("yyyyyyyy2", "fix: y"),
                C("0", "docs: words only"),
            ]
        )
        assert "## New\n\n- **skills**: add x (zzzzzzz)" in text
        assert "## Fixed\n\n- y (yyyyyyy)" in text
        assert "words only" not in text


class TestRelease:
    def test_a_feat_on_main_level_with_origin_is_tagged_and_pushed(self, ar, clone):
        work, origin = clone
        commit(work, "feat: first thing")
        run(work, "git", "tag", "-a", "v0.2.0", "-m", "v0.2.0")
        run(work, "git", "push", "-q", "origin", "v0.2.0")
        commit(work, "feat(hooks): publish them")
        commit(work, "docs: explain")
        publish(work)

        assert ar.main([]) == 0

        assert "v0.3.0" in remote_tags(origin)
        message = run(work, "git", "tag", "-l", "--format=%(contents)", "v0.3.0")
        assert "**hooks**: publish them" in message
        assert "explain" not in message

    def test_nothing_user_facing_makes_no_tag(self, ar, clone):
        work, origin = clone
        commit(work, "docs: only words")
        publish(work)

        assert ar.main([]) == 0
        assert remote_tags(origin) == []

    def test_a_second_run_does_not_tag_again(self, ar, clone):
        work, origin = clone
        commit(work, "fix: a bug")
        publish(work)

        ar.main([])
        ar.main([])

        assert remote_tags(origin) == ["v0.0.1"]

    def test_main_ahead_of_origin_is_not_released(self, ar, clone):
        work, origin = clone
        commit(work, "feat: pushed")
        publish(work)
        commit(work, "feat: only local")

        assert ar.main([]) == 0
        assert remote_tags(origin) == []

    def test_another_branch_is_not_released(self, ar, clone):
        work, origin = clone
        commit(work, "feat: on main")
        publish(work)
        run(work, "git", "checkout", "-q", "-b", "feat/x")

        assert ar.main([]) == 0
        assert remote_tags(origin) == []

    def test_turned_off_for_one_pull(self, ar, clone, monkeypatch):
        work, origin = clone
        commit(work, "feat: on main")
        publish(work)
        monkeypatch.setenv("AUTO_RELEASE", "0")

        assert ar.main([]) == 0
        assert remote_tags(origin) == []

    def test_dry_run_prints_the_tag_and_changes_nothing(self, ar, clone, capsys):
        work, origin = clone
        commit(work, "feat: something")
        publish(work)

        assert ar.main(["--dry-run"]) == 0

        assert capsys.readouterr().out.startswith("v0.1.0")
        assert remote_tags(origin) == []
        assert run(work, "git", "tag", "--list") == ""
