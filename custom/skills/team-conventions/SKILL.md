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

## How a change moves — team conventions

Goes at the top of AGENTS.md §B, adapted to the repo. The ledgers it names are in
`ledgers.md`.

1. **Branch.** Off `main`, in the checkout the person has open: branch there, no extra
   folder. A separate checkout only for a long-running process (a loop, a server), or
   when the person asks for one. Rendered output (a PDF, an image, a built page) goes to
   the one folder the repo's AGENTS.md names for it in the person's main checkout, never
   only into a separate checkout, so there is one place to look.
2. **One milestone.** One logical change, a test that fails without it, `make check`, one
   commit. Small and buildable, not a day-long branch. A gate passes on its exit code,
   never on grepping its output for "passed".
3. **Show it.** Run the change for real once. Until then it is listed in
   `.agent/DEFERRED_VERIFICATION.md`.
4. **Route what is not the task.** Anything noticed on the way goes to a ledger, not into
   this change.
5. **Integrate.** Up to date with `main`, `make check`, one independent review pass, then
   at most one recheck; what it finds after that is fixed forward. Open a pull request;
   the person merges it on GitHub. Push only when the person says so; never force-push.
   Once a PR link has been given, a further change goes on a fresh branch and a new PR;
   check the PR's state before pushing to its branch. When a permission check refuses an
   action, hand the person the exact command; do not look for another route.
6. **Close.** Once merged: delete the branch, remove a separate checkout if there was one,
   and in the main checkout `git switch main && git pull --ff-only`, which tags the
   release when the repo uses the `auto-release` hook. Ledgers updated, nothing left open.

### Where each fact lives

One place per fact; no second copy anywhere. A repository creates only the files it needs.

| Fact | Owner |
|---|---|
| Rules, commands, gates, how a change moves | `AGENTS.md` |
| What the thing is for and for whom | `docs/PRODUCT.md`, only if the README does not say it |
| Why it is built the way it is | `docs/ARCHITECTURE.md` |
| Work a person has chosen to do | `docs/BACKLOG.md` |
| Setup, first run, everyday use | `README.md` |
| What changed for users | `CHANGELOG.md` |
| Open observations and proposals | the ledgers in `.agent/` |

Code and tests own the behaviour. Documents keep intent and decisions, not a second
implementation. Every document states how things are, not how they came to be.

## Writing documents

**Check the date before writing one.** Run `date +"%Y-%m-%d"`. Some harnesses supply
today's date and some do not, and a model's own sense of it comes from training data.

This covers every "Last updated" and "Analysis date" field, dated filenames, and anything
rendered to PDF — where a wrong date is invisible until someone cites it. Never carry a
date forward from an older document without re-checking it.

### Look at it before calling it done

Anything rendered (a slide, a page, a diagram, a PDF) is opened and looked at, every page,
with the Read tool on the image or preview, before the reply says it is done. Check for
text overflowing its box, overlapping or clipped elements, images upside down or cropped,
arrows that miss their target, and the same element styled differently across pages. Say
which pages you looked at. A build that succeeded says nothing about how it looks.

### Plain words

Titles and copy are plain statements. No "From X to Y:" openers, no "X, not Y" contrasts,
no counted slogans ("One agent, two questions"), no colon set-ups, no numbers that carry no
information. Name the subject of every heading and tile: "Solver converges", not
"Converges". Read each line alone and ask whether a person would have written it.

No absolute claim that is only usually true; write "often" or "mostly". A share, split or
rule of thumb needs a named published source, or it goes.

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

No emoji in a commit message, in any repo, gitmoji repos included. The type and scope
already say what an emoji would. A Claude Code hook and the repo's commit-msg hook refuse it.

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
produced it. PR titles and descriptions follow the same rule: the change and its reason,
never what someone wanted or what was discussed.

Never name an agent, model, tool or session, and **never add AI attribution** — no
`Co-Authored-By` trailer for a tool and no "Generated with ..." line, in a commit message or
in a PR description. Commits and PRs are authored by the person whose name is on them.

`make setup-user` turns Claude Code's attribution off, and a `commit-msg` hook plus a PR
check reject it; do not work around either. A repo that wants it back sets `attribution`
in its own `.claude/settings.json` and leaves out the hook and the check.

### Never commit an absolute path

Not in the message, not in code, not in a committed `.agent/` or `.claude/` file. Write
`backend/scripts/import.js`, never `/Users/<someone>/...`: that breaks for everyone else and
for CI, and in a commit message it survives forever. If one is unavoidable in code, ask
first and leave a comment above it saying why.

