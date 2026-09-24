# Changelog

Notable changes to the shared config, written when a version is tagged. Tags are what
colleagues pin.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is date-driven rather than semantic — this is a configuration bundle, not a
library with an API.

## [Unreleased]

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
