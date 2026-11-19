---
paths:
  - "**/.agent/**"
  - "**/AGENTS.md"
  - "**/docs/ARCHITECTURE.md"
  - "**/docs/BACKLOG.md"
---
# Ledgers, ARCHITECTURE and BACKLOG — team conventions

## The ledgers in `.agent/`

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

## `docs/ARCHITECTURE.md`

One section per decision. A changed decision gets a new section naming the one it
replaces; the old one stays.

```markdown
## <n>. <the decision, as a statement>

**Decision.** What is done, naming the files that do it.
**Why.** The reason, with the evidence.
**Rejected.** The alternatives, and why each lost.
```

## `docs/BACKLOG.md`

Only what the person has picked, in order: item, where it came from (a finding id), the
date it was picked. Done items leave with their commit; the changelog records them.

## Adopting this in an existing repo

1. Create the ledgers that have content, filled from git history, TODO files and open
   change requests.
2. Write `docs/ARCHITECTURE.md` from commit messages and plans.
3. Add "How a change moves" and "Where each fact lives" to AGENTS.md; move open items out
   of AGENTS.md into `FINDINGS.md`.
