---
name: new-repo
description: Use when the person asks to start a new repository, or to bring an existing one up to the team's structure ("set up a repo", "make this repo conform"). Lists what a repository gets and in which order, and where each rule lives, so the files are written for this repo instead of copied from another.
---

# Start a repository, or bring one up to the structure

The rules are in `custom/rules/`, installed under `~/.claude/rules/ecc/custom/`. This skill
says what to create and in which order; it does not repeat the rules. Read the one named in
each step before writing its file, and create only what the repo needs: a file that would be
empty or repeat another is not created.

## Ask first

1. What the thing does, in one sentence, and for whom.
2. The language and tooling (Python with uv is the default here), and whether it ships an
   agent (then `agents.md` applies too).
3. The owner and whether the repo is public. In a public repo nothing names a client.
4. The folder AGENTS.md should name for rendered output (default `out/`, gitignored).

## Create, in this order

1. **`AGENTS.md`** from `repo.md` and `change.md`: §A using this, §B changing the code. §B
   opens with "How a change moves", adapted to this repo, and has the "Where each fact
   lives" table. It ends with "Things that will bite you" and a "Definition of done".
   `CLAUDE.md` and `GEMINI.md` are two-line pointers to it.
2. **`Makefile`** from `repo.md`: `help`, `setup`, `hooks`, `check` (exactly what CI runs),
   and `test` when there are tests. Every target has a `## comment`.
3. **`.pre-commit-config.yaml`** from `repo.md` and `python.md`. Pin this repo's shared
   hooks by tag rather than copying their patterns:

   ```yaml
   - repo: https://github.com/danielvogler/agent-harness-config
     rev: <the newest tag>
     hooks: [{id: no-ai-attribution}, {id: no-commit-emoji},
             {id: no-service-account-key}, {id: repo-conformance}]
   ```

   `make hooks` installs the commit-msg stage too. Copy `.github/workflows/pr-description.yml`
   from this repo, and add CI that runs `make check`.
4. **The project itself**, for Python per `python.md`: `pyproject.toml` with uv, ruff, mypy
   and pytest, `.python-version`, a committed `uv.lock`, one test that fails without the
   first real code.
5. **The root files** from `repo.md` "Also at the root": `LICENSE` and `NOTICE`,
   `CHANGELOG.md` with an Unreleased section, `.editorconfig`, `.gitignore` per
   `gitignore.md`, and `.env.example` with names and no values.
6. **`README.md`** from `repo.md`: the banner pair, the badges, one bold sentence in the
   user's words, and "Start here" pointing at AGENTS.md. Make the banner with the
   `house-style` skill; do not hand-draw it.
7. **`docs/ARCHITECTURE.md`** from `ledgers.md`, with a first decision for each real choice
   already made (the language, where it runs). Not created when there is none yet.

The `.agent/` ledgers and `docs/BACKLOG.md` are not created up front. Each starts with its
first row.

## An existing repo

Work through the same list, and change one file per commit. Fill the ledgers from the git
history, TODO files and open change requests, and write `docs/ARCHITECTURE.md` from commit
messages and plans, as `ledgers.md` describes. Move open items out of AGENTS.md into
`.agent/FINDINGS.md`.

## Done when

`make check` passes, including `repo-conformance`; `make help` lists every target; the README
banner is rendered and looked at in light and dark mode (`docs.md`); and the first commit
follows `git.md`.
