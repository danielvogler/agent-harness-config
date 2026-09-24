# Upstream

What we take from [`affaan-m/ECC`](https://github.com/affaan-m/ECC), how it is pinned, and
every way our install differs from a stock one.

## The pin

| | |
| --- | --- |
| Repo | `affaan-m/ECC` (MIT) |
| Pinned SHA | `e4e4163101f162881e628f300a9ca4e6a940bcea` |
| Commit date | 2026-07-29 (`fix(docs): restore main CI (#2623)`) |
| Pinned on | 2026-07-29 |
| Declared in | [`upstream.json`](upstream.json) — the only place the version appears |

Upstream is a **well-kept reference implementation, not a dependency with guarantees** — 235k stars against 1,222 watchers is a viral thread, not adoption, though the project is genuinely maintained. Treat it accordingly.

**Never track upstream `main`.** It receives daily commits. Bumping the pin is a deliberate
act: change the SHA in `upstream.json`, run `make validate` and `make plan`, read the diff,
then commit. Review monthly; never auto-merge.

### Why we do not fork

ECC's installer resolves module `paths` relative to its own repo root
(`scripts/lib/install-manifests.js`), so its content and ours must sit in one tree *at
install time*. They do not have to sit in one tree *in git*.

`tools/materialize.py` clones ECC at the pinned SHA into `.ecc/` (gitignored), copies
`custom/` into it, and patches its manifests from `overlay/manifest-overlay.json`. The result
is byte-for-byte what a fork would have produced — verified against an actual merge during the
initial build — while this repo stays ~200 files instead of ~3,400.

The practical payoff: bumping upstream is a one-line SHA edit, never a merge conflict, and
`git log` shows our decisions rather than upstream's release history.

## Deltas against a stock ECC install

Everything here is applied by `overlay/manifest-overlay.json` unless stated otherwise.

### Modules removed (15)

Removed outright, so they cannot be reached even via `--profile full`.

| Modules | Why |
| --- | --- |
| `docs-ja-jp`, `docs-zh-cn`, `docs-ko-kr`, `docs-pt-br`, `docs-ru`, `docs-tr`, `docs-vi-vn`, `docs-zh-tw`, `docs-de-de` | Translation packs, every one marked `heavy` |
| `prediction-market-skills`, `ito-compute`, `supply-chain-domain`, `media-generation`, `social-distribution`, `business-content` | The upstream author's own problem domain, not ours |

Removing them orphans references elsewhere in the manifests, so `materialize.py` also prunes
those ids from `install-profiles.json` (`research`, `full`) and from
`install-components.json`, which drops 15 now-empty components (81 → 66). This was not in the
build instructions; without it our own validation would fail against upstream's schemas.

### MCP servers removed (4)

From `mcp-configs/mcp-servers.json`: **`ito-compute`** (points at an unpublished package from
the upstream author's company) and **`nexus`** (the upstream author's own infrastructure).

Then two more, added 2026-08-29 and worth explaining because they look useful:
**`jira`** and **`confluence`**. Both are shaped for Atlassian **Cloud** — `jira` is
`mcp-atlassian` configured with `JIRA_EMAIL` + `JIRA_API_TOKEN`, and `confluence` is
`confluence-mcp-server`, which supports Cloud only. The instances this targets are
**self-hosted Data Center**, which authenticates with a personal access token, not an email
plus API token. Left in the catalog, these two are a trap: the obvious thing to do with them
is paste a Data Center credential into a server that cannot use it.

### MCP servers added (3)

| id | shape | what it reaches | credentials | blast radius |
| --- | --- | --- | --- | --- |
| `bigquery` | stdio, `npx` | BigQuery in one GCP project | Application Default Credentials | `BIGQUERY_READONLY` and a 1 GB `BIGQUERY_MAXIMUM_BYTES_BILLED` are set **at the server**, not left to the agent. A runaway query errors instead of invoicing. |
| `miro` | remote HTTP, `https://mcp.miro.com/` | Miro boards | OAuth in the browser; nothing stored locally | Every board the authenticating Miro account can see. On a shared team account that is all of them. Miro operates the server, so board content transits their infrastructure — which it already does. |
| `atlassian-agent` | stdio, `uvx` from git | whatever `$JIRA_URL` / `$CONFLUENCE_URL` name; no defaults | Personal access tokens, read from `$JIRA_TOKEN` and `$CONFLUENCE_TOKEN` | Everything your account can read in Jira and Confluence — including other people's tickets, and anything anyone has pasted into a wiki page. 13 tools, 7 marked read-only. Writes are dry runs returning a unified diff until a second call passes `apply=true`, and Confluence updates carry the version that was read, so a page edited in between is refused rather than silently reverted. |

Tool counts and description sizes in this table are measured from each server's own
`tools/list` over a real MCP handshake, not read off a README. `@google-cloud/mcp-toolbox-bigquery`
is why.

`atlassian-agent` is <https://github.com/danielvogler/atlassian_agent> (MIT), owned by this
team. Its `pyproject.toml` declares an `atlassian-agent-mcp` console script, so `uvx` runs it
straight from the git URL — **no clone, no `make setup`, no local checkout**. Verified by
an MCP handshake against a cold `uvx` with nothing on disk and no tokens set: it initialises
and returns all 13 tools (7 annotated `readOnlyHint`, 6 that write). Note the upstream
README's prose says "nine read, four write"; its own tables, and the server itself, say 7
and 6. Missing tokens surface at tool-call time, not at startup — which is deliberate, since
Jira is optional and the Confluence tools work without it.

It is not on PyPI, so the entry pins a **commit SHA** rather than tracking `main` — the same
discipline this repo applies to ECC. Bumping it is a deliberate edit to the overlay.
Publishing to PyPI would let the entry become `uvx atlassian-agent-mcp` with a version range;
worth doing, not required.

The tokens are per-person and must never be committed, so the catalog carries
`YOUR_JIRA_TOKEN_HERE` / `YOUR_CONFLUENCE_TOKEN_HERE` and `mcp-setup.py` fills them from
`$JIRA_TOKEN` and `$CONFLUENCE_TOKEN`.

### `github`, activated 2026-09-15 — upstream's own catalog entry, unchanged

Added to `activateMcpServers.ids`, not to `addMcpServers`: upstream's catalog already
carries a correct `github` entry (`npx -y @modelcontextprotocol/server-github`, official
Anthropic-maintained package), the same situation as `context7` above — nothing to
override, just switch it on. No `removeMcpServers` reason applies either, unlike `jira` and
`confluence`.

| id | shape | what it reaches | credentials | blast radius |
| --- | --- | --- | --- | --- |
| `github` | stdio, `npx` | every repo, issue and PR your token can see | `$GITHUB_PERSONAL_ACCESS_TOKEN`, a personal token — never a team-owned one | Whatever the token's scopes allow: creating, editing and closing issues and PRs, pushing files, merging. A fine-grained token scoped to the repos actually in use is safer than a classic PAT with blanket `repo` scope. |

The env key is `GITHUB_PERSONAL_ACCESS_TOKEN`, not `GITHUB_TOKEN` — upstream's own naming,
kept as-is rather than aliased, so the catalog entry stays byte-identical to upstream's.
Resolution goes through the same generic `env_value()` precedence as every other server
(`mcp-setup.py`, [above](#env-precedence-and-keeping-the-tool-generic)): `$GITHUB_PERSONAL_ACCESS_TOKEN`
in your shell wins, and with nothing set `make mcp` skips the server rather than registering
a broken one.

### The `bigquery` entry pointed at a package that does not exist

Corrected 2026-08-29. The entry ran `npx -y @google-cloud/mcp-toolbox-bigquery@latest`.
**There is no such package** — npm returns 404. `claude mcp add` accepted it, `make mcp`
reported success, and `claude mcp list` showed `Failed to connect — CONNECTION_CLOSED`,
which nobody had looked at. So the BigQuery access this repo documented had never worked,
and the cost-guardrail story attached to it was describing flags on a package that was
never installed.

The real thing is Google's **MCP Toolbox for Databases**: `@toolbox-sdk/server`, pinned,
`--prebuilt bigquery --stdio`. Verified by an MCP handshake — 9 tools, including
`execute_sql`, `get_table_info` and `ask_data_insights`.

The guardrails survive the swap, but they are **environment variables, not flags**:
`BIGQUERY_READONLY=true` and `BIGQUERY_MAXIMUM_BYTES_BILLED=1000000000`. There is no
`--read-only` and no `--max-bytes-billed`; anyone reading the old entry would have
concluded otherwise. `BIGQUERY_PROJECT` now resolves from `$GOOGLE_CLOUD_PROJECT` first
(the name Google's own tools use), then `$GCP_PROJECT`, then the ambient gcloud default —
last, because that is most likely to be someone's unrelated personal project.

One caveat worth carrying: the toolbox logs a warning that prebuilt profiles are intended
for build-time use by trusted developers and are "not secure enough for run time use
cases, where the agent will be talking to potentially untrusted developers". That is what
we are using it for, but it is worth knowing before anyone points it at a public surface.

**The lesson is not about BigQuery.** A catalog entry that names a nonexistent package
fails silently at exactly the place nobody looks. `make doctor` reports which servers are
*configured*, not which ones *connect* — worth closing.

### Env precedence, and keeping the tool generic

`mcp-setup.py` contains **no site-specific string**. One rule applies to every server's
`env` block:

1. `$KEY` from your environment wins, always.
2. Otherwise the catalog value — which is where a team default belongs.
3. Unless that value is still a `YOUR_..._HERE` placeholder, meaning only you can supply
   it. Then it says which variable to export and skips that server rather than
   registering a broken one.

The Atlassian entry has no catalog values at all: both URLs and both tokens are
`personalEnv`, because which instance you use is as personal as your token. Set them in
`.env` and nothing here changes. The same rule
now lets `$GOOGLE_CLOUD_PROJECT` override the BigQuery project, which previously only
followed `gcloud`.

Two conventions this adds to a catalog entry, both ours rather than upstream's:

- **`personalEnv`** — variables only the person running `make mcp` can supply: tokens and
  API keys. They are listed **by name, with no value in the catalog.** A dummy value would
  be one more secret-shaped string in a tracked file, and `detect-secrets` is right to
  refuse those — it cannot tell a placeholder from a pasted credential, and the day it
  guesses wrong is the day a real one lands in git. (This convention exists because the
  hook caught exactly that and the temptation was to add an exclusion.)
- **`optionalEnv`** — keys whose absence is a note rather than a failure. `atlassian-agent`
  serves its Confluence tools with no Jira credentials at all and returns a clear error per
  `jira_*` tool, so demanding `JIRA_TOKEN` would refuse a server that works.
- **`--env-file`** (`make mcp ENV_FILE=...`, default `./.env`) — read tokens from wherever
  they already are instead of copying them. One copy is one thing to rotate and one thing
  to leak. An existing environment variable still wins.

`mcp-setup.py` never prints a credential: `claude mcp add` takes secrets as `--env KEY=value`
on the command line, so every printed command goes through `redact()`, which masks any value
whose key looks like a secret. Terminal output ends up in screenshots and bug reports.

This server speaks to **self-hosted** Jira and Confluence only. `*.atlassian.net` sites
are Cloud; those need the official Atlassian remote server instead. **They do land in `~/.claude.json` in plaintext**,
which is the cost of dropping the checkout — the server's own `.env` was better on that one
axis and worse on every other. `mcp-setup.py` prints `(set)` rather than the value, because
its output gets pasted into chat threads.

### `tools/mcp-setup.py` understands two entry shapes

Upstream's catalog is stdio-only in practice. Miro is a remote server, so `mcp-setup.py` now
also accepts `{"type": "http"|"sse", "url": ...}` and emits
`claude mcp add --transport <type>`. Placeholder resolution was generalised at the same time:
it applies to the command and its arguments, not only to `env` values, and an unresolved
placeholder prints what to do about it and skips that one server rather than failing the run.

### Skills vendored (82)

81 from `ai-skills-library` at `779b98c`, plus `custom-deep-research`, which we ported. None of
the 82 collides with any of ECC's 281 skills or its `.agents/skills/` set — checked, and
enforced on every commit by `make validate`.

`ai-skills-library` has meanwhile grown `profiles/` and its own `scripts/install-*.sh`. That is
worth watching: if it becomes an installer in its own right, it stops being a content source and
starts being a second, competing distribution mechanism — exactly the duplication this repo
exists to remove. See the open question below.

### Modules added (3)

`custom-skills`, `custom-research`, `custom-rules`. See `README.md` for what each provides.

### Profile added (1)

`custom` — upstream's `minimal` plus `workflow-quality` plus our three modules. It is the only
profile anyone here should install.

`hooks-runtime` **is included.** The original build draft excluded it pending an audit, on the
grounds that `hooks/hooks.json` is 37 KB of minified inline `node -e "..."` one-liners. The
audit has now been done and that description, while literally true, overstates the problem:

- There are **21 hook commands across 7 events**, and the ~1 KB of minified code in each is the
  *same* root-resolution bootstrap repeated — it locates the ECC install, then delegates to a
  named, readable script. So it is not 37 KB of obfuscation.
- **Corrected 2026-08-04:** an earlier pass here said "19 scripts". The directory holds **50
  files**; the registry references **21** directly, and two of those are dispatchers
  (`pre-bash-dispatcher.js`, `posttooluse-dispatcher.js`) that fan out to more — which is why
  `block-no-verify.js` never appears in the registry. Some scripts, such as
  `insaits-security-monitor.py`, are on disk and wired to nothing. The reviewable surface is
  larger than the original audit claimed, though the conclusions below still hold.
- **No telemetry.** No matches for posthog, segment, sentry, amplitude or mixpanel anywhere in
  the hook scripts.
- **One hook can reach the network**: `mcp-health-check.js`, and only to health-check the MCP
  server URLs already in your own config. Every other `https://` in those files is a
  documentation link in a comment.
- There are runtime controls: `ECC_HOOK_PROFILE=minimal|standard|strict` (default `standard`)
  and `ECC_DISABLED_HOOKS=id,id`. Individual hooks can be switched off without reinstalling.

Hooks reach **Claude, Cursor and opencode only** — `hooks-runtime` declares no Codex or
Antigravity target, and cannot, since neither has a hook system. Anything that must hold
everywhere still has to be a skill.

## Known issues, carried deliberately

### `rules/common/` is TypeScript-biased

Upstream's shared rules assume TypeScript idioms — `rules/common/coding-style.md` opens with
*"Immutability (CRITICAL): ALWAYS create new objects, NEVER mutate"*, which is not how we write
Python. **Left in place for now.** It needs a Python/GCP pass, and that is a deliberate team
task, not a side effect of the initial build. Until then, `custom/rules/` is where our own
conventions go, and they load alongside upstream's.

### Upstream's Python rules point at two skills we do not install

`rules/python/*.md` refers the reader to `python-patterns` and `python-testing`. **Neither
is installed here** — both ship inside the 69-skill `framework-language` module, which we
do not take. The references are dead ends in our install, so `custom/rules/python.md` has
to carry that content itself rather than delegating to a skill that will never load.

### `deep-research` is two different skills — resolved by renaming ours

`/agent-frameworks` opens with *"Load the `deep-research` skill"*, and both candidate skills
carry that name while doing unrelated things:

| | Upstream ECC's `deep-research` | `ohmyopenagent-runner`'s `deep-research` |
| --- | --- | --- |
| What it is | An MCP wrapper around firecrawl and exa | The pipeline methodology itself |
| Defines | Search-and-cite behaviour, MCP tool usage | Three-phase pipeline, folder layout, save-with-fallback chain, source-count gate, anti-hallucination guardrails, final self-review |
| Module | `research-apis` (not in our profile) | n/a — lives in the source repo |

The command cites the second contract by name, item for item. Adding `research-apis` to the
profile would therefore have satisfied the *word* `deep-research` while leaving the command
broken, since ECC's skill defines none of those things.

**Resolution:** ported the source repo's skill to `custom/skills/custom-deep-research/` and
pointed the command at it. The `custom-` prefix is exactly the reserved namespace
the original build draft called for, and it is what keeps both skills installable side by side —
`make validate` fails the build on any such collision.

The port is minimal. Command: dropped the leading `ultrawork:` line, and changed one skill name.
Skill: changed `name:`, and updated the one sentence telling future command authors what to
reference. Nothing else differs from source.

`ultrawork` is an [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) keyword. It
is undefined in the source repo, absent from ECC, and meaningless in all five target harnesses,
where it would have been a stray token at the head of the prompt.

### Hooks are installed but not wired — they do nothing

**Found 2026-07-30. This is the most consequential issue on this page.**

`hooks-runtime` installs a resolved registry to `~/.claude/hooks/hooks.json` — 21 matchers
across 7 events — and upstream's `hooks/README.md` presents that as the end of the job.
It is not. Per the [Claude Code hooks
documentation](https://code.claude.com/docs/en/hooks), hooks are only active when declared
under a `"hooks"` key in a settings file (`~/.claude/settings.json`,
`.claude/settings.json`, `.claude/settings.local.json`), in managed policy settings, or in
`hooks/hooks.json` **inside an enabled plugin directory**. Claude Code does not read
`~/.claude/hooks/hooks.json`.

`~/.claude` is not a plugin directory (plugins live under `~/.claude/plugins/<name>/`), and
the installer never touches `settings.json`. So on a stock install of this repo, **every
hook is inert**, while `README.md` advertises 21 of them and `AGENTS.md` builds its
"rules advise, hooks enforce" split on top of them.

`make doctor` now reports this explicitly rather than leaving it as folklore.

Not fixed by the installer, deliberately. The fix means writing a `"hooks"` key into the
user's own `~/.claude/settings.json`, which is outside install-state and therefore outside
what `make uninstall` can reverse. That needs a team decision about whether this repo edits
personal settings at all, and if so via an explicit opt-in with a backup rather than silently
during `make install`.

#### Recommended: wire two, not twenty-one

The value is concentrated. Of the 21 wired matchers, categorised 2026-08-04:

| | Count | |
| --- | --- | --- |
| Real guardrails | **2** | `block-no-verify` (via the bash dispatcher) and `config-protection` |
| JS/TS-only | 2 | `stop-format-typecheck`, `check-console-log` — dead weight for a Python team |
| ECC's own product surface | ~17 | cost tracking, continuous-learning evaluators, a governance event store, plan-canvas session surfacing, desktop notifications, compaction suggestions, MCP health checks |

The last group is not bad code, it is someone else's product telemetry and lifecycle
management, and each one spawns `node` on every matching tool call. So prefer wiring the two
that earn it. Both scripts install to `~/.claude/scripts/hooks/`, a stable path that survives
`make clean`, so this does not depend on `.ecc/` existing:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "node ~/.claude/scripts/hooks/block-no-verify.js" }]
      },
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [{ "type": "command", "command": "node ~/.claude/scripts/hooks/config-protection.js" }]
      }
    ]
  }
}
```

Why these two. `block-no-verify` exits 2 on `git commit --no-verify` and on
`-c core.hooksPath=`, which makes it the one hook that protects `.pre-commit-config.yaml` —
without it an agent can route around every check in a repo with one flag. `config-protection`
blocks edits to linter and formatter config, which stops the failure mode where an agent
"fixes" a lint error by loosening the rule.

Verified standalone before recommending:

```bash
echo '{"tool_input":{"command":"git commit --no-verify -m x"}}' \
  | node ~/.claude/scripts/hooks/block-no-verify.js
