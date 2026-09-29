# Changelog

Notable changes to the shared config, written when a version is tagged. Tags are what
colleagues pin.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is date-driven rather than semantic — this is a configuration bundle, not a
library with an API.

## [Unreleased]

- Fixed: a file dropped from `custom/` (a removed command or skill) stayed installed and
  discoverable forever, and `make doctor` reported it as a harmless "stale install-state
  record ignored" even while it was still on disk. `make doctor` now warns and names the
  file instead. Separately, `make reinstall` removed such a file but never cleared its
  bookkeeping record, because uninstall keeps the whole install-state file whenever
  anything was retained (it always retains `settings.json`, which `setup-user.py` edits
  on purpose) — so the same stale record kept being reported forever after. `make
  setup-user` now prunes any install-state record whose destination file is confirmed
  gone, right after its own edits, on every install/update/reinstall. See UPSTREAM.md,
  "Uninstall never fully clears install-state, so dropped files stay reported forever".

## [v0.1.0] — 2026-09-25

First public release.

- One `make install` puts skills, rules, commands, agents and hooks into Claude Code, Codex
  and opencode at user scope, and into Cursor and Antigravity per project. ECC is pinned to
  one commit and patched by `overlay/`, never forked.
- `make setup-user` turns on the permission lists, the two guard hooks and the team
  conventions for Codex and opencode. `make mcp` connects context7, BigQuery, Miro,
  self-hosted Jira and Confluence, and GitHub.
- No instance-specific value lives in a rule or skill: GCP reads the active gcloud
  configuration, everything else comes from environment variables.
- `make doctor`, `make context`, `make check` (everything CI runs) and a GitHub release for
  every `v*` tag.
- Vendored skills ship with their licenses in `THIRD_PARTY_LICENSES/`.

[Unreleased]: https://github.com/danielvogler/agent-harness-config/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/danielvogler/agent-harness-config/releases/tag/v0.1.0