### Staging and history

- **Stage named paths.** `git add -A` and `git add .` are how `.DS_Store`, a stray notebook
  and a 200 MB output file get committed. Run `git status` first and look.
- **Never `--no-verify`.** The hook is the convention; skipping it removes the convention.
- **Say the working tree is about to change** before a rebase, reset, checkout or stash,
  and wait. Prefer a squash that leaves the tree untouched.
- **Never rewrite history that is already pushed** to a shared branch.
- Commit or push only when asked. If on the default branch, branch first.
- **Regroup before the pull request:** one commit per logical change, before the push.

### Pushing

The person's setup decides which credential pushes where. Before the first push, run
`git push --dry-run`; if it is refused, give the person the exact push command and open the
pull request once they have pushed. Never switch remote URL, protocol, token or SSH key.

### Issues via API or MCP

`.github/ISSUE_TEMPLATE/` is a web-UI convenience the REST API, and any MCP tool built on
it, never sees. Read the matching template first and copy its title, label and headings.

Sub-issue listings span repositories: a child's `number` is in its own repo. Act on
`html_url` or `repository_url`, never the bare `number`, and print number, repo and title
before a batch edit.

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

A pattern with no leading slash matches at **any** depth. In one of our repos a bare `lib/`
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

## Ledgers, ARCHITECTURE and BACKLOG — team conventions

### The ledgers in `.agent/`

Tracked. An entry grants no new scope: it is recorded, and a person decides. Each row
names its evidence (a commit, a file, a run, a date). Ids are prefixed (F1, D1, A1, U1).

A ledger lists only what is open. A row that is done, declined or verified is deleted in
the commit that settles it, and that commit's message records the decision. What still
matters later moves to its owner first: a rule in AGENTS.md, a decision in
`docs/ARCHITECTURE.md`, a check. An empty ledger is not created.

| File | Holds | Columns |
|---|---|---|
| `FINDINGS.md` | Observations outside the task, with the agent's proposed triage (now, later, check, drop). A picked row moves to `docs/BACKLOG.md`. | #, finding, status, proposed, evidence |
| `DEFERRED_VERIFICATION.md` | Commits no real run has shown working yet. | commit, change, risk, evidence that would close it |
| `AGENT_IMPROVEMENTS.md` | Proposals for how work in the repo is done. An accepted one moves into AGENTS.md, a hook or a make target. | #, proposal, evidence, status |
| `UPSTREAM_ISSUES.md` | Behaviour of external tools the repo works around. Filing upstream needs the person's yes. | #, upstream, behaviour, workaround, report |

A repo that already has its own channel for one of these (an issue tracker, a loop's own
change requests) keeps it and triages it into `FINDINGS.md`.

An `AGENT_IMPROVEMENTS.md` row that recurs in several repos is proposed to the harness repo
rather than fixed per repo; its `repo-conformance` hook warns on rows older than 14 days.

### `docs/ARCHITECTURE.md`

One section per decision. A changed decision gets a new section naming the one it
replaces; the old one stays.

```markdown
### <n>. <the decision, as a statement>

**Decision.** What is done, naming the files that do it.
**Why.** The reason, with the evidence.
**Rejected.** The alternatives, and why each lost.
```

### `docs/BACKLOG.md`

Only what the person has picked, in order: item, where it came from (a finding id), the
date it was picked. Done items leave with their commit; the changelog records them.

### Adopting this in an existing repo

1. Create the ledgers that have content, filled from git history, TODO files and open
   change requests.
2. Write `docs/ARCHITECTURE.md` from commit messages and plans.
3. Add "How a change moves" and "Where each fact lives" to AGENTS.md; move open items out
   of AGENTS.md into `FINDINGS.md`.

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

### AGENTS.md is the single source of truth

`CLAUDE.md` and `GEMINI.md` are two-line pointers to it, holding no content of their own.
Never write an instruction into more than one of the three.

Two parts for two readers: **§A — using this** (the runbook for setting it up for somebody:
questions first, cheapest run next) and **§B — changing the code**, opening with "How a change
moves" (`change.md`), ending with **Things that will bite you** and a **Definition of done**.

### README

1. `<picture>` with `docs/assets/banner-{dark,light}.svg`; `alt` says what the thing does.
2. Badges (CI, licence, Python, uv, Ruff, mypy, pre-commit, gitleaks), flat `0E0E10`.
3. One bold sentence, in the user's words rather than the architecture's.
4. **Start here**, handing the reader to `AGENTS.md`.

