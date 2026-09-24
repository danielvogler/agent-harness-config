#!/usr/bin/env python3
"""Activate the team's agreed MCP servers.

Installing ECC's MCP catalog activates nothing: `mcp-configs/mcp-servers.json` is a menu,
and Claude Code reads live servers from elsewhere. So without this, a catalog entry is only
a bookmark and everyone still runs `claude mcp add` by hand — which is where the flags that
matter get forgotten. `--max-bytes-billed` is not a detail you want depending on whether
someone read the README.

This resolves `activateMcpServers.ids` from the overlay against the merged catalog and runs
`claude mcp add` for each, so the agreed spec — same package, same flags, same scope — is
one command instead of a copy-paste.

Deliberately NOT part of `make install`:

  - It writes to your own Claude config, which is outside install-state and therefore
    outside what `make uninstall` can reverse. Undo is `claude mcp remove <id>`.
  - A server means credentials plus network egress plus third-party code running against
    team data. That should be a decision someone makes, not a side effect of installing.

Two shapes of catalog entry are understood:

  - stdio  — {"command": ..., "args": [...], "env": {...}}, run as a local process;
  - remote — {"type": "http"|"sse", "url": ...}, a server someone else operates, which
             authenticates in the browser rather than from a token in a file.

Idempotent: servers already present are reported and skipped, never re-added or clobbered.
Removing and re-adding is a decision someone makes, same reasoning as installing a server
in the first place — so a server whose environment now has keys that would resolve but
aren't part of the current registration (e.g. JIRA_TOKEN exported after a Confluence-only
`make mcp`) gets a `[note]` with the exact fix, not a silent, automatic reconfigure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / ".ecc" / "mcp-configs" / "mcp-servers.json"
OVERLAY = REPO / "overlay" / "manifest-overlay.json"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


SECRET_KEY = re.compile(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|_KEY$|APIKEY|API_KEY")


def redact(cmd: list[str]) -> str:
    """The command as a printable string, with credential values masked.

    Everything this script prints ends up somewhere it should not: a terminal someone
    screenshots, a bug report, a chat thread. `claude mcp add` takes secrets as
    `--env KEY=value` on the command line, so printing the command verbatim leaks them.
    Never print a command any other way.
    """
    out = []
    for part in cmd:
        key, sep, _ = part.partition("=")
        out.append(f"{key}=***" if sep and SECRET_KEY.search(key.upper()) else part)
    return " ".join(out)


def load_env_file(path: Path) -> int:
    """Read KEY=VALUE lines into the environment. Returns how many keys it set.

    Tokens already live somewhere on most machines — the atlassian_agent checkout keeps
    them in its own .env. Reading from there beats copying them into a second file: one
    copy is one thing to rotate and one thing to leak.

    An existing environment variable always wins, matching dotenv everywhere else. Values
    are never printed.
    """
    count = 0
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value or os.environ.get(key):
            continue
        os.environ[key] = value
        count += 1
    return count


def gcloud_project() -> str | None:
    """The project to fill a placeholder with.

    $GOOGLE_CLOUD_PROJECT first (the name Google's own tools use), then $GCP_PROJECT, then
    whatever gcloud is pointed at. The ambient gcloud default is last because it is the
    one most likely to be someone's unrelated personal project.
    """
    explicit = (
        os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
        or os.environ.get("GCP_PROJECT", "").strip()
    )
    if explicit:
        return explicit
    if not shutil.which("gcloud"):
        return None
    out = run(["gcloud", "config", "get-value", "project"])
    value = out.stdout.strip()
    return value if value and value != "(unset)" else None


PLACEHOLDER = re.compile(r"^YOUR_[A-Z0-9_]+_HERE$")


def resolvers() -> dict[str, str | None]:
    """Placeholders this script knows how to work out on its own.

    Only for values that come from a tool rather than from the person — everything else
    is an environment variable, handled generically by `env_value` below. Keep this map
    small: a placeholder resolved by magic is one nobody can predict.
    """
    return {"YOUR_GCP_PROJECT_HERE": gcloud_project()}


HOWTO = {
    "YOUR_GCP_PROJECT_HERE": "run `gcloud config set project <id>`, or `make mcp GCP_PROJECT=<id>`",
    "CONFLUENCE_URL": "set CONFLUENCE_URL to your Confluence base URL in .env",
    "CONFLUENCE_TOKEN": "create a personal access token in your Confluence profile, then set CONFLUENCE_TOKEN in .env",
    "JIRA_URL": "set JIRA_URL to your Jira base URL in .env",
    "JIRA_TOKEN": "create a personal access token in your Jira profile, then set JIRA_TOKEN in .env",
    "GITHUB_PERSONAL_ACCESS_TOKEN": "create a token at github.com/settings/tokens (fine-grained, scoped to the repos you use), then export GITHUB_PERSONAL_ACCESS_TOKEN",
}


def env_value(key: str, catalog: str) -> tuple[str | None, str | None]:
    """Resolve one env entry. Returns (value, problem).

    The precedence is deliberate and applies to every server, so nothing about any one
    site is baked into this script:

      1. `$KEY` in your environment always wins. This is how someone at a different
         institution, or with a second instance, overrides a team default without
         editing the overlay.
      2. Otherwise the catalog value, which is where the team's agreed default lives.
      3. Unless that value is still a `YOUR_..._HERE` placeholder, in which case it is
         something only you can supply — a personal token — and we say so and skip the
         server rather than registering a broken one.
    """
    override = os.environ.get(key, "").strip()
    if override:
        return override, None
    if not PLACEHOLDER.match(catalog):
        return catalog, None
    resolved = resolvers().get(catalog)
    if resolved:
        return resolved, None
    how = HOWTO.get(catalog, f"export {key}=<value>")
    return None, f"{key} is unset and the catalog has only a placeholder — {how}"


def substitute(text: str, values: dict[str, str | None]) -> tuple[str, list[str]]:
    """Replace placeholders outside `env` — a command or an argument."""
    problems: list[str] = []
    for name, value in values.items():
        if name not in text:
            continue
        if value is None:
            problems.append(
                f"{name} could not be resolved — {HOWTO.get(name, 'set it in the overlay')}"
            )
            continue
        text = text.replace(name, value)
    return text, problems


def already_installed() -> set[str]:
    out = run(["claude", "mcp", "list"])
    if out.returncode != 0:
        return set()
    # Output format is not a stable contract, so match ids loosely rather than parsing it.
    return {
        line.split(":")[0].strip()
        for line in out.stdout.splitlines()
        if ":" in line and not line.startswith(" ")
    }


def build_command(
    name: str, spec: dict, values: dict[str, str | None]
) -> tuple[list[str], list[str], list[str], set[str]]:
    """Return (command, problems, notes, resolved_env_keys).

    A non-empty problems list means do not run the command. `resolved_env_keys` is every
    env var name that resolved to a usable value right now — used to spot drift against an
    already-registered server, not just to build a fresh `claude mcp add`.
    """
    problems: list[str] = []
    notes: list[str] = []
    resolved_keys: set[str] = set()
    base = ["claude", "mcp", "add", "--scope", "user"]

    # Remote server: someone else operates it, and it authenticates in the browser.
    # There is no command to run and no token to place, so this is the whole entry.
    transport = spec.get("type")
    if transport:
        if transport not in ("http", "sse"):
            problems.append(f"unknown transport {transport!r} — expected 'http' or 'sse'")
        url = spec.get("url")
        if not url:
            problems.append("remote catalog entry has no url")
            return base, problems, notes, resolved_keys
        url, url_problems = substitute(url, values)
        cmd = base + ["--transport", transport, name, url]
        return cmd, problems + url_problems, notes, resolved_keys

    # stdio server: a local process, and the place where flags and credentials matter.
    cmd = base + [name]
    # Some servers work with only part of their configuration — atlassian-agent serves the
    # Confluence tools with no Jira credentials at all, and says so per tool rather than
    # failing to start. Treating every key as required would refuse a server that works.
    optional = set(spec.get("optionalEnv") or [])

    # personalEnv names variables that only the person running this can supply — tokens and
    # keys. They are listed by NAME ONLY, with no value in the catalog: a dummy value would
    # be one more secret-shaped string in a tracked file, and detect-secrets is right to
    # refuse those. It cannot tell a placeholder from a pasted credential, and the day it
    # guesses wrong is the day a real one lands in git.
    entries = [(k, str(v)) for k, v in (spec.get("env") or {}).items()]
    entries += [(k, "") for k in (spec.get("personalEnv") or [])]

    for key, value in entries:
        resolved = os.environ.get(key, "").strip()
        problem = None
        if not resolved:
            if value:
                resolved, problem = env_value(key, value)
            else:
                problem = f"{key} is unset — {HOWTO.get(key, f'export {key}=<value>')}"
        if not problem:
            cmd += ["--env", f"{key}={resolved}"]
            resolved_keys.add(key)
        elif key in optional:
            notes.append(f"{key} unset — that part of the server will be unavailable")
        else:
            problems.append(problem)

    if not spec.get("command"):
        problems.append("catalog entry has neither a command nor a type/url")
        return cmd, problems, notes, resolved_keys

    argv = [spec["command"], *spec.get("args", [])]
    resolved_argv = []
    for part in argv:
        resolved, argv_problems = substitute(str(part), values)
        problems += argv_problems
        resolved_argv.append(resolved)

    cmd += ["--", *resolved_argv]
    return cmd, problems, notes, resolved_keys


def registered_env_keys(name: str) -> set[str] | None:
    """Env var names currently registered for `name`, or None if that can't be read.

    `claude mcp get` prints an "Environment:" block as `KEY=value` — values in plaintext,
    since this is the person's own local config. Only the names are extracted; a value
    read here must never be printed.
    """
    out = run(["claude", "mcp", "get", name])
    if out.returncode != 0:
        return None
    keys: set[str] = set()
    in_env = False
    for line in out.stdout.splitlines():
        if line.strip() == "Environment:":
            in_env = True
            continue
        if not in_env:
            continue
        stripped = line.strip()
        if not stripped or "=" not in stripped:
            break
        keys.add(stripped.split("=", 1)[0])
    return keys


def drift_note(name: str, resolved_keys: set[str]) -> str | None:
    """A note to print if env vars now resolve that aren't part of the live registration.

    None if there is nothing to resolve (remote servers), the registration can't be read,
    or nothing is missing — the common, silent case.
    """
    if not resolved_keys:
        return None
    registered = registered_env_keys(name)
    if registered is None:
        return None
    missing = sorted(resolved_keys - registered)
    if not missing:
        return None
    keys = ", ".join(missing)
    verb = "resolves" if len(missing) == 1 else "resolve"
    be = "is" if len(missing) == 1 else "are"
    return (
        f"{keys} now {verb} but {be} not part of the "
        f"registered server — run `claude mcp remove {name} -s user` then `make mcp` to "
        "pick it up"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the commands without running them (default is to run)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help=(
            "read KEY=VALUE lines from this file before resolving (default: ./.env if it "
            "exists). Point it at wherever your tokens already live rather than copying "
            "them; an existing environment variable still wins."
        ),
    )
    args = parser.parse_args()

    env_file = args.env_file or (REPO / ".env")
    if env_file.exists():
        n = load_env_file(env_file)
        print(f"read {n} variable(s) from {env_file}")
    elif args.env_file:
        print(f"--env-file {env_file} does not exist", file=sys.stderr)
        return 1

    if not CATALOG.exists():
        print("no materialized catalog — run `make plan` first", file=sys.stderr)
        return 1
    if not shutil.which("claude") and not args.dry_run:
        print("`claude` not on PATH — re-run with --dry-run to see the commands", file=sys.stderr)
        return 1

    catalog = json.loads(CATALOG.read_text())["mcpServers"]
    wanted = json.loads(OVERLAY.read_text()).get("activateMcpServers", {}).get("ids", [])
    if not wanted:
        print("no servers declared in activateMcpServers — nothing to do")
        return 0

    values = resolvers()
    present = set() if args.dry_run else already_installed()
    failures = 0

    for name in wanted:
        spec = catalog.get(name)
        if spec is None:
            print(f"[skip] {name}: not in the catalog (materialize should have caught this)")
            failures += 1
            continue
        cmd, problems, notes, resolved_keys = build_command(name, spec, values)

        if name in present:
            drift = drift_note(name, resolved_keys)
            if drift:
                print(f"[note] {name}: {drift}")
            print(f"[ ok ] {name}: already configured")
            continue

        for note in notes:
            print(f"[note] {name}: {note}")

        if problems:
            print(f"[fail] {name}:")
            for p in problems:
                print(f"         {p}")
            print(f"         would have run: {redact(cmd)}")
            failures += 1
            continue

        if args.dry_run:
            print(f"[dry ] {redact(cmd)}")
            continue

        out = run(cmd)
        if out.returncode == 0:
            print(f"[ add] {name}")
        else:
            print(f"[fail] {name}: {(out.stderr or out.stdout).strip().splitlines()[:1]}")
            failures += 1

    print()
    for placeholder, value in values.items():
        if value:
            print(f"{placeholder} -> {value}")
    print("Check with `claude mcp list`; undo with `claude mcp remove <id>`.")
    if not args.dry_run:
        print("Restart your session for new servers to appear.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
