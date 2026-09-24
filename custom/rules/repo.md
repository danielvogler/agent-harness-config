---
paths:
  - "**/README.md"
  - "**/AGENTS.md"
  - "**/CLAUDE.md"
  - "**/GEMINI.md"
  - "**/Makefile"
  - "**/.pre-commit-config.yaml"
---
# Repository layout — team conventions

Reference implementations: `sectorradar`, `billwright`, `talanton`, `atlassian_agent`.

## AGENTS.md is the single source of truth

`CLAUDE.md` and `GEMINI.md` are two-line pointers to it, holding no content of their own.
Never write an instruction into more than one of the three.

Two parts, because two readers arrive: **§A — using this** (the runbook an agent follows
to set it up for somebody: questions first, cheapest run next) and **§B — changing the
code** (layout, setup, checks, conventions, testing). End §B with **Things that will bite
you** and a **Definition of done**.

## README

1. `<picture>` with `docs/assets/banner-{dark,light}.svg`; `alt` is the one-line
   description of what the thing does.
2. Badges — CI, licence, Python, uv, Ruff, mypy, pre-commit, gitleaks — flat `0E0E10`,
   not default coloured shields.
3. One bold sentence, in the user's words rather than the architecture's.
4. **Start here**, handing the reader to `AGENTS.md`.

Diagrams are mermaid, themed — Google Material, one `%%{init}%%` line before the graph:

```
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#FFFFFF","primaryTextColor":"#202124","primaryBorderColor":"#DADCE0","lineColor":"#5F6368","secondaryColor":"#F8F9FA","tertiaryColor":"#F8F9FA","clusterBkg":"#F8F9FA","clusterBorder":"#DADCE0","edgeLabelBackground":"#FFFFFF"},"flowchart":{"curve":"basis","nodeSpacing":40,"rankSpacing":64,"useMaxWidth":true}} }%%
```

Draw the trust boundary, not the call graph. Colour the node where a human approves.

## Makefile is the interface

Every target carries a `## comment` and `help` prints them. `make setup` installs, `make
hooks` installs git hooks, and **`make check` runs exactly what CI runs** — a green `check`
means a green pipeline. Nobody should need the underlying commands.

## Pre-commit

`ruff-check --fix`, `ruff-format`, the `pre-commit-hooks` basics (end-of-file-fixer,
trailing-whitespace, check-{yaml,toml,json}, check-merge-conflict, check-added-large-files,
detect-private-key), `uv-lock`, `gitleaks`.

mypy runs as a **`local`** hook (`entry: uv run mypy`) — the upstream mirror runs isolated,
can't see project deps, and invents import errors.

Add a `commit-msg` pygrep hook rejecting AI attribution (`Co-Authored-By` trailers and
"Generated with" lines), a PR workflow that runs the same hook on the PR description (copy
`pr-description.yml` from the harness repo), and a hook rejecting `"type": "service_account"`
in JSON.

## Also at the root

`LICENSE` (Apache-2.0) with `NOTICE`, `CHANGELOG.md`, `.editorconfig`, `.python-version`,
`.env.example` listing every variable with no values, a committed `uv.lock`.
