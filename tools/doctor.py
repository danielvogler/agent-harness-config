#!/usr/bin/env python3
"""Report drift between this checkout and what is actually installed.

The failure mode this exists for is silent staleness. `make install` writes into
`~`, so there is no directory to look at and nothing tells you your config is
three weeks behind the team's. People then hit behaviour nobody else can
reproduce, and the first question — "are you on the current config?" — has no
easy answer. This makes it one command.

Four checks, cheapest first:

  1. Pin drift      — the upstream SHA recorded in each install-state versus the
                      SHA in upstream.json. Differ means `make update`.
  2. Content drift  — whether custom/, overlay/ or the pin have been touched
                      since the last install. This is the one that fires most
                      often in practice: you add a skill and forget to reinstall.
  3. Repo staleness — how far behind origin/main this checkout is, plus which
                      release tag you are on.
  4. File drift     — delegated to upstream's own `scripts/doctor.js`, which
                      compares every managed file against its source.

Locating install-state files is delegated to upstream's doctor too, so the paths
live in one place (upstream's adapters) rather than being hardcoded here and
going stale the next time ECC adds a target.

Exits 0 even when it finds problems — the report is the point, and a non-zero
exit here would just print `make: *** [doctor] Error 1` over the advice. Pass
--strict to exit 1 on anything actionable, for CI or a wrapper script.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ECC = REPO / ".ecc"

# Watched for content drift. A change to any of these means the installed fan-out
# no longer matches this checkout.
WATCHED = ("custom", "overlay", "upstream.json")

# Fallback only. The real list comes from upstream's doctor; this keeps `doctor`
# useful before `.ecc/` has ever been materialized.
KNOWN_STATE_PATHS = (
    Path.home() / ".claude" / "ecc" / "install-state.json",
    Path.home() / ".codex" / "ecc-install-state.json",
    Path.home() / ".config" / "opencode" / "ecc-install-state.json",
    Path.home() / ".opencode" / "ecc-install-state.json",
)

# setup-user.py rewrites these after every install on purpose: it replaces the hook block
# ECC writes into ~/.claude/settings.json and appends the team conventions to each
# AGENTS.md. Upstream's doctor sees its managed copy changed and reports it, which is
# only drift if setup-user has not been applied. Matched by name, so opencode's old and
# new config directories are both covered.
SETUP_USER_FILES = ("settings.json", "AGENTS.md")
SETUP_USER_CODES = ("missing-managed-files", "drifted-managed-files")

# Upstream's install-state carries records forward from earlier installs even when the
# current plan no longer contains them, so a file dropped upstream is reported missing
# or drifted forever and no reinstall clears it. A path the installer would not write at
# this pin is such a record, not drift. `make` installs with this profile.
STALE_CODES = ("missing-managed-files", "drifted-managed-files", "missing-source-files")
PROFILE = "custom"

OK, WARN, ERR = "ok", "warning", "error"
LABEL = {OK: "  ok  ", WARN: " warn ", ERR: " fail "}

findings: list[tuple[str, str, str]] = []  # (status, headline, advice)


def note(status: str, headline: str, advice: str = "") -> None:
    findings.append((status, headline, advice))


def git(*args: str) -> str | None:
    """Run a git command in this repo, returning None on any failure.

    Every caller here is diagnostic, so a missing ref or absent remote is a
    reason to skip a check, never a reason to crash the report.
    """
    try:
        out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def newest_mtime(paths: tuple[str, ...]) -> tuple[float, Path | None]:
    """Most recent mtime across the watched paths, and which file it was."""
    newest, where = 0.0, None
    for name in paths:
        target = REPO / name
        if not target.exists():
            continue
        candidates = [target] if target.is_file() else target.rglob("*")
        for entry in candidates:
            if entry.is_dir() or entry.name == ".DS_Store":
                continue
            mtime = entry.stat().st_mtime
            if mtime > newest:
                newest, where = mtime, entry
    return newest, where


def upstream_doctor() -> dict | None:
    """Upstream's file-level drift report, or None if it cannot run."""
    script = ECC / "scripts" / "doctor.js"
    if not script.exists():
        return None
    try:
        out = subprocess.run(
            ["node", str(script), "--json"],
            cwd=ECC,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 and not out.stdout.strip():
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def state_paths(report: dict | None) -> list[Path]:
    if report:
        found = [Path(r["installStatePath"]) for r in report.get("results", [])]
        if found:
            return found
    return [p for p in KNOWN_STATE_PATHS if p.exists()]


def setup_user_applied() -> bool:
    """True when setup-user.py would change nothing, so its edits are all in place."""
    try:
        out = subprocess.run(
            [sys.executable, str(REPO / "tools" / "setup-user.py"), "--check"],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def planned_paths(target: str) -> set[str] | None:
    """Every source and destination the installer would touch for one target, or None."""
    script = ECC / "install.sh"
    if not script.exists():
        return None
    cmd = [str(script), "--profile", PROFILE, "--enable-hooks", "--target", target]
    try:
        out = subprocess.run(
            [*cmd, "--dry-run", "--json"], cwd=ECC, capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        operations = json.loads(out.stdout)["plan"]["plannedOperations"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    paths: set[str] = set()
    for op in operations:
        paths.update(op[key] for key in ("sourcePath", "destinationPath") if op.get(key))
    return paths


def legacy_opencode_state() -> Path:
    return Path.home() / ".opencode" / "ecc-install-state.json"


def drop_legacy_opencode(states: list[tuple[Path, dict]]) -> list[tuple[Path, dict]]:
    """Ignore a pre-2.2 opencode install-state when a current one exists beside it.

    ECC 2.2 moved opencode to ~/.config/opencode but leaves the old state file behind.
    Read next to the current one, it reports an old pin and old content that no
    `make update` can clear, because update never writes to ~/.opencode.
    """
    legacy = legacy_opencode_state()
    opencode = [path for path, st in states if st.get("target", {}).get("id") == "opencode-home"]
    if legacy not in opencode or len(opencode) < 2:
        return states
    note(
        WARN,
        "opencode-home: a leftover install-state in ~/.opencode is ignored",
        "move ~/.opencode/ecc-install-state.json aside; the current install is elsewhere",
    )
    return [(path, st) for path, st in states if path != legacy]


def check_pin(states: list[tuple[Path, dict]], pinned: str) -> None:
    for path, state in states:
        target = state.get("target", {}).get("id", path.name)
        installed = state.get("source", {}).get("repoCommit")
        if not installed:
            note(WARN, f"{target}: install-state records no upstream commit")
        elif installed != pinned:
            note(
                ERR,
                f"{target}: installed upstream {installed[:8]}, pin says {pinned[:8]}",
                "run `make update`",
            )
        else:
            note(OK, f"{target}: upstream {installed[:8]} matches the pin")

        profile = state.get("request", {}).get("profile")
        if profile and profile != "custom":
            note(
                WARN,
                f"{target}: installed with profile {profile!r}, not 'custom'",
                "reinstall with `make install` unless this was deliberate",
            )


def check_content(states: list[tuple[Path, dict]]) -> None:
    mtime, where = newest_mtime(WATCHED)
    if not where:
        return
    changed = datetime.fromtimestamp(mtime, tz=UTC)

    for path, state in states:
        target = state.get("target", {}).get("id", path.name)
        stamp = state.get("installedAt")
        if not stamp:
            continue
        try:
            installed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if changed > installed:
            rel = where.relative_to(REPO)
            note(
                ERR,
                f"{target}: {rel} changed after the last install",
                "run `make update` — your edits are not installed yet",
            )
        else:
            age = (datetime.now(tz=UTC) - installed).days
            note(OK, f"{target}: installed {age}d ago, newer than any local change")


def check_repo() -> None:
    if git("rev-parse", "--git-dir") is None:
        note(WARN, "not a git checkout — cannot check staleness")
        return

    if git("status", "--porcelain"):
        note(WARN, "working tree has uncommitted changes")

    describe = git("describe", "--tags", "--always")
    tag = git("describe", "--tags", "--abbrev=0")
    if tag:
        note(OK, f"release: {describe} (nearest tag {tag})")
    else:
        note(
            WARN,
            "no release tags in this checkout",
            "tag a known-good config so colleagues can pin one",
        )

    counts = git("rev-list", "--left-right", "--count", "HEAD...origin/main")
    if counts is None:
        note(
            WARN,
            "no origin/main ref — cannot tell whether this checkout is current",
            "run `git fetch origin`",
        )
        return
    try:
        ahead, behind = (int(n) for n in counts.split())
    except ValueError:
        return
    if behind:
        note(
            ERR,
            f"{behind} commit(s) behind origin/main",
            "run `make update`",
        )
    elif ahead:
        note(OK, f"up to date with origin/main ({ahead} local commit(s) ahead)")
    else:
        note(OK, "up to date with origin/main")

    # A stale fetch makes the comparison above meaningless, so say so.
    fetched = git("log", "-1", "--format=%cr", "origin/main")
    if fetched:
        note(OK, f"origin/main last fetched commit dated {fetched}")


def check_hooks(states: list[tuple[Path, dict]]) -> None:
    """Are the installed hooks actually wired up, or just sitting on disk?

    Claude Code does not read ~/.claude/hooks/hooks.json. Hooks are only active
    when declared under a "hooks" key in a settings file, or when they ship inside
    an enabled plugin directory. ECC's installer writes the resolved registry to
    ~/.claude/hooks/hooks.json and stops there, so a stock install leaves every
    hook inert while both the installer and our own README claim otherwise.

    This is worth a loud check rather than a footnote: the whole "rules advise,
    hooks enforce" split in AGENTS.md depends on the enforcing half existing.
    """
    for _, state in states:
        target = state.get("target", {})
        if target.get("target") != "claude":
            continue

        root = Path(target.get("root", Path.home() / ".claude"))
        wired = hooks_wired(root)
        registry = root / "hooks" / "hooks.json"

        if wired:
            note(OK, f"{target.get('id')}: hooks wired into settings")
        elif not registry.exists():
            # From ECC 2.2 the installer registers hooks in settings.json and no longer
            # ships hooks/hooks.json, so an absent registry says nothing. Settings do.
            note(
                WARN,
                f"{target.get('id')}: no hooks declared in settings",
                "run `make setup-user` to turn on the two guards",
            )
        else:
            events = (load_json(registry) or {}).get("hooks", {})
            count = sum(len(v) for v in events.values() if isinstance(v, list))
            note(
                ERR,
                f"{target.get('id')}: {count} hook matcher(s) installed but INERT",
                "nothing reads hooks/hooks.json. Rules, skills and commands all work; "
                "nothing is being enforced. Diagnosis and opt-in wiring: UPSTREAM.md, "
                "'Hooks are installed but not wired'.",
            )


def hooks_wired(root: Path) -> bool:
    """True when a settings file declares hooks, or a plugin directory would load them."""
    for name in ("settings.json", "settings.local.json"):
        settings = load_json(root / name)
        if settings and settings.get("hooks"):
            return True
    return (root / ".claude-plugin").exists()


def mcp_health() -> dict[str, bool] | None:
    """id -> does it actually connect, from `claude mcp list`. None if we cannot tell.

    Configured is not the same as working. A catalog entry naming a package that does not
    exist is accepted by `claude mcp add`, reported as success by `make mcp`, and then
    fails silently forever — which is exactly what happened to the BigQuery server, for
    weeks, because nothing here ever asked whether a configured server responds.

    `claude mcp list` starts each server, so this is seconds rather than instant. That is
    the price of the check being worth anything.
    """
    if not shutil.which("claude"):
        return None
    try:
        out = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=120)
    except (subprocess.SubprocessError, OSError):
        return None
    if out.returncode != 0 and not out.stdout:
        return None

    health: dict[str, bool] = {}
    for line in out.stdout.splitlines():
        name, sep, rest = line.partition(":")
        # The output format is not a stable contract, so match loosely and treat anything
        # we cannot classify as unknown rather than as broken.
        if not sep or not name.strip() or name.startswith(" "):
            continue
        if "Connected" in rest:
            health[name.strip()] = True
        elif "Failed" in rest or "failed" in rest:
            health[name.strip()] = False
    return health or None


def check_mcp() -> None:
    """Are the agreed MCP servers configured, and do they actually respond?

    Discoverability is the real problem here, not configuration. Most people have never
    used MCP, so they will not go looking for `make mcp` — and the catalog installing
    successfully tells them nothing, because a catalog entry is not a running server.
    Reporting it here puts it in front of someone at the one moment they are already
    asking whether their setup is right.
    """
    overlay = load_json(REPO / "overlay" / "manifest-overlay.json") or {}
    wanted = overlay.get("activateMcpServers", {}).get("ids", [])
    if not wanted:
        return

    # Where Claude Code keeps *active* servers, as opposed to the installed catalog.
    active: set[str] = set()
    for path in (Path.home() / ".claude.json", Path.home() / ".claude" / "settings.json"):
        conf = load_json(path)
        if conf:
            active |= set(conf.get("mcpServers", {}))

    missing = [s for s in wanted if s not in active]
    if missing:
        note(
            WARN,
            f"mcp: {len(missing)} of {len(wanted)} agreed server(s) not active "
            f"({', '.join(missing)})",
            "run `make mcp` — an MCP server lets an agent reach live docs or BigQuery "
            "instead of asking you to paste results. Installing the catalog does not start "
            "one. See overlay/README.md.",
        )
        return

    health = mcp_health()
    if health is None:
        note(
            WARN,
            f"mcp: all {len(wanted)} agreed server(s) configured — could not test them",
            "`claude mcp list` was unavailable, so this says nothing about whether they "
            "work. Configured is not connected.",
        )
        return

    broken = [s for s in wanted if health.get(s) is False]
    untested = [s for s in wanted if s not in health]
    if broken:
        note(
            ERR,
            f"mcp: {len(broken)} configured server(s) do not connect ({', '.join(broken)})",
            "run `claude mcp list` for the error. A server can be configured and dead — a "
            "package name that does not exist behaves exactly like this, and nothing else "
            "in this repo would notice.",
        )
        return
    if untested:
        note(
            WARN,
            f"mcp: {len(wanted) - len(untested)} of {len(wanted)} confirmed "
            f"connected; could not classify {', '.join(untested)}",
            "",
        )
        return
    note(OK, f"mcp: all {len(wanted)} agreed server(s) connected")


class FileContext:
    """Answers check_files asks the slow tools, each at most once per doctor run."""

    def __init__(self) -> None:
        self._applied: bool | None = None
        self._plans: dict[str, set[str] | None] = {}

    def setup_user_applied(self) -> bool:
        if self._applied is None:
            self._applied = setup_user_applied()
        return self._applied

    def plan(self, target: str) -> set[str] | None:
        if target not in self._plans:
            self._plans[target] = planned_paths(target)
        return self._plans[target]


def split_issue(issue: dict, target: str, ctx: FileContext) -> tuple[list, list, list]:
    """Divide an issue's paths into (stale records, setup-user's edits, real drift)."""
    code = issue.get("code")
    rest = [Path(p) for p in issue.get("paths", [])]

    stale: list[Path] = []
    if rest and code in STALE_CODES:
        plan = ctx.plan(target)
        if plan is not None:
            stale = [p for p in rest if str(p) not in plan]
            rest = [p for p in rest if p not in stale]

    ours: list[Path] = []
    candidates = [p for p in rest if p.name in SETUP_USER_FILES]
    if code in SETUP_USER_CODES and candidates and ctx.setup_user_applied():
        ours = candidates
        rest = [p for p in rest if p not in ours]
    return stale, ours, rest


def report_issue(adapter: str, issue: dict, target: str, ctx: FileContext) -> None:
    status = ERR if issue.get("severity") == "error" else WARN
    if not issue.get("paths"):
        note(status, f"{adapter}: {issue.get('message')}", "")
        return

    stale, ours, rest = split_issue(issue, target, ctx)
    for path in stale:
        note(OK, f"{adapter}: stale install-state record ignored: {path.name}")
    if ours:
        names = ", ".join(p.name for p in ours)
        note(OK, f"{adapter}: {names} changed by setup-user.py, as intended")
    if not rest:
        return
    if not stale and not ours:
        note(status, f"{adapter}: {issue.get('message')}", "")
        return
    # Some paths were explained away, so upstream's count no longer fits; restate it.
    message = issue.get("message", "").split(" ", 1)[-1]
    names = ", ".join(p.name for p in rest)
    note(status, f"{adapter}: {len(rest)} {message}: {names}", "")


def check_files(report: dict | None) -> None:
    if report is None:
        note(
            WARN,
            "upstream doctor unavailable — no file-level check",
            "run `make plan` to materialize .ecc/ first",
        )
        return
    ctx = FileContext()
    for result in report.get("results", []):
        adapter = result["adapter"]["id"]
        target = result["adapter"].get("target", adapter.split("-")[0])
        issues = result.get("issues", [])
        if not issues:
            note(OK, f"{adapter}: managed files intact")
            continue
        for issue in issues:
            report_issue(adapter, issue, target, ctx)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 1 if anything is actionable")
    args = parser.parse_args()

    pin = load_json(REPO / "upstream.json")
    if not pin:
        print("cannot read upstream.json — is this the right directory?", file=sys.stderr)
        return 2
    pinned = pin["upstream"]["sha"]

    report = upstream_doctor()
    states: list[tuple[Path, dict]] = []
    for path in state_paths(report):
        state = load_json(path)
        if state:
            states.append((path, state))
    states = drop_legacy_opencode(states)
    if report and legacy_opencode_state() not in [p for p, _ in states]:
        legacy = str(legacy_opencode_state())
        report["results"] = [
            r for r in report.get("results", []) if r.get("installStatePath") != legacy
        ]

    if not states:
        print("Nothing is installed — no ECC install-state found.\n")
        print("  run `make install`")
        return 1 if args.strict else 0

    check_pin(states, pinned)
    check_content(states)
    check_hooks(states)
    check_mcp()
    check_repo()
    check_files(report)

    print(f"agent-harness-config doctor — pin {pinned[:8]}\n")
    for status, headline, advice in findings:
        print(f"[{LABEL[status]}] {headline}")
        if advice:
            print(f"           -> {advice}")

    errors = sum(1 for s, _, _ in findings if s == ERR)
    warnings = sum(1 for s, _, _ in findings if s == WARN)
    print(f"\n{len(findings)} checks, {errors} needing action, {warnings} worth a look.")
    if any(s == ERR and "make update" in a for s, _, a in findings):
        print("\nThe errors that say so are fixed by `make update`.")

    return 1 if args.strict and (errors or warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
