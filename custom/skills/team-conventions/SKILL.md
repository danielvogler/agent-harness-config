---
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


## Building agents — team conventions



### Prompts are code

They live in their own files, version-controlled and reviewed — not in triple-quoted
strings scattered through the source. A prompt change is a behaviour change.

### Every autonomous loop needs a ceiling

Max iterations, max spend, or a wall clock — set before the first run, not after the
surprise. Anything irreversible (writes to shared storage, deletes, sends, publishes)
needs a human in the loop, or a dry-run mode that is the default.

### Evaluation

- **A behaviour without a test is a rumour.** Before an agent is relied on, write the
  handful of cases that define "working", including the failure cases.
- Evaluate on held-out examples the prompt was not tuned against.
- **Record the model and its version with every result.** Model updates change behaviour,
  and undated agent output is not citable.

### Scientific integrity

This is the part with no equivalent anywhere else in this config.

- An agent may draft, search and summarise. **It does not get to be the source of a
  factual claim.** Every number and citation traces to a document a human can open.
- Log every tool call — name, arguments, outcome. Persist the full trace of any run whose
  output reaches a paper or a decision. An agent you cannot replay is one whose results
  you cannot defend.
- Never let generated text into a manuscript without recording what was generated and who
  checked it. Journals and funders increasingly require the disclosure.

## Writing documents

**Check the date before writing one.** Run `date +"%Y-%m-%d"`. Some harnesses supply
today's date and some do not, and a model's own sense of it comes from training data.

This covers every "Last updated" and "Analysis date" field, dated filenames, and anything
rendered to PDF — where a wrong date is invisible until someone cites it. Never carry a
date forward from an older document without re-checking it.

## GCP — conventions

### What data may go into the cloud at all

Whoever puts data somewhere is the one who classifies it. Four levels: **public**,
**internal**, **confidential**, **strictly confidential**.

- **Public and internal** — fine in a project bucket.
- **Confidential** — needs a cloud assessment first. Ask before uploading.
- **Strictly confidential** — never goes to an external cloud service at all.

Unsure which level? Then it is not public. Ask before uploading.

### Credentials

- **Application Default Credentials** for people, attached service accounts for workloads.
- **Never create or download a service-account key file.** A `*.json` key in a repo, a
  home directory or an image is the most common way a project like this leaks. One that
  already exists is compromised: rotate, then delete.
- Secrets live in **Secret Manager**, fetched at runtime — never a committed `.env`, an
  infrastructure variable, or a notebook cell.
- Never print or log a credential, token, or full signed URL.

### Always name the project

Read the project from the active gcloud configuration (`gcloud config get project`), say
which one you are using, and still pass `--project` explicitly on every command. An unstated
ambient default is why things get run against the wrong project.

### Destructive operations need a yes first

`gcloud ... delete`, `bq rm`, `gsutil rm -r`, `terraform destroy` / `tofu destroy`, and
anything dropping a dataset, bucket, table or project: **say what will be destroyed and
wait for explicit confirmation in the conversation.** Do not infer approval from an earlier
unrelated yes. Prefer a reversible step — disable, detach, lifecycle-expire — when one
exists.

### Regions

Pin the region rather than accepting a provider default. Read it from the active gcloud
configuration (`gcloud config get compute/region`); if it is empty, ask the user. Never leave
a bucket, dataset or job in `US` by accident.
Where a data-residency requirement applies, it decides; check before assuming it does not.

### BigQuery — cost is the failure mode, not correctness

- **Dry-run anything unfamiliar** and read the byte estimate first.
- **Set `maximum_bytes_billed` on every programmatic query.** That is what turns a runaway
  query into an error instead of an invoice.
- **Filter the partition column**, and never `SELECT *` on a partitioned or wide table.

## Git — team additions

Add a scope: `fix(storage): ...`, not `fix: ...`. The scope is the area touched.

Emoji: some repos use gitmoji, most do not. Match the repo you are in; do not introduce it
to a repo that has none.

### Shape of a message

Subject in the imperative, under 72 characters, no trailing full stop. Then a blank line,
then bullets — not paragraphs. Wrap at 72.

