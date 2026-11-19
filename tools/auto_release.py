#!/usr/bin/env python3
"""Tag and release main from its commits, locally, after a pull (the auto-release hook).

Runs as a pre-commit `post-merge` hook, so it fires when `git pull` brings merged pull
requests into the local `main`. When `main` is level with `origin/main`, it reads the
conventional commits since the last `v*` tag:

- a breaking change (`feat!:` or a `BREAKING CHANGE` footer) raises the major version,
  or the minor one while the major is 0;
- a `feat` raises the minor version;
- a `fix` or `perf` raises the patch version;
- anything else (`docs`, `chore`, `ci`, `test`, `refactor`) makes no release.

It then creates an annotated tag whose message is the release notes, pushes the tag, and
creates the GitHub release with `gh` when it is available. Nothing is committed back and
no CI workflow is involved. A second machine pulling the same commits finds the tag on the
remote and does nothing.

    python3 tools/auto_release.py             # what the hook runs
    python3 tools/auto_release.py --dry-run   # print the next tag and its notes only

AUTO_RELEASE=0 in the environment turns it off for one pull.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<text>.+)$")
FIELD, RECORD = "\x1f", "\x1e"
HEADINGS = {"feat": "New", "fix": "Fixed", "perf": "Faster"}
RELEASE_BRANCH = "main"


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str = ""


def bump_of(commits: list[Commit]) -> str | None:
    """The largest change among the commits: major, minor, patch, or None for no release."""
    found: set[str] = set()
    for commit in commits:
        match = SUBJECT.match(commit.subject)
        if not match:
            continue
        if match["bang"] or "BREAKING CHANGE" in commit.body:
            found.add("major")
        elif match["type"] == "feat":
            found.add("minor")
        elif match["type"] in ("fix", "perf"):
            found.add("patch")
    return next((bump for bump in ("major", "minor", "patch") if bump in found), None)


def version_of(tag: str | None) -> tuple[int, int, int]:
    match = TAG.match(tag or "")
    return (int(match[1]), int(match[2]), int(match[3])) if match else (0, 0, 0)


def next_tag(last: str | None, bump: str) -> str:
    major, minor, patch = version_of(last)
    if bump == "major" and major == 0:
        bump = "minor"  # before 1.0 a breaking change is a minor step
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def notes(commits: list[Commit]) -> str:
    """Each feat, fix and perf subject under its heading, newest first."""
    sections: dict[str, list[str]] = {kind: [] for kind in HEADINGS}
    for commit in commits:
        match = SUBJECT.match(commit.subject)
        if match and match["type"] in sections:
            scope = f"**{match['scope']}**: " if match["scope"] else ""
            sections[match["type"]].append(f"- {scope}{match['text']} ({commit.sha[:7]})")
    return "\n\n".join(
        f"## {HEADINGS[kind]}\n\n" + "\n".join(lines) for kind, lines in sections.items() if lines
    )


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True, text=True).returncode == 0


def last_tag() -> str | None:
    tags = [t for t in git("tag", "--merged", "HEAD", "--list", "v*").split() if TAG.match(t)]
    return max(tags, key=version_of, default=None)


def commits_since(tag: str | None) -> list[Commit]:
    span = f"{tag}..HEAD" if tag else "HEAD"
    out = git("log", "--no-merges", f"--format=%H{FIELD}%s{FIELD}%b{RECORD}", span)
    return [
        Commit(*entry.strip("\n").split(FIELD, 2)) for entry in out.split(RECORD) if entry.strip()
    ]


def why_not_release() -> str | None:
    """A reason to skip, or None when this checkout may release."""
    if os.environ.get("AUTO_RELEASE") == "0":
        return "AUTO_RELEASE=0"
    if not git_ok("rev-parse", "--verify", "-q", "HEAD"):
        return "no commits yet"
    branch = git("branch", "--show-current")
    if branch != RELEASE_BRANCH:
        return f"on {branch or 'a detached HEAD'}, not {RELEASE_BRANCH}"
    upstream = f"origin/{RELEASE_BRANCH}"
    if not git_ok("rev-parse", "--verify", "-q", upstream):
        return f"no {upstream}"
    if git("rev-parse", "HEAD") != git("rev-parse", upstream):
        return (
            f"{RELEASE_BRANCH} is not level with {upstream}; only what is on the remote is released"
        )
    return None


def on_remote(tag: str) -> bool:
    return bool(git("ls-remote", "--tags", "origin", f"refs/tags/{tag}"))


def release(tag: str, body: str) -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(body + "\n")
        notes_file = handle.name
    try:
        subprocess.run(["git", "tag", "-a", tag, "-F", notes_file], check=True)
        pushed = subprocess.run(["git", "push", "-q", "origin", f"refs/tags/{tag}"])
        if pushed.returncode != 0:
            # A tag nobody else can see is not a release; take it back so the next pull retries.
            subprocess.run(["git", "tag", "-d", tag], capture_output=True)
            print(f"auto-release: could not push {tag}; the next pull tries again", file=sys.stderr)
            return 1
        print(f"auto-release: tagged and pushed {tag}")
        if shutil.which("gh") is None:
            print(
                "auto-release: gh not found, so no GitHub release; the tag stands", file=sys.stderr
            )
            return 0
        made = subprocess.run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--title",
                tag,
                "--notes-file",
                notes_file,
                "--verify-tag",
            ],
            capture_output=True,
            text=True,
        )
        if made.returncode != 0:
            print(f"auto-release: no GitHub release: {made.stderr.strip()}", file=sys.stderr)
            return 1
        print(f"auto-release: GitHub release {tag} created")
        return 0
    finally:
        os.unlink(notes_file)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the next tag and notes only")
    args = parser.parse_args(argv)

    reason = why_not_release()
    if reason and not args.dry_run:
        return 0  # nothing to say on an ordinary pull of a feature branch
    tag = last_tag()
    commits = commits_since(tag)
    bump = bump_of(commits)
    if bump is None:
        if args.dry_run:
            print(f"no release: nothing user-facing since {tag or 'the first commit'}")
        return 0
    new = next_tag(tag, bump)
    body = notes(commits) if tag else "The first release."
    if args.dry_run:
        print(new + (f"  (would skip: {reason})" if reason else ""))
        print(body)
        return 0
    if on_remote(new):
        subprocess.run(["git", "fetch", "-q", "origin", f"refs/tags/{new}:refs/tags/{new}"])
        return 0  # another checkout released these commits first
    return release(new, body)


if __name__ == "__main__":
    sys.exit(main())
