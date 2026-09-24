---
paths:
  - "**/.gitignore"
  - "**/.dvcignore"
  - "**/.dockerignore"
---
# `.gitignore`

## Every repo ignores these

```gitignore
# Finder and editor clutter
.DS_Store

# Agent working notes — local only
notes/
TODO.md
TODOs.md
INSTRUCTIONS.md
```

`.DS_Store` is not optional: macOS writes one into every directory anyone opens in Finder,
and it reaches a shared branch the first time somebody runs `git add -A`.

`TODO.md`, `TODOs.md` and `INSTRUCTIONS.md` are working material — written fast, aimed at
one reader, and stale within a week. **If the repo already tracks one, ask whether to keep
it in version control before changing anything**; do not silently untrack a file somebody
is relying on. When the answer is to keep it, say so in a comment above the line you
removed. Conclusions worth keeping graduate into `README.md`, `AGENTS.md` or `CHANGELOG.md`.

If a file is already tracked, adding it here does nothing — `git rm --cached <file>` is
what stops it, and that is a change worth mentioning rather than slipping into a commit.

## Anchor patterns to the root

A pattern with no leading slash matches at **any** depth. In `sectorradar` a bare `lib/`
meant for Python build output silently swallowed `web/src/lib/`, so the front end's runtime
was never committed and a fresh clone could not build. A bare `data/` took `web/src/data/`
the same way.

Write `/build/`, `/dist/`, `/lib/` when you mean the repository root.

## Git has no inline comments

The whole line is the pattern, trailing comment included, so this ignores nothing:

```gitignore
dist/          # build output
```

It does not error. It quietly fails to match `dist/`, and you find out when build output
turns up in a merge request. Comments go on their own line.

## Check rather than assume

`git check-ignore -v <path>` prints the rule that matches, and prints nothing when none
does. `git status --ignored` shows what is actually being held back.
