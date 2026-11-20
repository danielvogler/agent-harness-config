#!/usr/bin/env python3
"""Run a pinned Langfuse on this machine, for traces of your own agent sessions.

Langfuse's own instructions are `git clone`, `docker compose up`. Followed as written
they leave four things that differ from person to person or that nobody chose:

  - the clone is whatever `main` was that day and the images float on the tag `4`, so
    two people run two versions and an update happens whenever Docker pulls;
  - usage telemetry to Langfuse is on;
  - the web UI, MinIO and the AI gateway listen on every network interface, so the
    traces are on whatever network the laptop joins;
  - every password is the default from the compose file.

`install` settles them the same way for everyone: the release in upstream.json, checked
against its commit; a `.env` (mode 600) with generated passwords, telemetry off and the
image tag; `langfuse/docker-compose.override.yml`, which binds the three open ports to
127.0.0.1. Before anything starts, the merged configuration is read back from Compose
and refused if any port is published beyond the local machine. That check is generic on
purpose: a later release that adds an open port fails here instead of going unnoticed.

Passwords are generated here and written to `.env` only. They are never printed and
never passed on a command line. They are generated only for a first install: the
databases keep the passwords they were created with, so a new one for an existing
volume locks Langfuse out of its own data.

Not part of `make install` or `make update`: it needs a Docker engine, downloads about
6 GB of images and keeps full transcripts. That is a decision someone makes.

Safe to run again; it changes only what differs. The one destructive command is
`reset`, which removes the volumes and asks first.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PINS = REPO / "upstream.json"
OVERRIDE = REPO / "langfuse" / "docker-compose.override.yml"
OVERRIDE_NAME = "docker-compose.override.yml"

# Fixed, so volume names do not depend on the name of the folder.
PROJECT = "langfuse"

# The services of the pinned release. `status` wants each of them running.
SERVICES = (
    "langfuse-web",
    "langfuse-worker",
    "langfuse-ai-gateway",
    "clickhouse",
    "minio",
    "redis",
    "postgres",
)

# The ports Langfuse publishes on every interface, which the override binds to
# 127.0.0.1. `status` wants a listener on each, on the local machine only.
LOCAL_PORTS = (3000, 9090, 3031)
HEALTH_URL = "http://127.0.0.1:3000/api/public/health"
LOOPBACK = ("127.0.0.1", "::1", "localhost")

# Written to .env on every install. Not secrets.
TELEMETRY = "TELEMETRY_ENABLED"
IMAGE_TAG = "LANGFUSE_IMAGE_TAG"

# Every value the compose file marks CHANGEME, by the variable that sets it. The
# variables sharing a row must hold the same value (MinIO's password is also the S3
# secret of three upload settings). Hex only: one of them ends up in a URL and one on
# redis' command line inside its container.
SECRET_GROUPS: tuple[tuple[str, ...], ...] = (
    ("NEXTAUTH_SECRET",),
    ("SALT",),
    ("ENCRYPTION_KEY",),  # must be 64 hex characters
    ("POSTGRES_PASSWORD",),
    ("CLICKHOUSE_PASSWORD",),
    ("REDIS_AUTH",),
    (
        "MINIO_ROOT_PASSWORD",
        "LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY",
        "LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY",
        "LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY",
    ),
)
DATABASE_URL = "postgresql://postgres:{password}@postgres:5432/postgres"

# The Docker engine's memory. Below this Langfuse's seven containers start and are
# then killed one by one; Langfuse itself recommends 16 GiB for a server.
MIN_MEMORY_GIB = 8

# Keychain items and the variables the plugin reads, in the naming the README uses for
# the other tokens.
PROFILE_LINES = """\
# ~/.zprofile — only if not set yet, so a value passed in from outside wins
[[ -z $LANGFUSE_PUBLIC_KEY ]] && LANGFUSE_PUBLIC_KEY=$(security find-generic-password -a "$USER" -s langfuse-public-key -w 2>/dev/null) && export LANGFUSE_PUBLIC_KEY
[[ -z $LANGFUSE_SECRET_KEY ]] && LANGFUSE_SECRET_KEY=$(security find-generic-password -a "$USER" -s langfuse-secret-key -w 2>/dev/null) && export LANGFUSE_SECRET_KEY
export LANGFUSE_BASE_URL=http://localhost:3000
export CC_LANGFUSE_STATE_DIR="$HOME/.claude/cache/langfuse"
"""

OK, WARN, ERR = "ok", "warning", "error"
LABEL = {OK: "  ok  ", WARN: " warn ", ERR: " fail "}
Finding = tuple[str, str, str]  # (status, headline, advice)


class Stop(Exception):
    """A reason to stop, already worded for the person. Never carries a secret."""


def home() -> Path:
    """Where Langfuse is cloned. A function so tests can move it."""
    return Path(os.environ.get("LANGFUSE_HOME") or Path.home() / "opt" / "langfuse")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def passthrough(cmd: list[str]) -> int:
    """Run with the terminal attached, for commands whose progress the person watches."""
    return subprocess.run(cmd).returncode


def confirm(question: str, expected: str = "y") -> bool:
    try:
        return input(question).strip() == expected
    except EOFError:
        return False


# ----------------- pins -----------------


def load_pins(path: Path | None = None) -> dict:
    """The `langfuse` block of upstream.json, checked. Raises Stop on a bad pin."""
    try:
        block = json.loads((path or PINS).read_text())["langfuse"]
        server, plugin = block["server"], block["plugin"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise Stop(f"upstream.json has no usable langfuse block ({error})") from error
    for name, pin in (("server", server), ("plugin", plugin)):
        if not re.fullmatch(r"v\d+\.\d+\.\d+", str(pin.get("tag", ""))):
            raise Stop(f"upstream.json: langfuse.{name}.tag must be a release tag like v1.2.3")
        if not re.fullmatch(r"[0-9a-f]{40}", str(pin.get("sha", ""))):
            raise Stop(f"upstream.json: langfuse.{name}.sha must be a full commit hash")
    return block


def version(pin: dict) -> str:
    """v1.2.3 -> 1.2.3: the image tag, and what the health endpoint reports."""
    return pin["tag"].removeprefix("v")


# ----------------- .env -----------------


def read_env(path: Path) -> dict[str, str]:
    """KEY=VALUE lines of a .env file. Values are never printed by any caller."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def new_secrets() -> dict[str, str]:
    values: dict[str, str] = {}
    for group in SECRET_GROUPS:
        value = secrets.token_hex(32)
        values.update(dict.fromkeys(group, value))
    values["DATABASE_URL"] = DATABASE_URL.format(password=values["POSTGRES_PASSWORD"])
    return values