```
fix(qr): compute the payment amount from the line items

- The QR payload read a stored total that could disagree with the bill.
- Totals are now derived at render time; the stored field is gone.
- Adds a regression test for the CHF 10 mismatch this caused.
```

Say **why** in the message; the diff already shows what. One logical change per commit — if
the bullets need an "also", it is two commits.

### A commit is read by a stranger in two years

**Nothing that needs the session to make sense.** No "as discussed", "as you asked", "per
the review", "the issue you mentioned", "fixed the thing from earlier". No `I`, no `we`, no
apologies, no narration of the process. State the change, not the conversation that
produced it.

Never name an agent, model, tool or session, and **never add AI attribution** — no
`Co-Authored-By` trailer for a tool and no "Generated with ..." line, in a commit message or
in a PR description. Commits and PRs are authored by the person whose name is on them.

Where it is enforced, so do not work around any of it:

- `make setup-user` turns Claude Code's own attribution off (`attribution` in
  `~/.claude/settings.json`), so it is not generated in the first place.
- A `commit-msg` hook rejects it in commit messages, and a PR check runs the same hook on the
  PR description.

A repo that wants attribution opts back in: `attribution` in its own `.claude/settings.json`
overrides the user setting, and it leaves out the hook and the PR check.

### Never commit an absolute path

Not in the message, not in code, not in a committed `.agent/` or `.claude/` file.

- Wrong: ``Updated `/Users/an/git/projects/backend/scripts/import.js` ``
- Right: ``Updated `import.js` `` or ``Fixed `backend/scripts/provision.js` ``

`/Users/<someone>/...` breaks for everyone else and for CI the moment it is shared, and in
a commit message it survives forever. If one is genuinely unavoidable in code, ask first
and leave a comment above it saying why.

### Staging and history

- **Stage named paths.** `git add -A` and `git add .` are how `.DS_Store`, a stray notebook
  and a 200 MB output file get committed. Run `git status` first and look.
- **Never `--no-verify`.** The hook is the convention; skipping it removes the convention.
- **Say the working tree is about to change** before a rebase, reset, checkout or stash,
  and wait. Prefer a squash that leaves the tree untouched.
- **Never rewrite history that is already pushed** to a shared branch.
- Commit or push only when asked. If on the default branch, branch first.

### Filing an issue via API or MCP

`.github/ISSUE_TEMPLATE/` is a web-UI convenience the REST API, and any MCP tool built on
it, never sees. Read the matching template first and copy its title, label and headings.

## `.gitignore`

### Every repo ignores these