# exit 2, "BLOCKED: --no-verify flag is not allowed with git commit."
```

Both scripts are readable at `~/.claude/scripts/hooks/`.

#### Or wire the whole set, if you want to evaluate it

**Not a team default.** 21 hooks firing on every tool call is a real behaviour change and
nobody has run them in anger yet, so do this on one machine and report back — whether the
team adopts hooks should rest on someone's experience, not on upstream shipping them.

```bash
# Your file, and this changes agent behaviour on every call. Back it up.
cp ~/.claude/settings.json ~/.claude/settings.json.bak

python3 - <<'PY'
import json
from pathlib import Path

settings_path = Path.home() / ".claude" / "settings.json"
registry_path = Path.home() / ".claude" / "hooks" / "hooks.json"

settings = json.loads(settings_path.read_text())
registry = json.loads(registry_path.read_text())

if "hooks" in settings:
    raise SystemExit("settings.json already has a hooks key — merge by hand, do not clobber")

settings["hooks"] = registry["hooks"]
settings_path.write_text(json.dumps(settings, indent=2) + "\n")
print(f"wired {sum(len(v) for v in registry['hooks'].values())} matchers")
PY
```

Restart Claude Code and confirm with `/hooks`. To back out, restore the `.bak` or delete the
`"hooks"` key. Individual hooks can be disabled with `ECC_DISABLED_HOOKS=id,id` and the whole
set dialled back with `ECC_HOOK_PROFILE=minimal`, without unwiring anything.

Read one before enabling all 21 — `.ecc/scripts/hooks/block-no-verify.js` is the clearest:
a `PreToolUse` hook on `Bash` that exits `2` on `git commit --no-verify`.

Until it is wired:

- Rules, skills, commands and agents are all genuinely working. Only hooks are affected.
- Anything that must actually **block** currently has to be `.pre-commit-config.yaml` in
  the target repo, not a hook.
- The audit recorded below under "Not adopted" that concluded hooks were safe to enable
  was an audit of what the hooks *do*, not of whether they run.

### AgentShield has no custom-rule mechanism — the templates folder was fiction

`custom/agentshield-templates/` existed on the premise, taken from the build draft, that
AgentShield custom rules are "TOML templates that live in `~/.agentshield/templates/`".
**That is not true.** Checked 2026-08-04: its repo has 275 files, no `templates/` directory,
no custom-rule loader, and its only `.toml` files are its own Codex agent configs. The 102
rules are TypeScript modules compiled into the npm package. Its README documents no
extension point of any kind.

The folder is removed. Writing TOML into it would have produced files that silently never
load — worse than nothing, because the folder implied a security floor that did not exist.

AgentShield remains useful as what it actually is: a scanner you *run*, via `make audit` or
`npx ecc-agentshield scan`. It grades an install A–F across secrets, permissions, hooks, MCP
risk and agent config. If we want rules of our own that actually bite, they belong in
`permissions.deny` or in `.pre-commit-config.yaml`, both of which execute.

### `skills-lock.json` hashes do not verify locally

80 lock entries, 81 vendored skill directories, and `computedHash` matches none of the files under
plain SHA-256 (tried raw, whitespace-normalised, CRLF-normalised, and body-only). The digest is
`npx skills`' own scheme, computed against upstream source content rather than the vendored
copy. Post-install verification of skill integrity therefore needs `npx skills` itself, not a
hand-rolled hash check.

### Local fix to vendored content

`custom/skills/adk-agent-builder/references/advanced-patterns.md` links to
`dynamic-nodes.md` relatively. Upstream links to an absolute `file:///` path on the
author's own disk, which resolves for nobody else. **Report it to `google/adk-python` and drop
the patch once fixed there.**

