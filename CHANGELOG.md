# Changelog

Notable changes to the shared config, in words. Tags are what colleagues pin; the
`auto-release` hook makes them from the commits when `main` is pulled, and the next change
here renames `## [Unreleased]` to that tag.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the conventional commits: a `feat` raises the minor version, a `fix` the
patch.

## [Unreleased]

Run `make setup-user` again after `make update`.

- `security.md`: a public repository names no private repository and no choice made
  about one; it describes it generically.
- Rules learned from corrections: `change.md` branches in the checkout the person has
  open (a separate checkout only for a long-running process or when asked), opens a new
  PR for a change after a PR link was given, judges a gate by its exit code and hands
  over the command a permission check refused. `working.md` adds batch jobs with one
  decision list at the end, one reply for many background agents, a review as a work
  order, asks that name the place, one session per repo, clones beside the main
  checkout, style edits across siblings, no third round of hand-made logo drafts and no
  shell trace near a token. `git.md` applies the commit wording rule to PR text and
  acts on sub-issues by URL, not number. `docs.md` drops absolutes and unsourced shares.
- Releases are tagged locally: the `auto-release` post-merge hook tags, pushes and
  releases the next version from the conventional commits when `main` is pulled, and is
  published for other repos. The tag-triggered release workflow is gone.
- New skill `new-repo`: what a new repository gets, in which order, and which rule each
  file follows, so it is written for that repo instead of copied from another. It also
  covers bringing an existing repo up to the structure.
- Repos now reference this repo's hooks by tag instead of copying their patterns, which
  had drifted apart. `.pre-commit-hooks.yaml` publishes `no-ai-attribution`,
  `no-commit-emoji`, `no-service-account-key` and a new `repo-conformance`, which fails on
  empty `.agent/` ledgers, settled rows and unprefixed ids, and warns on
  `AGENT_IMPROVEMENTS.md` rows older than 14 days and on a CLAUDE.md that is more than a
  pointer to AGENTS.md. `repo.md` shows the snippet. The local ids `no-agent-coauthors`,
  `no-emoji-in-commit` and `no-gcp-service-account-keys` are renamed to match; a copied
  `pr-description.yml` runs `no-ai-attribution` now.
- New skill `house-style`: one look for README banners, the architecture picture,
  diagrams and HTML reports, in a neutral palette with one accent per repo. Scripts draw
  the banner and the architecture picture as light and dark SVG pairs and fill a
  single-file HTML report; a repo's own colours come from a committed `.house-style.json`.
  `repo.md` now points at it for the architecture picture and the mermaid theme line.
- The deny rule for `gcloud ... delete` now matches. It was written as
  `Bash(gcloud * delete:*)`, which Claude Code reads as a literal prefix, so deletes were
  never blocked and Claude Code warned on every start. `make setup-user` replaces it with
  `Bash(gcloud * delete*)` and removes the old entry.
- No emoji in commit messages, in any repo. `make setup-user` wires a third guard,
  `block-commit-emoji`, that refuses such a commit, and repos get a matching commit-msg
  hook to copy. As before, `make setup-user` resets Claude Code's hooks to the guards, so
  a tool that adds its own hook (herdr) has to install it again afterwards.
- `git.md`: before the first push an agent runs `git push --dry-run`, and when it is
  refused hands the person the exact command instead of trying other credentials. Commits
  made while iterating are regrouped into one per logical change before the push.
- Opt-in `lean` profile (`make reinstall PROFILE=lean`): the guards, `custom/`, the Python,
  TypeScript and web rules and four agents (code, security and Python review, docs lookup).
  No upstream `rules/common`, commands or workflow-quality skills. On Claude that is 60
  skills instead of 147, 0 commands instead of 95 and 4 agents instead of 68. The default
  profile is unchanged.
- `make mcp SKIP=<id>` leaves an agreed server out on one machine, as `ADD=` adds one.
- New rule `security.md`: the secrets part of upstream's `common/security.md`, so the lean
  profile keeps it.
- New rules `change.md` and `ledgers.md`: how a change moves (a branch in the checkout
  the person has open, rendered output in one named folder, a pull request the person
  merges, then the branch deleted and `main` pulled), where each fact lives, and the `.agent/` ledger,
  `docs/ARCHITECTURE.md` and `docs/BACKLOG.md` formats. They replace a personal copy that
  lived outside this repo.
- New rule `working.md`: lettered options for matters of taste, one recommended path for
  how-to questions, decisions written down so they are never asked again, a warning before
  moving a folder, and deliverables kept local rather than published to a hosted service.
- `docs.md` now also covers HTML and SVG. Every rendered page is looked at before it is
  reported done, and titles are plain statements without the usual machine-written
  patterns.
- New skill `close-session`: answers "can I close this?" from uncommitted and unpushed
  work, open pull requests, worktrees, running jobs, ledgers and decisions held only in the
  conversation.
- `repo.md`: the architecture picture (what runs where) is an SVG pair drawn by a script, in
  zones by place with service marks, status chips and numbered arrows, and changes with the code.

## [v0.2.0] — 2026-10-04

Run `make update`, then `make mcp`. If `make mcp` prints a `[note]` about a stored token,
follow it: remove that server and run `make mcp` again.

- `make mcp` no longer writes tokens into the Claude config. Servers inherit them from the
  shell Claude Code starts in, so a rotated token takes effect on the next start instead
  of being overridden by an expired stored copy. A token found only in `.env` is refused.
- GitHub uses GitHub's own `github-mcp-server` instead of the deprecated npm package, and
  is opt-in: `brew install github-mcp-server && make mcp ADD=github`.
- atlassian-agent 0.4.0, installed from PyPI at a pinned version.
- `make doctor` no longer warns when no MCP server is active; that is a valid choice. It
  does warn about a file dropped from `custom/` that is still installed, and names it.
- Install-state records for files no longer on disk are pruned on every install, so
  `make doctor` stops reporting them forever after a `make reinstall`.

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

[Unreleased]: https://github.com/danielvogler/agent-harness-config/compare/v0.2.0...HEAD
[v0.2.0]: https://github.com/danielvogler/agent-harness-config/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/danielvogler/agent-harness-config/releases/tag/v0.1.0