The banner, the architecture picture (what runs where, updated in the same pull request as
what it shows), the README hero graph, mermaid diagrams with their `%%{init}%%` theme line,
HTML reports, dashboards and one-pagers follow the `house-style` skill.

### Makefile is the interface

Every target carries a `## comment` and `help` prints them. `make setup` installs, `make
hooks` installs git hooks, and **`make check` runs exactly what CI runs** — a green `check`
means a green pipeline. Nobody should need the underlying commands.

### Pre-commit

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

### Also at the root

`LICENSE` (Apache-2.0) with `NOTICE`, `CHANGELOG.md`, `.editorconfig`, `.python-version`,
`.env.example` listing every variable with no values, a committed `uv.lock`.

## Secrets — team conventions

The part of upstream's `common/security.md` that holds in every repo here; the lean profile
installs this instead of `common/`. GCP specifics are in `gcp.md`.

- Never write a secret into code, a config file, a notebook, a commit message or a log:
  no API key, token, password, private key or full signed URL.
- Secrets come from the environment or a secret manager (Secret Manager on GCP, the
  Keychain on a Mac), read at runtime. A program checks at start that the ones it needs
  are there and fails with a message naming the missing one, never its value.
- `.env` files stay untracked; `.env.example` lists every variable with no values.
- A secret that was printed, committed or pasted anywhere shared is exposed: say so,
  rotate it, then remove it. Removing it alone does not help.
- Before a commit, look at the staged diff for anything that looks like a secret.
  gitleaks and detect-secrets catch most; they are not a reason to stop looking.
- A public repository names no private repository, links to none, and records no choice
  made about one (licensing, plans, who uses it). Describe it generically: "a separate
  package pinned to this library". Unsure of a repo's visibility? Check with
  `gh repo view --json visibility` before writing.

## Working with the person

Extends ECC's `common/` rules with what people on this team corrected agents for most.

### Options or one answer

- **A matter of taste** (colour, wording, naming, layout): offer two to four lettered
  options with concrete values (hex codes, the exact wording) and change nothing until
  one is picked. "Make a suggestion" asks for options, not for an edit.
- **A how-to question**: give the one path you recommend and its steps. Add at most one
  alternative, and only when it changes the outcome. A survey of every way confuses.

### A decision stays decided

When the person decides something, write it to where it lasts in the same turn: the
ledger row, the commit message, the brief or memory. Never ask it again, also not after
the conversation was summarized. Read the summary's list of decisions before asking.

### Say where the work happens

- Before moving or renaming a repository or project folder, say so and wait. A shell or
  session open inside it breaks with `getcwd` errors.
- A session that works in a worktree or a copy names that path in its first reply, and
  says when the work moves back.
- A clone or worktree goes beside the main checkout, never in `/tmp` or a scratchpad.
  Credentials can be chosen by the folder git runs in, so a push from elsewhere fails.
- One working session per repository unless the person starts another. Open work goes
  into the repo, not only into chat.

### Batches, reviews and asks

- A job over several items is done in one go: take the usual default for each open
  question, note it, and list every decision once at the end.
- With several background agents, reply once when all are back; at most one progress
  line while waiting.
- After the person answers a review's questions and says to go ahead, the whole review
  is the work order. List only what was left out, and why.
- An ask for the person's action names the place (the link, the screen, the button) and
  what happens if it is not done.

### Edits and drafts

- A style edit (corners, line width, spacing) applies to every sibling on that frame,
  page or deck, not only the element named.
- When hand-made drafts of a logo or illustration are rejected twice, stop drafting.
  Offer a designer brief or a proper drawing tool.

### Never trace a shell that may hold a token

No `set -x` or `bash -x` around anything that may call gh, git or a cloud CLI: a shell
function wrapping it can read a token, and the trace prints it. Debug with `echo` lines.

### Deliverables stay local

An HTML page, dashboard or report is written to the repo or the scratchpad and opened
with `open`. Never publish it to a hosted service (claude.ai artifacts, a gist, a paste
site) unless the person asks for that service by name. How it looks follows the
`house-style` skill, also in a loop or a brief written for another agent: a reference
file, the starter, variants side by side, and `check_visual.js` exiting 0.

---

Rules that must *block* rather than advise are not here — a skill cannot enforce. Those live in `.pre-commit-config.yaml` in each repo, and in the hooks `make setup-user` wires (`tools/setup-user.py`).
