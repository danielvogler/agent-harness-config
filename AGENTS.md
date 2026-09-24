# AGENTS.md

This repo is the team's shared agent configuration. It is **build material, not a workspace** —
nobody develops here. It writes into `~`, and every harness picks things up from there in every
other project.

It holds a pinned reference to [ECC](https://github.com/affaan-m/ECC) plus our own content. It
does **not** contain a copy of ECC; that gets cloned at install time.

Two readers arrive here. Setting it up for someone: read part A and stop. Changing the
repo: read both.

## A. Setting it up for someone

Ask before you run anything:

1. **Which tools do they use?** Claude Code, Codex and opencode install once for the whole
   machine. Cursor and Antigravity install per project, so ask which project folders.
2. **Do they want the Confluence, Jira, GitHub and BigQuery servers?** If yes, they need
   their Confluence URL and token (and optionally Jira's) first. Ask for them; never guess.
   They go in `.env`, copied from `.env.example`, which lists every variable `make mcp`
   reads.

Then run, in order: `make install`, `make setup-user`, `make doctor`, then
`make install-project PROJECT=<path>` for each Cursor or Antigravity project, then `make mcp`
if they want the servers. `make doctor` should report nothing to fix.

## Install and update

```bash
make install     # once per person, per machine — copies the files
make setup-user  # once per person — turns them on (permissions, hooks, no AI attribution, codex conventions)
make update      # thereafter — pulls this repo and reinstalls
```

`make mcp` is separate and reads personal values from `.env` (copy `.env.example`) or the
environment: `CONFLUENCE_URL` and `CONFLUENCE_TOKEN` (plus optional `JIRA_URL` and
`JIRA_TOKEN`) for Atlassian, `GITHUB_PERSONAL_ACCESS_TOKEN` for GitHub (fine-grained, scoped
to the repos you use). If you are an agent setting this up for someone, ask them for those
rather than guessing; `make mcp` names the variable and skips that one server when it cannot
find it. Tokens come from each system's own profile settings.

Contributing to this repo (not needed just to install it):

```bash
uv tool install pre-commit   # make setup only needs it on PATH
make setup                   # activates the pre-commit hooks
```

Other targets:

```bash
make plan        # show what install would write, without writing anything
make doctor      # is what you have installed still current?
make context     # what the installed config costs in context every session
make check       # everything CI runs (hooks, tests, then the overlay against the pinned upstream)
make test        # unit tests for tools/ (pip install -r requirements-dev.txt first)
make mcp         # activate the agreed MCP servers (writes to your Claude config)
make reinstall   # clean reinstall — clears files dropped from custom/
make bump        # show what changing the upstream pin would do
make uninstall   # remove everything installed (only files recorded in install-state)
make audit       # scan the installed config with AgentShield
make validate    # check the pin, the overlay and custom/ are consistent
make clean       # remove the materialized .ecc/ checkout
```

`make install` is reversible: ECC records every file it writes in an install-state file, and
`make uninstall` removes exactly those. It does not touch unrelated files in your harness
directories.

Prerequisites: `git`, `node`, `python3`, `make`. `make install` clones ECC at the pinned SHA
into `.ecc/` (gitignored), copies `custom/` into it, patches its manifests from
`overlay/manifest-overlay.json`, then runs ECC's installer against the result.

If someone reports a broken install, `make doctor` is the first thing to run — it compares the
upstream SHA and content actually installed against this checkout, and most answers are "you are
behind, run `make update`". If doctor is clean and the install is still wrong,
`make clean && make plan` rebuilds `.ecc/` from scratch and shows the plan without writing.

## Where files land

Claude Code, Codex and opencode install to **user scope**: there is no directory to `cd`
into. Cursor and Antigravity install into one project at a time, with
`make install-project PROJECT=<path>`.

| | Claude | Cursor | Codex | Antigravity | opencode |
| --- | --- | --- | --- | --- | --- |
| **Skills** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Agents** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Commands** | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Rules** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Hooks** | ✅ | ✅ | ❌ | ❌ | ✅ |

Roughly: `~/.claude/`, `~/.codex/`, `~/.config/opencode/`, and `.cursor/` and `.agents/` in
each project installed with `make install-project`.

The gaps are inherent to the harnesses, not to our tooling. Codex has no hook system, so nothing
can give it one.

## B. Changing this repo

Everything below is for contributors. Rules this repo installs land in Claude Code at
`~/.claude/rules/ecc/` — user scope, so a project's own `./CLAUDE.md` or `./.claude/rules/`
wins on conflict. Intended: the shared config is a floor, not a ceiling.

## How to contribute

### Add a skill

Drop a directory containing `SKILL.md` into `custom/skills/` and open a PR. Nothing else needs
wiring — `custom-skills` already points at that directory and is already in the profile.

The frontmatter `name` **must** match the directory name, or the skill will not load:

```markdown
---
name: my-skill
description: Use when ... — one line, written so an agent can decide whether to load it.
---
```

### Add a command or a rule

Same shape, into `custom/commands/` or `custom/rules/`. Commands are prompt macros invoked as
`/name`; their frontmatter is `description` plus optional `argument-hint`.

### Add a whole source repo

1. Put its content under `custom/<kind>/`.
2. Add a module entry to `overlay/manifest-overlay.json`:

   ```json
   {
     "id": "custom-example",
     "kind": "skills",
     "description": "One line on what this provides and where it came from.",
     "paths": ["custom/example"],
     "targets": ["claude", "cursor", "codex", "antigravity", "opencode"],
     "dependencies": [],
     "defaultInstall": false,
     "cost": "light",
     "stability": "stable"
   }
   ```

   All nine fields are required and no others are allowed — the upstream schema sets
   `additionalProperties: false`.
3. Add the module id to the `custom` profile in the same file.
4. Record the source repo and the SHA you vendored from in `upstream.json`.
5. Put its license text in `THIRD_PARTY_LICENSES/` as `<owner>-<repo>.txt`, plus its
   `NOTICE` if it has one, and add a row to `THIRD_PARTY_LICENSES/README.md`.

Keep every source remote URL in `upstream.json` and nowhere else, so moving the sources to a
shared org later is a one-line edit rather than a hunt.

### Which layer to choose

| Want it to... | Use | Reaches |
| --- | --- | --- |
| work in every harness | **skill** | all five |
| be a repeatable prompt you invoke | **command** | all but Codex |
| passively guide behaviour | **rule** | Claude, Cursor, Antigravity |
| actually *block* something | **hook** | Claude, Cursor, opencode |

Rules are advisory — they shape behaviour, they cannot stop anything. If it must actually
block, it is a hook or a pre-commit hook, not a rule. When in doubt, write a skill: it is the
only unit that reaches everywhere.

## Keep the docs current in the same PR

Not a separate chore — a change that lands without its documentation is a change the next
person has to reverse-engineer.

| If your change... | Update |
| --- | --- |
| alters what lands in `~`, or adds a target/module/skill/rule | `CHANGELOG.md` under `## [Unreleased]` |
| changes install, update or any `make` target | `README.md` |
| touches the pin, the overlay, or anything about upstream's behaviour | `UPSTREAM.md` |
| changes how content is authored or which layer to pick | this file |
| changes the variables `make mcp` reads | `.env.example` |
| changes what loads when, or where files land | the diagrams and tables in `README.md` |

`UPSTREAM.md` is specific to this repo — it exists because we consume a pinned upstream, and
nothing else we build does. The other three generalise.

Two things that are *not* documentation chores but read like them:

- **A finding about upstream goes in `UPSTREAM.md`, not in a commit message.** Commit
  messages are not searchable by someone hitting the same problem in six months.
- **Working notes stay out of git.** `notes/` is ignored in full. Only conclusions graduate,
  into this file, `README.md`, `UPSTREAM.md`, `CHANGELOG.md` or `custom/rules/`.

## Conventions

- **`custom-` is a reserved prefix.** Our module ids use it, and it is reserved for skill names
  too. `make validate` fails if a name in `custom/skills/` ever collides with an upstream skill
  — both install into the same directory, so a collision would silently shadow.
- **Vendored content stays byte-identical to its source**, so it can be re-synced. If something
  in `custom/skills/` needs fixing, fix it upstream and re-vendor. Local fixes are recorded in
  `UPSTREAM.md` and are meant to be temporary.
- **Never track upstream `main`.** It takes daily commits. Bumping the pin is deliberate: edit
  the SHA in `upstream.json`, run `make validate && make plan`, read the diff, commit. Review
  monthly, never auto-merge.
- **Never install `--profile full`.** It pulls modules we removed for good reasons.

## Don'ts

- Don't commit `.ecc/`. It is generated and gitignored. The pin is the source of truth, not a
  copy of upstream's files.
- Don't edit anything inside `.ecc/` — it is wiped and rebuilt on every install. Changes to
  upstream behaviour go through `overlay/manifest-overlay.json`, and get written up in
  `UPSTREAM.md`.
- Don't add an MCP server without recording in `UPSTREAM.md` what it reaches, which
  credentials it needs, who owns them, and the blast radius if compromised. Adding it to
  `activateMcpServers.ids` means everyone runs it on the next `make mcp`.
- Don't author rules without review. `custom/rules/` holds `agents.md`, `docs.md`, `gcp.md`,
  `git.md`, `gitignore.md`, `python.md` and `repo.md`; keep each under the 60-line ceiling and
  scope it with `paths:` unless it must be in context before a shell command. Rules are
  always-on context, paid on every session by every person — `make context` shows the bill.
- **Scope a rule with the narrowest glob that works.** Upstream's `arkts/*.md` claims
  `**/*.ts` and `react-native/*.md` claims `**/*.ts,tsx`, so touching one TypeScript file
  loads thirteen rule files where five were wanted. A `paths:` entry is a claim on everyone's
  context budget; `**/*.md` and `**/*.ts` are almost always too broad.

## Maintenance

The failure mode for a shared repo is not technical — it is that one person maintains it and
everyone else quietly drifts back to their own local config. Guard against that: contributing
must stay a five-minute PR, and pruning is a team decision, not a unilateral one. Someone's
quiet dependency is easy to delete by accident.

Quarterly, prune with `context-budget`, `config-gc` and `skill-stocktake`. Context cost is real
and worth setting a ceiling on.

## Things that will bite you

- **A change under `custom/` does not exist until `make install`.** `make doctor` names the
  file you forgot to install.
- **The installer adds and overwrites, but never removes.** A file dropped from `custom/`
  stays in everyone's `~` until they run `make reinstall`.
- **Editing a rule means regenerating the conventions skill.** Run `make conventions`; the
  pre-commit hook fails until the two match.
- **pre-commit excludes `custom/` for every hook.** A hook with a `files:` filter on
  `custom/` never fires. Use `always_run: true` and filter inside the script.
- **Adding a rule costs every person, every session.** Run `make context` before and after.
- **Cursor and Antigravity are per project.** `make install` alone does not reach them.

## Definition of done

- `make check` passes. It runs what CI runs.
- If `custom/` changed: `make install`, then `make doctor` reports nothing to fix.
- The docs in the table under *Keep the docs current* are updated in the same PR.
- Commits are conventional with a scope (`fix(hooks): ...`), explain why, and carry no AI
  attribution: no `Co-Authored-By` trailer, no "Generated with" line. PR descriptions
  neither.
