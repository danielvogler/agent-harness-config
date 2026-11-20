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

## AGENTS.md is the single source of truth

`CLAUDE.md` and `GEMINI.md` are two-line pointers to it, holding no content of their own.
Never write an instruction into more than one of the three.

Two parts for two readers: **§A — using this** (the runbook for setting it up for somebody:
questions first, cheapest run next) and **§B — changing the code**, opening with "How a change
moves" (`change.md`), ending with **Things that will bite you** and a **Definition of done**.

## README

1. `<picture>` with `docs/assets/banner-{dark,light}.svg`; `alt` says what the thing does.
2. Badges (CI, licence, Python, uv, Ruff, mypy, pre-commit, gitleaks), flat `0E0E10`.
3. One bold sentence, in the user's words rather than the architecture's.
4. **Start here**, handing the reader to `AGENTS.md`.

The banner, the architecture picture (what runs where, updated in the same pull request as
what it shows), the README hero graph, mermaid diagrams with their `%%{init}%%` theme line,
HTML reports, dashboards and one-pagers follow the `house-style` skill.

## Makefile is the interface

Every target carries a `## comment` and `help` prints them. `make setup` installs, `make
hooks` installs git hooks, and **`make check` runs exactly what CI runs** — a green `check`
means a green pipeline. Nobody should need the underlying commands.

## Pre-commit

`ruff-check --fix`, `ruff-format`, the `pre-commit-hooks` basics (end-of-file-fixer,
trailing-whitespace, check-{yaml,toml,json}, check-merge-conflict, check-added-large-files,
detect-private-key), `uv-lock`, `gitleaks`. mypy runs as a **`local`** hook (`entry: uv run
mypy`): the upstream mirror runs isolated, can't see project deps, and invents import errors.

Reference the harness repo's hooks by tag, never copy them; copy only `pr-description.yml`, which
runs `no-ai-attribution` on PRs. Set `default_install_hook_types: [pre-commit, commit-msg]`.

```yaml
- repo: https://github.com/danielvogler/agent-harness-config
  rev: <tag>
  hooks: [{id: no-ai-attribution}, {id: no-commit-emoji},
          {id: no-service-account-key}, {id: repo-conformance}]
```

## Also at the root

`LICENSE` (Apache-2.0) with `NOTICE`, `CHANGELOG.md`, `.editorconfig`, `.python-version`,
`.env.example` listing every variable with no values, a committed `uv.lock`.
