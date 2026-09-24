#!/usr/bin/env python3
"""Generate a skill carrying the team conventions, from the rules.

Why this exists. Rules install to Claude, Cursor and Antigravity only. Codex and
opencode have no rules layer at all, so on a machine with all five harnesses the
team's conventions reach exactly one of them — verified: a distinctive line from
`custom/rules/gcp.md` appears in 8 files under `~/.claude/` and in **zero** under
`~/.codex/` or `~/.opencode/`.

That inverts the point of the repo. If Claude is unavailable and someone moves to
Codex, they lose every convention at the moment they can least afford to.

Skills are the only unit that reaches all five harnesses. So the rules stay the
rules — always-on context where the harness supports it — and this generates a
skill from the same text, so nothing is maintained twice and the two cannot drift.

Run by `make conventions`, and checked by pre-commit: if the generated file does
not match the rules, the commit fails. Same idea as a lockfile.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "custom" / "rules"
OUT = REPO / "custom" / "skills" / "team-conventions" / "SKILL.md"

FRONTMATTER = re.compile(r"^---\s*\n.*?\n---\s*\n", re.S)
# The blockquote under each rule's heading explains `paths:` scoping to a rules
# maintainer. That is noise inside a skill, which has no scoping mechanism. Line-based
# on purpose: with re.DOTALL this swallowed entire files.
LEAD_QUOTE = re.compile(r"^>.*(?:\n>.*)*\n?", re.M)

HEADER = """---
name: team-conventions
description: The team's Python, GCP and agent-building conventions. Load at the start of any
  task in a team repository, and before writing Python, touching a GCP project, running gcloud
  or bq, or building an agent. Required reading in Codex and opencode, which have no rules
  layer and therefore receive these conventions no other way.
---

# Team conventions

**Generated — do not edit.** Source of truth is `custom/rules/*.md` in
`agent-harness-config`; regenerate with `make conventions`.

This exists because rules only install to Claude, Cursor and Antigravity. Codex and opencode
have no rules layer, so without this skill the team's conventions would apply in some tools
and not others — which is the vendor lock-in the shared config exists to prevent.

In Claude, Cursor and Antigravity these same conventions are already in context as rules;
loading this skill is harmless but redundant. In Codex and opencode, this is the only copy.

"""


def body_of(path: Path) -> str:
    text = path.read_text()
    text = FRONTMATTER.sub("", text, count=1)
    # Drop the leading explanatory blockquote, then demote headings one level so the
    # concatenation nests under this skill's own H1.
    text = LEAD_QUOTE.sub("\n", text, count=1)
    text = re.sub(r"^(#+) ", r"#\1 ", text, flags=re.M)
    return text.strip()


def render() -> str:
    sources = sorted(p for p in RULES.glob("*.md") if p.name != "README.md")
    if not sources:
        sys.exit("no rules found in custom/rules/ — nothing to generate")
    parts = [HEADER.rstrip() + "\n"]
    for path in sources:
        parts.append(body_of(path))
    parts.append(
        "---\n\n"
        "Rules that must *block* rather than advise are not here — a skill cannot enforce. "
        "Those live in `.pre-commit-config.yaml` in each repo, and in the two hooks described "
        "in `UPSTREAM.md`.\n"
    )
    return "\n\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the generated skill is stale, without writing",
    )
    args = parser.parse_args()

    content = render()

    if args.check:
        current = OUT.read_text() if OUT.exists() else ""
        if current != content:
            print(
                f"{OUT.relative_to(REPO)} is stale — run `make conventions` and commit it",
                file=sys.stderr,
            )
            return 1
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content)
    lines = content.count("\n") + 1
    print(f"wrote {OUT.relative_to(REPO)} ({lines} lines) from {RULES.name}/*.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
