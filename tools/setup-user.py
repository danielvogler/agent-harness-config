#!/usr/bin/env python3
"""One command per person: make the shared config actually apply.

`make install` copies files. It does not turn anything on. Three things were left as
"read the docs and paste this", which means two people do them and everyone else does
not — and then the team is not working the same way, which is the whole point.

This does all four:

  1. Permission allow + deny lists in ~/.claude/settings.json. The allow list stops the
     prompts on read-only commands. The deny list is the only thing the client enforces
     no matter what the model or a tired human decides at 6pm.
  2. The two hooks worth having, out of ECC's 21. block-no-verify stops an agent
     bypassing pre-commit; config-protection stops it editing the linter config to make
     a failure go away.
  3. The team conventions into ~/.codex/AGENTS.md and ~/.opencode/AGENTS.md. Codex and
     opencode have no rules layer, and a skill is only read if the agent decides to read
     it. AGENTS.md is read every time, which is what Claude gets from rules.
  4. Claude Code's commit and PR attribution, turned off. Commits and PRs are authored
     by the person whose name is on them (custom/rules/git.md).

Everything is idempotent, backed up, and reversible. Not part of `make install` on
purpose: it writes to your own config, which `make uninstall` cannot reverse.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
CONVENTIONS = REPO / "custom" / "skills" / "team-conventions" / "SKILL.md"

# Written once setup-user has been applied, so install/update/reinstall can tell the
# difference between "never set up" and "set up, then clobbered by the installer".
STAMP = HOME / ".claude" / "ecc" / "setup-user.stamp"

# Claude Code otherwise adds a Co-Authored-By trailer to every commit and a "Generated
# with Claude Code" line to every PR description. Empty strings turn both off. A repo
# that wants them back sets `attribution` in its own .claude/settings.json, which takes
# precedence over this user-level file. The commit-msg hook and the PR check in CI catch
# what gets through from other tools.
ATTRIBUTION = {"commit": "", "pr": ""}

BEGIN = "<!-- BEGIN team-conventions (managed by agent-harness-config) -->"
END = "<!-- END team-conventions -->"

ALLOW = [
    "Bash(git status:*)",
    "Bash(git log:*)",
    "Bash(git diff:*)",
    "Bash(git show:*)",
    "Bash(git branch:*)",
    "Bash(git remote -v:*)",
    "Bash(git rev-parse:*)",
    "Bash(gcloud config list:*)",
    "Bash(gcloud projects list:*)",
    "Bash(gcloud projects describe:*)",
    "Bash(gcloud compute instances list:*)",
    "Bash(gcloud compute instances describe:*)",
    "Bash(gcloud storage ls:*)",
    "Bash(gcloud run services list:*)",
    "Bash(gcloud run services describe:*)",
    "Bash(gcloud logging read:*)",
    "Bash(gcloud iam service-accounts list:*)",
    "Bash(bq ls:*)",
    "Bash(bq show:*)",
    "Bash(bq query --dry_run:*)",
    "Bash(uv run pytest:*)",
    "Bash(uv run ruff check:*)",
    "Bash(uv tree:*)",
    "Bash(pre-commit run:*)",
    "Bash(make validate:*)",
    "Bash(make doctor:*)",
    "Bash(make context:*)",
    "Bash(make plan:*)",
    # Read-only shell basics. A markdown rule cannot grant a permission, so agents are
    # only spared the prompt for these because they are listed here.
    "Bash(ls:*)",
    "Bash(cat:*)",
    "Bash(head:*)",
    "Bash(tail:*)",
    "Bash(grep:*)",
    "Bash(rg:*)",
    "Bash(find:*)",
    "Bash(pwd:*)",
    "Bash(wc:*)",
    "Bash(git ls-files:*)",
    "Bash(git check-ignore:*)",
    # OpenTofu read-only, for infrastructure repos on OpenTofu rather than Terraform.
    "Bash(tofu plan:*)",
    "Bash(tofu validate:*)",
    "Bash(tofu fmt:*)",
    "Bash(tofu show:*)",
    # The Python template's task runner and checks.
    "Bash(just check:*)",
    "Bash(just lint:*)",
    "Bash(just test:*)",
    "Bash(just typecheck:*)",
    "Bash(uv run mypy:*)",
    "Bash(uv sync:*)",
    "Bash(uv lock:*)",
]

DENY = [
    "Bash(gcloud * delete:*)",
    "Bash(bq rm:*)",
    "Bash(gsutil rm -r:*)",
    "Bash(terraform destroy:*)",
    "Bash(tofu destroy:*)",
    "Bash(rm -rf:*)",
    # Nothing an agent does here needs root, and the blast radius of a wrong one is the
    # machine rather than a repo.
    "Bash(sudo:*)",
    "Read(**/*service-account*.json)",
    "Read(**/.env)",
    "Read(**/id_rsa)",
    "Read(**/id_ed25519)",
]

HOOKS = {
    "PreToolUse": [
        {
            "matcher": "Bash",
            "hooks": [
                {"type": "command", "command": "node ~/.claude/scripts/hooks/block-no-verify.js"}
            ],
        },
        {
            "matcher": "Write|Edit|MultiEdit",
            "hooks": [
                {"type": "command", "command": "node ~/.claude/scripts/hooks/config-protection.js"}
            ],
        },
    ]
}

changes: list[str] = []
skipped: list[str] = []


def backup(path: Path) -> None:
    if path.exists():
        dest = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, dest)
        changes.append(f"backed up {path} -> {dest.name}")


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        sys.exit(f"{path} is not valid JSON — fix it by hand first, nothing was changed")


def setup_permissions(dry: bool) -> None:
    path = HOME / ".claude" / "settings.json"
    settings = load(path)
    perms = settings.setdefault("permissions", {})

    for key, wanted in (("allow", ALLOW), ("deny", DENY)):
        current = perms.setdefault(key, [])
        added = [x for x in wanted if x not in current]
        if added:
            current.extend(added)
            changes.append(f"permissions.{key}: +{len(added)} entries")
        else:
            skipped.append(f"permissions.{key}: already current")

    if not dry and any(c.startswith("permissions.") for c in changes):
        backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2) + "\n")


def setup_attribution(dry: bool) -> None:
    path = HOME / ".claude" / "settings.json"
    settings = load(path)
    existing = settings.get("attribution")

    if existing == ATTRIBUTION:
        skipped.append("attribution: already off")
        return
    if existing is not None:
        skipped.append("attribution: left as you set it")
        return

    changes.append("attribution: turned off for commits and PRs")
    if not dry:
        backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        settings["attribution"] = ATTRIBUTION
        path.write_text(json.dumps(settings, indent=2) + "\n")


def setup_hooks(dry: bool) -> None:
    path = HOME / ".claude" / "settings.json"
    script = HOME / ".claude" / "scripts" / "hooks" / "block-no-verify.js"
    if not script.exists():
        skipped.append("hooks: skipped — run `make install` first (hook scripts absent)")
        return

    settings = load(path)
    existing = settings.get("hooks")

    # From ECC 2.2.x the installer writes its own resolved registry straight into
    # settings.json — upstream's fix for "hooks are installed but not wired" in
    # UPSTREAM.md. That turned 2 wired matchers into 27 on the 2026-09-12 bump,
    # including GateGuard (a justification prompt before every Bash call and every
    # first edit of a file) and matchers that send transcript text to an external
    # LLM or auto-deny edits. Nobody opted into that, so this is now authoritative:
    # our two guards, both of which only ever refuse an operation, and nothing else.
    #
    # To run the full upstream set instead, delete this and let the installer's
    # registry stand — but read the six capabilities install.sh lists first.
    if existing == HOOKS:
        skipped.append("hooks: already limited to the two guards")
        return

    if existing:
        extra = sum(len(v) for v in existing.values() if isinstance(v, list)) - len(HOOKS)
        changes.append(
            f"hooks: reset to block-no-verify and config-protection "
            f"({extra} upstream matcher(s) disabled)"
        )
    else:
        changes.append("hooks: enabled block-no-verify and config-protection")

    if not dry:
        backup(path)
        settings["hooks"] = HOOKS
        path.write_text(json.dumps(settings, indent=2) + "\n")


def conventions_roots() -> list[Path]:
    """Where Codex and opencode read AGENTS.md from.

    opencode moved from ~/.opencode to OPENCODE_CONFIG_DIR / XDG_CONFIG_HOME/opencode /
    ~/.config/opencode in ECC 2.2.x. Upstream's migration deliberately refuses to move a
    managed file it sees as modified — and ~/.opencode/AGENTS.md is *always* modified,
    because this script is what appends the conventions to it. So the migration cannot
    complete, and writing only to the old path leaves opencode with no conventions at all:
    it is the one harness where this append is the only route they arrive by.

    Write to the new path when it exists, and keep the legacy one only while it is still
    the live install.
    """
    roots = [HOME / ".codex"]

    env_dir = os.environ.get("OPENCODE_CONFIG_DIR")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if env_dir:
        current = Path(env_dir).expanduser()
    elif xdg:
        current = Path(xdg).expanduser() / "opencode"
    else:
        current = HOME / ".config" / "opencode"

    roots.append(current)
    legacy = HOME / ".opencode"
    if legacy.is_dir() and legacy != current:
        roots.append(legacy)
    return roots


def setup_conventions(dry: bool) -> None:
    """Put the conventions where Codex and opencode will always read them."""
    if not CONVENTIONS.exists():
        skipped.append("conventions: skipped — run `make conventions` first")
        return

    body = CONVENTIONS.read_text()
    # Drop the skill frontmatter; AGENTS.md is plain markdown.
    if body.startswith("---"):
        body = body.split("---", 2)[-1].lstrip()
    block = f"{BEGIN}\n\n{body.rstrip()}\n\n{END}\n"

    for root in conventions_roots():
        if not root.is_dir():
            skipped.append(f"conventions: {root.name} not installed, skipped")
            continue
        path = root / "AGENTS.md"
        existing = path.read_text() if path.exists() else ""

        if BEGIN in existing and END in existing:
            head, _, rest = existing.partition(BEGIN)
            _, _, tail = rest.partition(END)
            updated = head + block + tail.lstrip("\n")
            label = "updated"
        else:
            updated = (existing.rstrip() + "\n\n" if existing else "") + block
            label = "added"

        if updated == existing:
            skipped.append(f"conventions: {root.name}/AGENTS.md already current")
            continue

        changes.append(f"conventions: {label} in {root.name}/AGENTS.md")
        if not dry:
            backup(path)
            path.write_text(updated)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show changes, write nothing")
    parser.add_argument(
        "--restore",
        action="store_true",
        help=(
            "re-apply, but only if setup-user has been run on this machine before. "
            "install/update/reinstall end with this, because ECC's installer overwrites "
            "~/.codex/AGENTS.md and ~/.opencode/AGENTS.md — the files setup-user appends "
            "the team conventions to. Without it, every `make update` silently removes "
            "the only route those conventions reach Codex."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "exit 0 if this has already been applied, 1 otherwise. Writes nothing and "
            "prints nothing. `make reinstall` uses it to notice that it is about to throw "
            "your permissions and hooks away."
        ),
    )
    args = parser.parse_args()

    if args.restore and not STAMP.exists():
        return 0  # never set up here; nothing to put back, and not our call to start

    if args.check:
        # A dry run that would change nothing means everything is already in place.
        setup_permissions(True)
        setup_attribution(True)
        setup_hooks(True)
        setup_conventions(True)
        return 1 if changes else 0

    setup_permissions(args.dry_run)
    setup_attribution(args.dry_run)
    setup_hooks(args.dry_run)
    setup_conventions(args.dry_run)

    verb = "would change" if args.dry_run else "changed"
    print(f"{verb}:")
    for c in changes or ["  (nothing)"]:
        print(f"  {c}" if not c.startswith(" ") else c)
    if skipped:
        print("\nskipped:")
        for s in skipped:
            print(f"  {s}")

    if not args.dry_run:
        STAMP.parent.mkdir(parents=True, exist_ok=True)
        STAMP.write_text(
            "applied by tools/setup-user.py; remove to stop `make install` putting these back\n"
        )

    if not args.dry_run and changes:
        print("\nRestart your agent session for this to take effect.")
        print("To undo: restore the .bak files next to each config, or run `make doctor`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