```gitignore
## Finder and editor clutter
.DS_Store

## Agent working notes — local only
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

### Anchor patterns to the root

A pattern with no leading slash matches at **any** depth. In `sectorradar` a bare `lib/`
meant for Python build output silently swallowed `web/src/lib/`, so the front end's runtime
was never committed and a fresh clone could not build. A bare `data/` took `web/src/data/`
the same way.

Write `/build/`, `/dist/`, `/lib/` when you mean the repository root.

### Git has no inline comments

The whole line is the pattern, trailing comment included, so this ignores nothing:

```gitignore
dist/          # build output
```

It does not error. It quietly fails to match `dist/`, and you find out when build output
turns up in a merge request. Comments go on their own line.

### Check rather than assume

`git check-ignore -v <path>` prints the rule that matches, and prints nothing when none
does. `git status --ignored` shows what is actually being held back.

## Python — team conventions

### Tooling (overrides upstream)

- **`uv`** for environments, dependencies and locking — not pip, poetry or conda.
  `uv sync` is the setup step; commit `uv.lock`.
- **`ruff check` and `ruff format`** — not black, not isort, not flake8. Line length 110,
  Google docstring convention. Upstream names black + isort; ignore that here.
- **`mypy` strict** and **`pytest`**, both on pre-push rather than pre-commit.
- Hooks via **`prek`**; tasks via a **`justfile`** or **`Makefile`** whose `check` is fmt →
  lint → typecheck → test and runs exactly what CI runs.
- CI is **GitLab** on self-hosted infrastructure, **GitHub Actions** on the public repos.
  Check the remote before writing a pipeline.

### Layout

`src/<package>/` with `tests/` alongside — not a flat module dump at the repo root. One
module per concern; split at ~400 lines rather than growing a 2000-line `utils.py`.

Notebooks are for exploration and figures, never a deliverable and never imported. The
moment a cell is worth running twice it moves into `src/` and the notebook imports it — a
pipeline that only exists as a notebook is not reproducible.

### Signatures

- **No `**kwargs` as a catch-all.** It swallows typos silently, kills autocompletion and
  makes type checking impossible. Declare every parameter with a name and a type. The
  exception is a genuine pass-through wrapper — a decorator, `__init_subclass__`.
- **No `_` prefix on module-level helpers**, and `__name` only inside a class — at module
  level the interpreter does no mangling, so both signal "internal" and enforce nothing.

### Non-negotiables

- **Type hints on every public signature.** Internal helpers can go without.
- **`logging`, never `print`** outside CLI entry points; configure it once at the entry.
- **`pathlib.Path`, not `os.path`** — never string concatenation for paths.
- **No bare `except:`**, no `except Exception: pass`. A swallowed traceback costs hours.
- **No secrets or absolute personal paths in source.** Read from the environment.
- **Seed every stochastic process explicitly** and log the seed.

### Scientific code

- **Vectorising changes the answer.** Float summation order differs, so replacing a loop
  with numpy is not a refactor: compare against the loop with `np.allclose` at a stated
  tolerance before deleting it. Vectorise once it works — correct and slow beats fast and
  wrong.
- **Check shapes and units at function boundaries, and `raise` — never `assert`.** Asserts
  vanish under `python -O`, so the guard is absent in the run that matters. Put the unit in
  the name (`depth_m`, `rate_m3_s`): a name is read every time, a comment never. Unit
  errors are our most expensive bug class, and they are silent.
- **Never `==` on floats**, and decide at the boundary what NaN means. `np.mean` propagates
  it, `np.nanmean` hides it; choosing by accident is how a wrong number reaches a figure.

## Repository layout — team conventions

Reference implementations: `sectorradar`, `billwright`, `talanton`, `atlassian_agent`.

### AGENTS.md is the single source of truth

`CLAUDE.md` and `GEMINI.md` are two-line pointers to it, holding no content of their own.
Never write an instruction into more than one of the three.

Two parts, because two readers arrive: **§A — using this** (the runbook an agent follows
to set it up for somebody: questions first, cheapest run next) and **§B — changing the
code** (layout, setup, checks, conventions, testing). End §B with **Things that will bite
you** and a **Definition of done**.

### README

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

### Makefile is the interface

Every target carries a `## comment` and `help` prints them. `make setup` installs, `make
hooks` installs git hooks, and **`make check` runs exactly what CI runs** — a green `check`
means a green pipeline. Nobody should need the underlying commands.

### Pre-commit

`ruff-check --fix`, `ruff-format`, the `pre-commit-hooks` basics (end-of-file-fixer,
trailing-whitespace, check-{yaml,toml,json}, check-merge-conflict, check-added-large-files,
detect-private-key), `uv-lock`, `gitleaks`.

mypy runs as a **`local`** hook (`entry: uv run mypy`) — the upstream mirror runs isolated,
can't see project deps, and invents import errors.

Add a `commit-msg` pygrep hook rejecting AI attribution (`Co-Authored-By` trailers and
"Generated with" lines), a PR workflow that runs the same hook on the PR description (copy
`pr-description.yml` from the harness repo), and a hook rejecting `"type": "service_account"`
in JSON.

### Also at the root

`LICENSE` (Apache-2.0) with `NOTICE`, `CHANGELOG.md`, `.editorconfig`, `.python-version`,
`.env.example` listing every variable with no values, a committed `uv.lock`.

---

Rules that must *block* rather than advise are not here — a skill cannot enforce. Those live in `.pre-commit-config.yaml` in each repo, and in the two hooks described in `UPSTREAM.md`.
