#!/usr/bin/env python3
"""Report what the installed config costs in context, every session.

Bloat is this repo's stated failure mode, and it is invisible: adding a rule or a
skill is a one-line PR, and the cost is paid silently by everyone on every session
forever. This makes the number visible so pruning can be an argument about evidence
instead of taste.

The distinction that matters is **always-on versus on-demand**:

  - A rule under ~/.claude/rules/ with no `paths:` frontmatter is loaded into every
    session, in every repo, for every person. This is the expensive layer.
  - A rule *with* `paths:` frontmatter loads only when Claude reads a matching file.
    Nearly free until relevant.
  - A skill contributes only its frontmatter (name + description) at startup; the body
    loads when invoked. So skill count is cheap, but a bloated *description* is not.

Token figures are chars/4, the standard rough English estimate. They are for comparing
options and tracking a trend, not for billing.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

CHARS_PER_TOKEN = 4
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
PATH_SCOPED = re.compile(r"^---\s*\npaths:", re.S)

# A description much past this is doing something other than helping the model decide
# whether to load the skill.
DESCRIPTION_BUDGET = 400


def tokens(chars: int) -> int:
    return chars // CHARS_PER_TOKEN


def scan_rules(root: pathlib.Path) -> tuple[list, list]:
    always, scoped = [], []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(errors="replace")
        entry = (len(text), path.relative_to(root))
        (scoped if PATH_SCOPED.match(text) else always).append(entry)
    return always, scoped


def scan_skills(root: pathlib.Path) -> list:
    found = []
    for path in sorted(root.glob("*/SKILL.md")):
        match = FRONTMATTER.match(path.read_text(errors="replace"))
        if match:
            found.append((len(match.group(1)), path.parent.name))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".claude",
        help="harness root to inspect (default: ~/.claude)",
    )
    parser.add_argument("--top", type=int, default=8, help="how many worst offenders to list")
    args = parser.parse_args()

    rules_root = args.root / "rules"
    skills_root = args.root / "skills"
    if not rules_root.exists() and not skills_root.exists():
        print(f"nothing installed under {args.root} — run `make install`", file=sys.stderr)
        return 1

    always, scoped = scan_rules(rules_root) if rules_root.exists() else ([], [])
    skills = scan_skills(skills_root) if skills_root.exists() else []

    always_chars = sum(c for c, _ in always)
    scoped_chars = sum(c for c, _ in scoped)
    skill_chars = sum(c for c, _ in skills)
    startup = always_chars + skill_chars

    print(f"Context cost of the installed config  ({args.root})\n")
    print(f"  {'PAID EVERY SESSION':<24} {'chars':>9}  {'~tokens':>8}")
    print(f"  {'-' * 24} {'-' * 9}  {'-' * 8}")
    print(f"  {'rules (always-on)':<24} {always_chars:>9,}  {tokens(always_chars):>8,}")
    print(f"  {'skill descriptions':<24} {skill_chars:>9,}  {tokens(skill_chars):>8,}")
    print(f"  {'TOTAL AT STARTUP':<24} {startup:>9,}  {tokens(startup):>8,}")
    print()
    print(f"  {'LOADED ON DEMAND':<24} {'chars':>9}  {'~tokens':>8}")
    print(f"  {'-' * 24} {'-' * 9}  {'-' * 8}")
    print(f"  {'rules (path-scoped)':<24} {scoped_chars:>9,}  {tokens(scoped_chars):>8,}")
    print(f"  {len(skills)} skill bodies{'':<10} {'—':>9}  {'—':>8}")
    print()
    print(f"  {len(always)} always-on rule files, {len(scoped)} path-scoped, {len(skills)} skills")

    if always:
        print("\nAlways-on rules, largest first — this is where pruning pays:")
        for chars, rel in sorted(always, reverse=True)[: args.top]:
            print(f"  {chars:6,} chars  ~{tokens(chars):5,} tok  {rel}")
        print("\n  A rule that is not needed in every session wants `paths:` frontmatter.")
        print("  A rule that is documentation rather than instruction should not install at all.")

    over = [(c, n) for c, n in skills if c > DESCRIPTION_BUDGET]
    if over:
        print(f"\n{len(over)} skill description(s) over {DESCRIPTION_BUDGET} chars:")
        for chars, name in sorted(over, reverse=True)[: args.top]:
            print(f"  {chars:6,} chars  ~{tokens(chars):5,} tok  {name}")
        print("\n  Only the description is paid for at startup. Long trigger blocks are")
        print("  the one way a skill becomes expensive without being used.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
