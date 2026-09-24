# custom/rules

Team-authored conventions — the deliberate delta against upstream's generic,
TypeScript-biased `rules/common/`.

## Rules advise. They do not enforce.

Rules are markdown loaded into the agent's context. They shape behaviour; they cannot block
anything. If a convention must actually stop a bad write it belongs in a hook or in
`.pre-commit-config.yaml`; if it must actually *produce* something, in a command.

## Keep them short

Rules are **always-on context** — unlike a skill, whose body loads only when invoked, a rule
is paid for on every session, by every person, in every repo.

**Ceiling: 60 lines per file.** A rule that wants to be longer is a skill wearing the wrong
hat — write it as one and reference it from here.

Scope a rule with `paths:` frontmatter unless it must be in context before a shell command.
`make context` shows what the unscoped ones cost.

## Reach

Rules install to **Claude, Cursor and Antigravity only**. Anything that must hold in every
harness is a skill.

## Adding one

Drop a `<topic>.md` file here and open a PR — `custom-rules` already points at this directory
and is in the `custom` profile, so it installs on the next `make update`. Open the file with a
line saying which upstream file it extends and where it overrides.

## Notes per file

Keep provenance and scoping rationale here. A rule file is loaded as an instruction, so
anything addressed to a maintainer rather than to the agent is paid for and read by nobody.

| File | Note |
|---|---|
| `agents.md` | Covers agents *we ship*; ECC's `common/agents.md` covers orchestrating the ones we run. |
| `git.md` | Unscoped on purpose — writing a commit message is not a file read, so a `paths:` rule would not be loaded at the moment it is needed. ECC's `common/git-workflow.md` already carries the conventional-commit format and type list; this adds only our delta. |
| `gcp.md` | Unscoped on purpose — deciding to delete something, or to upload a dataset, is not a file read. |
| `python.md` | Extends and overrides ECC's `python/coding-style.md`. Both install under `~/.claude/rules/ecc/`, so cross-references resolve there, not in this repo. |
| `repo.md` | Extracted from `sectorradar`, `billwright`, `talanton` and `atlassian_agent` rather than invented. Re-read those before changing it. |