def write_private(path: Path, text: str) -> None:
    """Write a file only its owner can read, also when it existed with wider rights."""
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(text)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def upsert(text: str, key: str, value: str) -> str:
    """Set KEY=value in .env text, replacing the line that sets it or adding one."""
    line = f"{key}={value}"
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    return text + ("" if not text or text.endswith("\n") else "\n") + line + "\n"


def write_env(path: Path, image_tag: str, has_volumes: bool) -> list[str]:
    """Create or update .env. Returns the names of secrets still on a default.

    A first install gets generated secrets. An existing file keeps every value it has:
    only telemetry and the image tag are set. Without a file but with volumes, nothing
    can be generated safely, so that stops.
    """
    if path.is_file():
        text = path.read_text()
    elif has_volumes:
        raise Stop(
            f"{path} is missing but Langfuse's volumes exist, created with other passwords.\n"
            "  New passwords would lock Langfuse out of its own data. Either restore the\n"
            "  .env they were created with, or remove the data: make langfuse-reset"
        )
    else:
        text = "# Written by `make langfuse-install`. Keep it; the databases depend on it.\n"
        for key, value in new_secrets().items():
            text = upsert(text, key, value)
    text = upsert(text, TELEMETRY, "false")
    text = upsert(text, IMAGE_TAG, image_tag)
    write_private(path, text)
    present = read_env(path)
    return [group[0] for group in SECRET_GROUPS if not present.get(group[0])]