`custom/skills/custom-deep-research/SKILL.md` gains one paragraph under **Project layout**
instructing the agent to create `research/.gitignore` containing `*` on first invocation. A run
writes tens of megabytes of third-party PDFs into whatever repository it is invoked from, and the
original skill leaves that untracked-but-not-ignored, so every user has to remember to ignore it
themselves. Self-ignoring from inside the output directory is the only fix that holds in every
repo the command reaches. **Push this upstream to `ohmyopenagent-runner` and drop the patch on the
next sync.**

`custom/skills/final-checks/SKILL.md` has no `name` field in its frontmatter — it is the one
hand-authored skill in `ai-skills-library` (hence the 80-vs-81 gap in the lockfile), and without
`name` it does not load. We add `name: final-checks`. Still missing as of `779b98c`, so the fix
had to be re-applied after re-vendoring. **Fix it upstream in `ai-skills-library` and drop this
patch on the next sync.**

## Not adopted

- **`security` module** — mostly domain-specific (`defi-amm-security`, `hipaa-compliance`,
  `laravel-security`, `perl-security`, `springboot-security`). Only `security-review`,
  `security-scan`, `gateguard` and `safety-guard` are general-purpose. Worth noting that every
  upstream agent file carries a "Prompt Defense Baseline" block; that comes along with
  `agents-core` regardless.
- **AgentShield** (`ecc-agentshield`) — a separate npm package with its own release cadence.
  See `custom/agentshield-templates/README.md`.
- **`.claude-plugin/marketplace.json`** — only relevant if we distribute via Claude's plugin
  system. Note the pinning asymmetry if that ever changes: plugin *sources* accept an exact
  `sha`, *marketplace* sources accept only `ref`, so a marketplace must be pinned to a tag we
  control.
