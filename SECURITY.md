# Security

## Reporting

Report a vulnerability privately through
[GitHub security advisories](https://github.com/danielvogler/agent-harness-config/security/advisories/new).
Do not open a public issue for anything exploitable, or for a token, key or internal value
that reached a commit.

If a secret reaches a pushed commit, deleting it in a later commit leaves it in the history.
Rotate it first, then report it.

## Why this repository matters

Whatever merges here reaches every member's machine on their next `make update`: rules and
skills every agent reads, commands it runs, hooks that fire on every tool call, and MCP
servers that hold personal tokens. A bad change here is a supply-chain problem for the whole
team, not a bug in one project.

## What it is careful about

- **Upstream is pinned, never followed.** ECC is cloned at the SHA in `upstream.json`. A
  bump is a reviewed commit (`make bump` shows the diff first), so nothing upstream
  publishes reaches anyone without a person reading it.
- **Vendored skills are recorded.** The repository and commit they were copied from are in
  `upstream.json`, and each skill's original source and a content hash are in
  `custom/skills/skills-lock.json`. `make validate` fails if a custom skill would shadow an
  upstream one of the same name.
- **No credential lives in the repository.** MCP tokens are listed by name only
  (`personalEnv` in the overlay) and read from the environment or a gitignored `.env` when
  `make mcp` runs. `make mcp` masks credential values in everything it prints.
- **Secrets are blocked at commit time.** `detect-secrets` runs as a pre-commit hook, and a
  second hook refuses any JSON file shaped like a GCP service-account key.
- **Installs are reversible.** `make install` records every file it writes and
  `make uninstall` removes exactly those. `make setup-user` and `make mcp` write to your own
  config, back it up first, and say how to undo.
- **Guards, not just advice.** `make setup-user` adds a deny list to Claude Code (cloud
  deletes, `rm -rf`, `sudo`, reading `.env`, SSH keys and service-account files) and wires
  two hooks: one blocks `git commit --no-verify`, the other stops an agent editing linter
  config to make a failure go away.
- **CI checks every branch** against the pinned upstream, and weekly in case upstream
  removes something the overlay depends on.

## What it cannot protect

- An installed skill or rule is text that an agent follows. Review a vendored skill as you
  would code: it can tell an agent to run commands.
- MCP servers run third-party code with your tokens and network access. `UPSTREAM.md`
  records what each one reaches. Once `make mcp` runs, the tokens sit in plain text in your
  own Claude config.
- Whatever you show a cloud-hosted agent goes to that agent's model provider under its
  terms. Nothing here changes that.
- Rules are advisory. Only hooks, the deny list and pre-commit actually block anything.