# ----------------- checkout -----------------


def git(directory: Path, *args: str) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(directory), *args])


def head(directory: Path) -> str | None:
    """The commit checked out in `directory`, or None when it is not a checkout itself."""
    # Without this, a plain folder inside some other repository answers with that
    # repository's commit, and the install would switch the wrong working tree.
    if not (directory / ".git").exists():
        return None
    out = git(directory, "rev-parse", "HEAD")
    return out.stdout.strip() if out.returncode == 0 else None


def checkout(directory: Path, pin: dict) -> None:
    """Put the pinned release in `directory`, and prove it is the pinned commit."""
    if not directory.exists():
        directory.parent.mkdir(parents=True, exist_ok=True)
        print(f"==> cloning Langfuse {pin['tag']}")
        clone = ["git", "clone", "--quiet", "--depth", "1", "--branch", pin["tag"]]
        if passthrough([*clone, "-c", "advice.detachedHead=false", pin["repo"], str(directory)]):
            raise Stop("git clone failed")
    elif head(directory) is None or not (directory / "docker-compose.yml").is_file():
        raise Stop(f"{directory} exists but is not a Langfuse checkout; move it aside first")
    elif head(directory) != pin["sha"]:
        print(f"==> moving the checkout to Langfuse {pin['tag']}")
        fetch = git(directory, "fetch", "--quiet", "--depth", "1", pin["repo"], "tag", pin["tag"])
        if fetch.returncode != 0:
            raise Stop(f"git fetch failed: {fetch.stderr.strip()}")
        switch = git(
            directory, "-c", "advice.detachedHead=false", "checkout", "--detach", pin["tag"]
        )
        if switch.returncode != 0:
            raise Stop(f"git checkout failed: {switch.stderr.strip()}")
    # A tag can be moved onto other code. The commit cannot.
    if head(directory) != pin["sha"]:
        raise Stop(
            f"{pin['tag']} is not the pinned commit {pin['sha'][:12]}: upstream moved the tag,\n"
            "  or the checkout has local commits. Nothing was started."
        )


def install_override(directory: Path, assume_yes: bool) -> None:
    """Copy the override. A different one already there is shown and asked about."""
    target = directory / OVERRIDE_NAME
    wanted = OVERRIDE.read_text()
    if target.is_file() and target.read_text() != wanted:
        print(f"==> {OVERRIDE_NAME} in {directory} differs from this repo's:")
        diff = difflib.unified_diff(
            target.read_text().splitlines(),
            wanted.splitlines(),
            "installed",
            "this repo",
            lineterm="",
        )
        print("\n".join(diff))
        if not assume_yes and not confirm("Replace it? [y/N] "):
            raise Stop("not installed")
    target.write_text(wanted)


# ----------------- docker -----------------


def compose_command() -> list[str] | None:
    """`docker compose` when the plugin is there, else the standalone `docker-compose`."""
    if shutil.which("docker") and run(["docker", "compose", "version"]).returncode == 0:
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def compose(directory: Path) -> list[str]:
    command = compose_command()
    if command is None:
        raise Stop("Docker Compose not found. With Homebrew: brew install docker docker-compose")
    files = ["-f", str(directory / "docker-compose.yml"), "-f", str(directory / OVERRIDE_NAME)]
    return [*command, "-p", PROJECT, "--project-directory", str(directory), *files]


def engine_memory_gib() -> float | None:
    """The Docker engine's memory, or None when no engine answers."""
    if not shutil.which("docker"):
        return None
    out = run(["docker", "info", "--format", "{{.MemTotal}}"])
    try:
        return int(out.stdout.strip()) / 2**30 if out.returncode == 0 else None
    except ValueError:
        return None


