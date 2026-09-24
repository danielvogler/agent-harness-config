# overlay/

**Our delta to upstream ECC's own config files, expressed as a patch.** One file does the
work: `manifest-overlay.json`.

There is no `mcp/` folder because the folder is named for the mechanism, not a subject.
Upstream keeps its install behaviour in four files, and this is the single diff against all
four:

| Upstream file | What we change |
| --- | --- |
| `manifests/install-modules.json` | remove 15 modules, add our 3 |
| `manifests/install-profiles.json` | add the `custom` profile, prune dead references |
| `manifests/install-components.json` | prune references to removed modules |
| `mcp-configs/mcp-servers.json` | remove 2 servers, add ours |

## Why a patch and not a fork

Upstream takes daily commits. Edited copies of those four files would make every pin bump a
four-way merge in files we do not own. As a patch, bumping the pin stays a one-line SHA edit.
`materialize.py` applies it to a freshly checked-out pristine tree every time, never to the
previous run's output.

It fails loudly: removing a module upstream has deleted is a hard error, and adding a module
or server id that already exists upstream is refused rather than silently shadowing it.

## The five keys

`removeModules`, `removeMcpServers`, `addMcpServers`, `addModules`, `addProfiles`.

Keys beginning with `$` are ours and are stripped before writing — upstream's schema sets
`additionalProperties: false`. `$source` is the interesting one: `materialize.py` generates
each module's real `paths` array from it at build time, which is why `paths` is `[]` here.

## MCP servers: the catalog is not an activation

`mcp-configs/mcp-servers.json` installs to `~/.claude/mcp-configs/` and **nothing reads it as
configuration.** It is a catalog — 34 servers with package names, arguments and env
placeholders already worked out. Claude Code reads *active* servers from `~/.claude.json`, a
project `.mcp.json`, or whatever `claude mcp add` writes. On a fresh install none are running.

That is the right default: a server means credentials plus network egress plus a third party's
code running against team data, so `make install` should not switch it on for five people.

A server is a subprocess — the harness launches it, talks JSON-RPC over stdio, and its tools
appear to the agent as `mcp__<name>__*`. Not a library your code imports, not a deployed
service; it lives and dies with the session and only the agent calls it.

### Turning them on

`activateMcpServers.ids` in the overlay is the single list of what the team runs, resolved
from the merged catalog. Ids are validated at materialize time, so a typo fails the build
rather than silently activating nothing.

```bash
make mcp                                  # uses your ambient gcloud project
make mcp GCP_PROJECT=my-project           # or name it explicitly
python3 tools/mcp-setup.py --dry-run      # see the commands without running them
```

Not part of `make install`: it writes to your own Claude config, outside install-state and so
outside what `make uninstall` reverses. Undo with `claude mcp remove <id>`.

The equivalent by hand, per person, once — both read-only:

```bash
# Live library docs. Already in upstream's catalog, so no entry here. Also activates the
# docs-lookup agent, which agents-core ships and which is inert without it.
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp@latest

# Read-only BigQuery. ADC, never a key file — see custom/rules/gcp.md.
gcloud auth application-default login
claude mcp add --scope user bigquery \
  --env GOOGLE_CLOUD_PROJECT=your-project-here \
  -- npx -y @google-cloud/mcp-toolbox-bigquery@latest \
     --read-only --max-bytes-billed 1000000000
```

`claude mcp list` to check, `claude mcp remove <name>` to undo. `--read-only` and
`--max-bytes-billed` are set at the server, not left to the agent: `gcp.md` asks for both,
but a rule only advises. 1 GB is roughly USD 0.005 per query.

> The BigQuery package name is **not** verified against npm. Confirm it resolves, and prefer
> Google's own MCP Toolbox over a community server for anything holding credentials. The
> rejected candidates and the reasoning are recorded in the working notes.

### Testing the BigQuery server

Three layers, cheapest first — each one rules out a different failure.

```bash
# 1. Does the package exist and start? (this is the unverified part)
npx -y @google-cloud/mcp-toolbox-bigquery@latest --help

# 2. Do your credentials work at all, independently of MCP?
gcloud auth application-default login
bq --project_id=YOUR_PROJECT ls                       # datasets exist
bq --project_id=YOUR_PROJECT query --dry_run --use_legacy_sql=false \
   'SELECT 1'                                          # ADC can plan a query

# 3. Is the server registered and reachable?
make mcp
claude mcp list                                        # should show bigquery
```

Then in a fresh session, ask for something only the server can answer — "list the datasets in
this project", or "what columns does <table> have". If it answers, it worked. If it offers to
write you a `bq` command instead, the server is not connected: check `claude mcp list`, and
that you restarted the session.

Worth doing once, deliberately: ask it to run a query over a large table and confirm it
**fails on the byte cap** rather than running. That is the guardrail you are relying on, and
an untested guardrail is one everyone assumes works. Also try asking it to delete or write —
`--read-only` should refuse.

If step 1 fails, the package name is wrong. Prefer Google's own MCP Toolbox for Databases and
update `addMcpServers` accordingly; do not substitute a community server for something holding
data credentials without saying so in `UPSTREAM.md`.

## Adding to it

Edit `manifest-overlay.json`, then `make validate && make plan` and read the diff. New
modules: see `AGENTS.md`. New MCP server: record in `UPSTREAM.md` what it reaches, which
credentials it needs, who owns them, and the blast radius if compromised.