def require_engine() -> None:
    memory = engine_memory_gib()
    if memory is None:
        raise Stop(
            "No Docker engine answers. Start yours first; with Colima:\n"
            f"  colima start --cpu 4 --memory {MIN_MEMORY_GIB}"
        )
    # A VM given 8 GiB reports a little less.
    if memory < MIN_MEMORY_GIB - 0.5:
        print(
            f"[ warn ] the Docker engine has {memory:.1f} GiB; Langfuse needs about "
            f"{MIN_MEMORY_GIB}. With Colima: colima stop && colima start --cpu 4 "
            f"--memory {MIN_MEMORY_GIB}"
        )


def has_volumes() -> bool:
    out = run(
        ["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]
    )
    return out.returncode == 0 and bool(out.stdout.strip())


def open_ports(config: dict) -> list[str]:
    """Published ports of a merged Compose config that are not bound to this machine."""
    found = []
    for name, service in sorted(config.get("services", {}).items()):
        for port in service.get("ports") or []:
            if port.get("published") and port.get("host_ip") not in LOOPBACK:
                found.append(f"{name}:{port['published']}")
    return found


def verify_config(directory: Path, image_tag: str) -> None:
    """Read the merged configuration back and refuse it if it is not what was meant."""
    out = run([*compose(directory), "config", "--format", "json"])
    if out.returncode != 0:
        # stderr only: stdout would be the configuration, passwords included.
        raise Stop(f"docker compose config failed: {out.stderr.strip()}")
    try:
        config = json.loads(out.stdout)
    except json.JSONDecodeError as error:
        raise Stop("docker compose config did not print JSON") from error
    exposed = open_ports(config)
    if exposed:
        raise Stop(
            "these ports would be published beyond this machine: " + ", ".join(exposed) + "\n"
            f"  Bind them to 127.0.0.1 in langfuse/{OVERRIDE_NAME}. Nothing was started."
        )
    services = config.get("services", {})
    missing = [name for name in SERVICES if name not in services]
    if missing:
        raise Stop("the pinned release has no service " + ", ".join(missing))
    web = services["langfuse-web"]
    if str(web.get("environment", {}).get(TELEMETRY)).lower() != "false":
        raise Stop(f"{TELEMETRY} is not false in the merged configuration")
    if not str(web.get("image", "")).endswith(f":{image_tag}"):
        raise Stop(f"langfuse-web would not run the pinned image tag {image_tag}")


# ----------------- status -----------------


def parse_ps(text: str) -> list[dict]:
    """`docker compose ps --format json`: one array in older versions, a line each in newer."""
    text = text.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def container_findings(containers: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    state = {c.get("Service"): c.get("State") for c in containers}
    down = [name for name in SERVICES if state.get(name) != "running"]
    if down:
        findings.append((ERR, "not running: " + ", ".join(down), "run `make langfuse-up`"))
    else:
        findings.append((OK, f"all {len(SERVICES)} containers running", ""))
    # A set: Docker lists a port once for IPv4 and once for IPv6.
    exposed = sorted(
        {
            f"{c.get('Service')}:{p['PublishedPort']}"
            for c in containers
            for p in c.get("Publishers") or []
            if p.get("PublishedPort") and p.get("URL") not in LOOPBACK
        }
    )
    if exposed:
        findings.append(
            (
                ERR,
                "published beyond this machine: " + ", ".join(exposed),
                "run `make langfuse-install`; it restores the override",
            )
        )
    return findings


def listeners(text: str) -> dict[int, set[str]]:
    """port -> addresses listening on it, from `lsof -nP -iTCP -sTCP:LISTEN` or `ss -ltnH`.

    Both print `address:port` somewhere on the line; lsof as `*:3000` or
    `127.0.0.1:3000`, ss as `0.0.0.0:3000`, `[::1]:3000` or `*:3000`.
    """
    found: dict[int, set[str]] = {}
    for line in text.splitlines():
        for address, port in re.findall(r"(\*|\[[0-9a-fA-F:]*\]|[0-9.]+):(\d+)(?=\s|$)", line):
            found.setdefault(int(port), set()).add(address.strip("[]"))
    return found


def listener_findings(text: str) -> list[Finding]:
    found = listeners(text)
    findings: list[Finding] = []
    for port in LOCAL_PORTS:
        addresses = found.get(port, set())
        beyond = sorted(a for a in addresses if a not in LOOPBACK)
        if not addresses:
            findings.append((ERR, f"nothing listens on port {port}", "run `make langfuse-up`"))
        elif beyond:
            findings.append(
                (
                    ERR,
                    f"port {port} listens beyond this machine ({', '.join(beyond)})",
                    "anyone on the same network can read your traces; "
                    "run `make langfuse-install`, which binds it to 127.0.0.1",
                )
            )
        else:
            findings.append((OK, f"port {port} listens on this machine only", ""))
    return findings


def listening_sockets() -> str | None:
    """Every listening TCP socket, or None when no tool can tell.

    lsof shows only the caller's own processes without root. That is enough with a VM
    (Colima, Docker Desktop: the forwarder runs as you) but not for Docker on Linux,
    where root's docker-proxy listens; ss sees those.
    """
    for tool, args in (("ss", ["-ltnH"]), ("lsof", ["-nP", "-iTCP", "-sTCP:LISTEN"])):
        if shutil.which(tool):
            out = run([tool, *args])
            if out.stdout.strip():
                return out.stdout
    return None


def health(expected: str, timeout: float = 5.0) -> Finding:
    # No proxy: a configured one would be asked for 127.0.0.1.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(HEALTH_URL, timeout=timeout) as response:
            body = json.loads(response.read().decode())
    except (urllib.error.URLError, OSError, ValueError) as error:
        return (ERR, f"Langfuse does not answer on {HEALTH_URL}", f"{type(error).__name__}")
    if body.get("status") != "OK":
        return (ERR, f"Langfuse reports status {body.get('status')!r}", "")
    if body.get("version") != expected:
        return (
            ERR,
            f"Langfuse {body.get('version')} is running, the pin is {expected}",
            "run `make langfuse-install`",
        )
    return (OK, f"Langfuse {expected} answers on http://localhost:3000", "")


def wait_until_healthy(expected: str, seconds: int = 300) -> Finding:
    """Poll the health endpoint. The first start migrates the databases, which takes minutes."""
    deadline = time.monotonic() + seconds
    finding = health(expected)
    while finding[0] != OK and time.monotonic() < deadline:
        time.sleep(5)
        finding = health(expected)
    return finding


def status_findings(directory: Path, pins: dict) -> list[Finding]:
    out = run([*compose(directory), "ps", "--all", "--format", "json"])
    if out.returncode != 0:
        return [(ERR, "docker compose ps failed", out.stderr.strip())]
    findings = container_findings(parse_ps(out.stdout))
    sockets = listening_sockets()
    if sockets is None:
        findings.append((WARN, "could not list listening ports (no ss or lsof)", ""))
    else:
        findings.extend(listener_findings(sockets))
    findings.append(health(version(pins["server"])))
    return findings


# ----------------- drift, for `make doctor` and `make update` -----------------


def drift_findings(directory: Path, pins: dict) -> list[Finding]:
    """Compare an installed Langfuse with this checkout, from files alone. Empty if absent."""
    if not directory.is_dir():
        return []
    server = pins["server"]
    advice = "run `make langfuse-install` in a normal terminal"
    findings: list[Finding] = []
    installed = head(directory)
    if installed != server["sha"]:
        short = installed[:12] if installed else "no git checkout"
        findings.append((WARN, f"langfuse: installed {short}, the pin is {server['tag']}", advice))
    override = directory / OVERRIDE_NAME
    if not override.is_file() or override.read_text() != OVERRIDE.read_text():
        findings.append((ERR, f"langfuse: {OVERRIDE_NAME} is missing or differs", advice))
    env_file = directory / ".env"
    env = read_env(env_file)
    if not env_file.is_file():
        findings.append((ERR, "langfuse: no .env, so every password is the public default", advice))
    else:
        if env_file.stat().st_mode & 0o077:
            findings.append((ERR, "langfuse: .env is readable by other users", advice))
        if env.get(TELEMETRY, "").lower() != "false":
            findings.append((ERR, "langfuse: usage telemetry to Langfuse is on", advice))
        if env.get(IMAGE_TAG) != version(server):
            findings.append((WARN, f"langfuse: images are not pinned to {version(server)}", advice))
    return findings or [(OK, f"langfuse: installed {server['tag']} matches the pin", "")]


# ----------------- the plugin -----------------


def claude_json(*args: str) -> list[dict] | None:
    out = run(["claude", "plugin", *args, "--json"])
    try:
        parsed = json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def plugin_steps(pin: dict, marketplaces: list[dict], plugins: list[dict]) -> list[list[str]]:
    """The `claude plugin` commands still to run. Raises Stop when a person has to act."""
    plugin_id = f"{pin['name']}@{pin['marketplace']}"
    steps: list[list[str]] = []
    known = next((m for m in marketplaces if m.get("name") == pin["marketplace"]), None)
    if known is None:
        steps.append(["claude", "plugin", "marketplace", "add", f"{pin['source']}#{pin['tag']}"])
    elif known.get("ref") != pin["tag"]:
        raise Stop(
            f"the marketplace {pin['marketplace']} is not pinned to {pin['tag']} "
            f"(it follows {known.get('ref') or 'the default branch'}).\n"
            "  Removing it also uninstalls its plugin. Run, then run this again:\n"
            f"    claude plugin marketplace remove {pin['marketplace']}"
        )
    installed = next((p for p in plugins if p.get("id") == plugin_id), None)
    if installed is None or known is None:
        steps.append(["claude", "plugin", "install", plugin_id])
    elif installed.get("version") != version(pin):
        steps.append(["claude", "plugin", "update", plugin_id])
    return steps


# ----------------- commands -----------------


def report(findings: list[Finding]) -> int:
    for status, headline, advice in findings:
        print(f"[{LABEL[status]}] {headline}")
        if advice:
            print(f"           -> {advice}")
    return 1 if any(status == ERR for status, _, _ in findings) else 0


def next_steps(pins: dict) -> str:
    plugin = pins["plugin"]
    return f"""
Langfuse is running. What is left is yours, once:

  1. Open http://localhost:3000, sign up (the account exists only on this machine),
     create an organisation and a project, and under Settings, API Keys, a key pair.
  2. Store both keys in the Keychain; `security` asks for the value:
       security add-generic-password -U -a "$USER" -s langfuse-public-key -w
       security add-generic-password -U -a "$USER" -s langfuse-secret-key -w
  3. Add these lines to ~/.zprofile, then open a new terminal:

{PROFILE_LINES}
  4. make langfuse-plugin     (the Claude Code plugin, pinned to {plugin["tag"]})

Traces contain everything a session read, secrets in files included: langfuse/README.md."""


def cmd_install(args: argparse.Namespace) -> int:
    pins = load_pins()
    server = pins["server"]
    directory = home()
    require_engine()
    if directory.exists() and head(directory) not in (None, server["sha"]):
        print(
            f"An install exists in {directory}. It moves to Langfuse {server['tag']};\n"
            "Langfuse then migrates its databases on start, which cannot be undone."
        )
        if not args.yes and not confirm("Continue? [y/N] "):
            raise Stop("not installed")
    checkout(directory, server)
    defaults = write_env(directory / ".env", version(server), has_volumes())
    install_override(directory, args.yes)
    verify_config(directory, version(server))
    if defaults:
        print(
            "[ warn ] still on the compose file's default: " + ", ".join(defaults) + ".\n"
            "           -> kept, because the existing data was created with them; "
            "`make langfuse-reset` starts over with generated ones"
        )
    print("==> starting (the first start downloads about 6 GB of images)")
    if passthrough([*compose(directory), "up", "-d"]):
        raise Stop("docker compose up failed")
    print("==> waiting for Langfuse to answer (minutes on the first start)")
    wait_until_healthy(version(server))
    code = report(status_findings(directory, pins))
    if code == 0:
        print(next_steps(pins))
    return code


def installed_home() -> Path:
    directory = home()
    if not (directory / OVERRIDE_NAME).is_file():
        raise Stop(f"Langfuse is not installed in {directory}. Run: make langfuse-install")
    return directory


def cmd_up(_: argparse.Namespace) -> int:
    pins = load_pins()
    directory = installed_home()
    require_engine()
    verify_config(directory, version(pins["server"]))
    return passthrough([*compose(directory), "up", "-d"])


def cmd_down(_: argparse.Namespace) -> int:
    # Containers and network go, the volumes with the traces stay.
    return passthrough([*compose(installed_home()), "down"])


def cmd_status(_: argparse.Namespace) -> int:
    pins = load_pins()
    directory = installed_home()
    return report([*drift_findings(directory, pins), *status_findings(directory, pins)])


def cmd_reset(_: argparse.Namespace) -> int:
    directory = installed_home()
    out = run(
        ["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]
    )
    print("This stops Langfuse and deletes its volumes:")
    for name in out.stdout.split():
        print(f"  {name}")
    print(
        "Every trace, the account, the project and its API keys are gone afterwards, and\n"
        f"so is {directory / '.env'} with the passwords. There is no undo."
    )
    if not confirm("Type delete to go on: ", expected="delete"):
        print("nothing removed")
        return 1
    if passthrough([*compose(directory), "down", "--volumes"]):
        raise Stop("docker compose down failed; .env was kept")
    (directory / ".env").unlink(missing_ok=True)
    print("Removed. `make langfuse-install` starts a new, empty Langfuse.")
    return 0


def cmd_plugin(_: argparse.Namespace) -> int:
    pin = load_pins()["plugin"]
    if not shutil.which("claude"):
        raise Stop("claude not found on PATH")
    marketplaces, plugins = claude_json("marketplace", "list"), claude_json("list")
    if marketplaces is None or plugins is None:
        raise Stop("could not read `claude plugin ... --json`; update Claude Code")
    steps = plugin_steps(pin, marketplaces, plugins)
    for step in steps:
        print("==> " + " ".join(step))
        if passthrough(step):
            raise Stop("that command failed")
    done = f"{pin['name']} {pin['tag']} is installed from the pinned marketplace."
    print(done if not steps else done + " Restart Claude Code to load it.")
    return 0


def cmd_drift(args: argparse.Namespace) -> int:
    findings = drift_findings(home(), load_pins())
    if args.json:
        print(json.dumps(findings))
    elif args.notice:
        if any(status != OK for status, _, _ in findings):
            print("langfuse changed: run make langfuse-install in a normal terminal")
    else:
        report(findings)
    return 0


def cmd_profile(_: argparse.Namespace) -> int:
    print(PROFILE_LINES, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install", help="clone the pin, write .env, start, check")
    install.add_argument("--yes", action="store_true", help="do not ask before replacing")
    install.set_defaults(run=cmd_install)
    for name, function, text in (
        ("up", cmd_up, "start an installed Langfuse"),
        ("down", cmd_down, "stop it; the traces stay"),
        ("status", cmd_status, "containers, ports, version"),
        ("reset", cmd_reset, "delete every trace and the passwords; asks first"),
        ("plugin", cmd_plugin, "install the pinned Claude Code plugin"),
        ("profile", cmd_profile, "print the lines for ~/.zprofile"),
    ):
        commands.add_parser(name, help=text).set_defaults(run=function)
    drift = commands.add_parser("drift", help="compare the install with this checkout")
    drift.add_argument("--json", action="store_true")
    drift.add_argument("--notice", action="store_true", help="one line, only when it differs")
    drift.set_defaults(run=cmd_drift)
    args = parser.parse_args(argv)

    # The sandbox closes the Docker socket, ~/.claude/plugins and the Keychain.
    if os.environ.get("CLAUDE_SB_GUIDANCE") and args.command not in ("drift", "profile"):
        print("Run this in a normal terminal, not inside claude-sb.", file=sys.stderr)
        return 1
    try:
        return args.run(args)
    except Stop as stop:
        print(f"langfuse: {stop}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
