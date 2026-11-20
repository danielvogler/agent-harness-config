"""tools/langfuse-local.py: the local Langfuse install, without Docker or the network.

What can be wrong here costs more than a failed install: a port open to the network,
a password printed, a database locked out by a new password, a trace store deleted
without a question. Each of those has a test.
"""

from __future__ import annotations

import json
import re
import stat
import subprocess
from pathlib import Path

import pytest
from conftest import load_tool

REPO = Path(__file__).resolve().parent.parent
OVERRIDE = REPO / "langfuse" / "docker-compose.override.yml"


@pytest.fixture
def langfuse(tmp_path: Path, monkeypatch):
    """The tool with LANGFUSE_HOME in a temp folder, never the real install."""
    module = load_tool("langfuse-local.py")
    monkeypatch.setenv("LANGFUSE_HOME", str(tmp_path / "langfuse"))
    monkeypatch.delenv("CLAUDE_SB_GUIDANCE", raising=False)
    return module


def completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


def merged_config(**ports: list[dict]) -> dict:
    """A merged Compose config as `docker compose config --format json` prints it."""
    local = {"host_ip": "127.0.0.1", "published": "1", "target": 1}
    services = {
        name: {"image": f"example/{name}:4.83.0", "ports": ports.get(name, [local])}
        for name in (
            "langfuse-web",
            "langfuse-worker",
            "langfuse-ai-gateway",
            "clickhouse",
            "minio",
            "redis",
            "postgres",
        )
    }
    services["langfuse-web"]["environment"] = {"TELEMETRY_ENABLED": "false"}
    return {"services": services}


class TestPins:
    def test_the_pins_in_this_repo_load(self, langfuse):
        pins = langfuse.load_pins()

        assert langfuse.version(pins["server"]) == pins["server"]["tag"][1:]
        assert pins["plugin"]["source"].count("/") == 1

    @pytest.mark.parametrize("tag", ["main", "4", "latest", "v4.83"])
    def test_a_moving_reference_is_not_a_pin(self, langfuse, tmp_path, tag):
        # Arrange
        pin = {"repo": "https://example.com/x.git", "tag": tag, "sha": "a" * 40}
        path = tmp_path / "upstream.json"
        path.write_text(json.dumps({"langfuse": {"server": pin, "plugin": pin}}))

        # Act, Assert
        with pytest.raises(langfuse.Stop, match="release tag"):
            langfuse.load_pins(path)

    def test_a_short_commit_is_refused(self, langfuse, tmp_path):
        pin = {"repo": "https://example.com/x.git", "tag": "v1.2.3", "sha": "abc1234"}
        path = tmp_path / "upstream.json"
        path.write_text(json.dumps({"langfuse": {"server": pin, "plugin": pin}}))

        with pytest.raises(langfuse.Stop, match="full commit hash"):
            langfuse.load_pins(path)

    def test_no_version_is_written_outside_upstream_json(self):
        # One place to bump. The docs name the pin, not its value.
        pins = json.loads((REPO / "upstream.json").read_text())["langfuse"]
        versions = [pins[name]["tag"].removeprefix("v") for name in ("server", "plugin")]
        files = [REPO / "tools" / "langfuse-local.py", REPO / "Makefile", OVERRIDE]
        files.append(REPO / "langfuse" / "README.md")

        repeated = [
            f"{path.relative_to(REPO)}: {version}"
            for path in files
            for version in versions
            if version in path.read_text()
        ]

        assert repeated == []


class TestEnv:
    def test_a_first_install_gets_generated_secrets_only_the_owner_can_read(
        self, langfuse, tmp_path
    ):
        # Arrange
        path = tmp_path / ".env"

        # Act
        defaults = langfuse.write_env(path, "4.83.0", has_volumes=False)

        # Assert
        env = langfuse.read_env(path)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert defaults == []
        assert env["TELEMETRY_ENABLED"] == "false"
        assert env["LANGFUSE_IMAGE_TAG"] == "4.83.0"
        assert re.fullmatch(r"[0-9a-f]{64}", env["ENCRYPTION_KEY"])
        assert env["POSTGRES_PASSWORD"] in env["DATABASE_URL"]
        assert env["MINIO_ROOT_PASSWORD"] == env["LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY"]
        assert env["MINIO_ROOT_PASSWORD"] == env["LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY"]
        assert env["MINIO_ROOT_PASSWORD"] == env["LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY"]

    def test_no_secret_is_one_of_the_compose_files_defaults(self, langfuse, tmp_path):
        path = tmp_path / ".env"

        langfuse.write_env(path, "4.83.0", has_volumes=False)

        published = {"postgres", "clickhouse", "miniosecret", "myredissecret", "mysalt", "mysecret"}
        values = set(langfuse.read_env(path).values())
        assert not published & values
        assert "0" * 64 not in values

    def test_each_secret_differs(self, langfuse):
        generated = langfuse.new_secrets()

        firsts = [generated[group[0]] for group in langfuse.SECRET_GROUPS]
        assert len(set(firsts)) == len(firsts)

    def test_an_existing_env_keeps_its_secrets(self, langfuse, tmp_path):
        # The databases keep the passwords they were created with.
        path = tmp_path / ".env"
        path.write_text("POSTGRES_PASSWORD=kept\nTELEMETRY_ENABLED=true\n# a note\n")
        path.chmod(0o644)

        defaults = langfuse.write_env(path, "4.83.0", has_volumes=True)

        env = langfuse.read_env(path)
        assert env["POSTGRES_PASSWORD"] == "kept"  # pragma: allowlist secret
        assert env["TELEMETRY_ENABLED"] == "false"
        assert env["LANGFUSE_IMAGE_TAG"] == "4.83.0"
        assert "# a note" in path.read_text()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert "POSTGRES_PASSWORD" not in defaults
        assert "REDIS_AUTH" in defaults

    def test_writing_twice_changes_nothing(self, langfuse, tmp_path):
        path = tmp_path / ".env"
        langfuse.write_env(path, "4.83.0", has_volumes=False)
        first = path.read_text()

        langfuse.write_env(path, "4.83.0", has_volumes=True)

        assert path.read_text() == first

    def test_no_new_passwords_for_volumes_that_exist(self, langfuse, tmp_path):
        path = tmp_path / ".env"

        with pytest.raises(langfuse.Stop, match="lock Langfuse out"):
            langfuse.write_env(path, "4.83.0", has_volumes=True)

        assert not path.exists()

    def test_install_never_prints_a_secret(self, langfuse, tmp_path, capsys):
        path = tmp_path / ".env"

        langfuse.write_env(path, "4.83.0", has_volumes=False)

        printed = capsys.readouterr()
        for value in langfuse.read_env(path).values():
            assert len(value) < 32 or value not in printed.out + printed.err


class TestOverride:
    def test_it_binds_every_port_langfuse_leaves_open(self):
        text = OVERRIDE.read_text()

        ports = re.findall(r"^\s+- (\S+)$", text, re.MULTILINE)
        assert len(ports) == 4
        assert all(port.startswith("127.0.0.1:") for port in ports)
        # Without !override Compose appends, and the open port stays published too.
        assert text.count("ports: !override") == 3

    def test_it_covers_the_ports_status_checks(self, langfuse):
        text = OVERRIDE.read_text()

        for port in langfuse.LOCAL_PORTS:
            assert re.search(rf"127\.0\.0\.1:(\$\{{[A-Z_]+:-)?{port}\}}?:", text)

    def test_a_different_override_is_shown_and_kept_on_no(
        self, langfuse, tmp_path, monkeypatch, capsys
    ):
        # Arrange
        (tmp_path / "docker-compose.override.yml").write_text("services: {}\n")
        monkeypatch.setattr(langfuse, "confirm", lambda *_, **__: False)

        # Act
        with pytest.raises(langfuse.Stop):
            langfuse.install_override(tmp_path, assume_yes=False)

        # Assert
        assert "-services: {}" in capsys.readouterr().out
        assert (tmp_path / "docker-compose.override.yml").read_text() == "services: {}\n"

    def test_the_same_override_is_not_asked_about(self, langfuse, tmp_path, monkeypatch):
        (tmp_path / "docker-compose.override.yml").write_text(OVERRIDE.read_text())
        monkeypatch.setattr(langfuse, "confirm", lambda *_, **__: pytest.fail("asked"))

        langfuse.install_override(tmp_path, assume_yes=False)


class TestMergedConfig:
    @pytest.fixture
    def config(self, langfuse, monkeypatch):
        """Let a test set what `docker compose config` prints."""
        holder = {"config": merged_config()}
        monkeypatch.setattr(langfuse, "compose", lambda _: ["compose"])
        monkeypatch.setattr(
            langfuse, "run", lambda *_, **__: completed(json.dumps(holder["config"]))
        )
        return holder

    def test_a_local_only_config_passes(self, langfuse, config, tmp_path):
        langfuse.verify_config(tmp_path, "4.83.0")

    @pytest.mark.parametrize("host_ip", [None, "", "0.0.0.0", "::"])
    def test_a_port_open_to_the_network_stops_the_install(
        self, langfuse, config, tmp_path, host_ip
    ):
        # A later release that adds an open port must not start unnoticed.
        port = {"published": "4000", "target": 4000}
        if host_ip is not None:
            port["host_ip"] = host_ip
        config["config"] = merged_config(redis=[port])

        with pytest.raises(langfuse.Stop, match="redis:4000"):
            langfuse.verify_config(tmp_path, "4.83.0")

    def test_telemetry_left_on_stops_the_install(self, langfuse, config, tmp_path):
        config["config"]["services"]["langfuse-web"]["environment"]["TELEMETRY_ENABLED"] = "true"

        with pytest.raises(langfuse.Stop, match="TELEMETRY_ENABLED"):
            langfuse.verify_config(tmp_path, "4.83.0")

    def test_a_floating_image_tag_stops_the_install(self, langfuse, config, tmp_path):
        config["config"]["services"]["langfuse-web"]["image"] = "example/langfuse:4"

        with pytest.raises(langfuse.Stop, match="pinned image tag"):
            langfuse.verify_config(tmp_path, "4.83.0")

    def test_a_missing_service_stops_the_install(self, langfuse, config, tmp_path):
        del config["config"]["services"]["langfuse-ai-gateway"]

        with pytest.raises(langfuse.Stop, match="langfuse-ai-gateway"):
            langfuse.verify_config(tmp_path, "4.83.0")


class TestCheckout:
    def test_a_moved_tag_is_refused(self, langfuse, tmp_path, monkeypatch):
        # Arrange: the checkout exists and stays on another commit whatever is fetched.
        (tmp_path / "docker-compose.yml").write_text("services: {}\n")
        monkeypatch.setattr(langfuse, "head", lambda _: "b" * 40)
        monkeypatch.setattr(langfuse, "git", lambda *_: completed())
        pin = {"repo": "https://example.com/x.git", "tag": "v1.2.3", "sha": "a" * 40}

        # Act, Assert
        with pytest.raises(langfuse.Stop, match="not the pinned commit"):
            langfuse.checkout(tmp_path, pin)

    PIN = {"repo": "https://example.com/x.git", "tag": "v1.2.3", "sha": "a" * 40}

    def test_a_folder_that_is_no_checkout_is_left_alone(self, langfuse, tmp_path, monkeypatch):
        # Arrange: a plain folder, here inside this repository's own checkout or not.
        monkeypatch.setattr(langfuse, "git", lambda *_: pytest.fail("ran git"))
        monkeypatch.setattr(langfuse, "passthrough", lambda _: pytest.fail("ran a command"))

        # Act, Assert
        assert langfuse.head(tmp_path) is None
        with pytest.raises(langfuse.Stop, match="not a Langfuse checkout"):
            langfuse.checkout(tmp_path, self.PIN)

    def test_another_projects_checkout_is_left_alone(self, langfuse, tmp_path, monkeypatch):
        # LANGFUSE_HOME pointed at some other repository must not switch its working tree.
        monkeypatch.setattr(langfuse, "head", lambda _: "b" * 40)
        monkeypatch.setattr(langfuse, "git", lambda *_: pytest.fail("ran git"))

        with pytest.raises(langfuse.Stop, match="not a Langfuse checkout"):
            langfuse.checkout(tmp_path, self.PIN)


class TestStatus:
    def containers(self, langfuse, url: str = "127.0.0.1") -> list[dict]:
        port = {"URL": url, "TargetPort": 3000, "PublishedPort": 3000, "Protocol": "tcp"}
        unpublished = {"URL": "", "TargetPort": 9009, "PublishedPort": 0, "Protocol": "tcp"}
        return [
            {"Service": name, "State": "running", "Publishers": [port, unpublished]}
            for name in langfuse.SERVICES
        ]

    def test_seven_running_containers_on_local_ports_are_ok(self, langfuse):
        findings = langfuse.container_findings(self.containers(langfuse))

        assert [status for status, _, _ in findings] == [langfuse.OK]
        assert "7 containers" in findings[0][1]

    def test_a_missing_container_is_named(self, langfuse):
        containers = [c for c in self.containers(langfuse) if c["Service"] != "langfuse-ai-gateway"]

        findings = langfuse.container_findings(containers)

        assert findings[0][0] == langfuse.ERR
        assert "langfuse-ai-gateway" in findings[0][1]

    def test_an_exited_container_is_not_running(self, langfuse):
        containers = self.containers(langfuse)
        containers[0]["State"] = "exited"

        assert langfuse.container_findings(containers)[0][0] == langfuse.ERR

    def test_a_port_published_on_every_interface_is_reported_once(self, langfuse):
        # Docker lists it for IPv4 and for IPv6.
        containers = self.containers(langfuse)
        open_port = {"TargetPort": 3000, "PublishedPort": 3000, "Protocol": "tcp"}
        containers[0]["Publishers"] = [{**open_port, "URL": "0.0.0.0"}, {**open_port, "URL": "::"}]

        findings = langfuse.container_findings(containers)

        assert findings[1][0] == langfuse.ERR
        assert findings[1][1].count(":3000") == 1

    def test_both_shapes_of_compose_ps_output_parse(self, langfuse):
        rows = [{"Service": "redis"}, {"Service": "minio"}]

        as_lines = "\n".join(json.dumps(row) for row in rows)

        assert langfuse.parse_ps(json.dumps(rows)) == rows
        assert langfuse.parse_ps(as_lines) == rows
        assert langfuse.parse_ps("") == []

    LSOF = (
        "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n"
        "ssh 1 me 10u IPv4 0xa2f6 0t0 TCP {web}:3000 (LISTEN)\n"
        "ssh 1 me 11u IPv4 0xe8d8 0t0 TCP 127.0.0.1:9090 (LISTEN)\n"
        "ssh 1 me 12u IPv6 0x6fd6 0t0 TCP [::1]:3031 (LISTEN)\n"
    )

    def test_local_listeners_are_ok(self, langfuse):
        findings = langfuse.listener_findings(self.LSOF.format(web="127.0.0.1"))

        assert [status for status, _, _ in findings] == [langfuse.OK] * 3

    def test_a_listener_on_every_interface_is_an_error(self, langfuse):
        # What Colima forwards when the container port is not bound to 127.0.0.1.
        findings = langfuse.listener_findings(self.LSOF.format(web="*"))

        assert findings[0][0] == langfuse.ERR
        assert "3000" in findings[0][1]
        assert [status for status, _, _ in findings[1:]] == [langfuse.OK] * 2

    def test_ss_output_is_read_too(self, langfuse):
        text = (
            "LISTEN 0 4096 0.0.0.0:3000 0.0.0.0:*\n"
            "LISTEN 0 4096 127.0.0.1:9090 0.0.0.0:*\n"
            "LISTEN 0 4096 [::]:3031 [::]:*\n"
        )

        statuses = [status for status, _, _ in langfuse.listener_findings(text)]

        assert statuses == [langfuse.ERR, langfuse.OK, langfuse.ERR]

    def test_a_port_nobody_listens_on_is_an_error(self, langfuse):
        findings = langfuse.listener_findings("")

        assert [status for status, _, _ in findings] == [langfuse.ERR] * 3


class TestDrift:
    @pytest.fixture
    def pins(self, langfuse):
        return langfuse.load_pins()

    @pytest.fixture
    def installed(self, langfuse, pins, tmp_path, monkeypatch) -> Path:
        """A folder that looks like an install of the pin."""
        directory = tmp_path / "langfuse"
        directory.mkdir()
        (directory / "docker-compose.override.yml").write_text(OVERRIDE.read_text())
        langfuse.write_env(directory / ".env", langfuse.version(pins["server"]), has_volumes=False)
        monkeypatch.setattr(langfuse, "head", lambda _: pins["server"]["sha"])
        return directory

    def test_nothing_installed_is_nothing_to_report(self, langfuse, pins, tmp_path):
        assert langfuse.drift_findings(tmp_path / "missing", pins) == []

    def test_an_install_of_the_pin_is_ok(self, langfuse, pins, installed):
        findings = langfuse.drift_findings(installed, pins)

        assert [status for status, _, _ in findings] == [langfuse.OK]

    def test_an_older_checkout_is_named(self, langfuse, pins, installed, monkeypatch):
        monkeypatch.setattr(langfuse, "head", lambda _: "c" * 40)

        findings = langfuse.drift_findings(installed, pins)

        assert findings[0][0] == langfuse.WARN
        assert "make langfuse-install" in findings[0][2]

    def test_telemetry_on_is_an_error(self, langfuse, pins, installed):
        env = installed / ".env"
        env.write_text(env.read_text().replace("TELEMETRY_ENABLED=false", "TELEMETRY_ENABLED=true"))

        findings = langfuse.drift_findings(installed, pins)

        assert [(s, "telemetry" in h) for s, h, _ in findings] == [(langfuse.ERR, True)]

    def test_a_readable_env_is_an_error(self, langfuse, pins, installed):
        (installed / ".env").chmod(0o644)

        findings = langfuse.drift_findings(installed, pins)

        assert [(s, "readable" in h) for s, h, _ in findings] == [(langfuse.ERR, True)]

    def test_a_changed_override_is_an_error(self, langfuse, pins, installed):
        (installed / "docker-compose.override.yml").write_text("services: {}\n")

        findings = langfuse.drift_findings(installed, pins)

        assert findings[0][0] == langfuse.ERR

    def test_the_notice_for_make_update_is_silent_without_an_install(self, langfuse, capsys):
        code = langfuse.main(["drift", "--notice"])

        assert code == 0
        assert capsys.readouterr().out == ""


class TestPlugin:
    PIN = {
        "source": "example/plugin",
        "marketplace": "market",
        "name": "tracer",
        "tag": "v1.2.2",
        "sha": "a" * 40,
    }

    def test_a_first_install_adds_the_marketplace_at_the_tag(self, langfuse):
        steps = langfuse.plugin_steps(self.PIN, [], [])

        assert steps == [
            ["claude", "plugin", "marketplace", "add", "example/plugin#v1.2.2"],
            ["claude", "plugin", "install", "tracer@market"],
        ]

    def test_the_pinned_version_needs_nothing(self, langfuse):
        marketplaces = [{"name": "market", "ref": "v1.2.2"}]
        plugins = [{"id": "tracer@market", "version": "1.2.2"}]

        assert langfuse.plugin_steps(self.PIN, marketplaces, plugins) == []

    def test_an_older_plugin_from_the_pinned_marketplace_is_updated(self, langfuse):
        marketplaces = [{"name": "market", "ref": "v1.2.2"}]
        plugins = [{"id": "tracer@market", "version": "1.2.1"}]

        steps = langfuse.plugin_steps(self.PIN, marketplaces, plugins)

        assert steps == [["claude", "plugin", "update", "tracer@market"]]

    @pytest.mark.parametrize("known", [{"name": "market"}, {"name": "market", "ref": "v1.2.1"}])
    def test_a_marketplace_that_follows_something_else_is_left_to_the_person(self, langfuse, known):
        # Removing a marketplace uninstalls its plugins: not done without being asked.
        with pytest.raises(langfuse.Stop, match="claude plugin marketplace remove market"):
            langfuse.plugin_steps(self.PIN, [known], [])


class TestCommands:
    def test_reset_removes_nothing_without_the_word(self, langfuse, tmp_path, monkeypatch, capsys):
        # Arrange
        directory = tmp_path / "langfuse"
        directory.mkdir()
        (directory / "docker-compose.override.yml").write_text(OVERRIDE.read_text())
        (directory / ".env").write_text("POSTGRES_PASSWORD=kept\n")
        monkeypatch.setattr(langfuse, "run", lambda *_, **__: completed("langfuse_postgres_data\n"))
        monkeypatch.setattr(langfuse, "compose", lambda _: ["compose"])
        monkeypatch.setattr(langfuse, "passthrough", lambda _: pytest.fail("ran a command"))
        monkeypatch.setattr("builtins.input", lambda _: "y")

        # Act
        code = langfuse.main(["reset"])

        # Assert
        assert code == 1
        assert (directory / ".env").exists()
        assert "langfuse_postgres_data" in capsys.readouterr().out

    def test_reset_removes_the_volumes_and_the_passwords_after_the_word(
        self, langfuse, tmp_path, monkeypatch
    ):
        # Arrange
        directory = tmp_path / "langfuse"
        directory.mkdir()
        (directory / "docker-compose.override.yml").write_text(OVERRIDE.read_text())
        (directory / ".env").write_text("POSTGRES_PASSWORD=kept\n")
        ran: list[list[str]] = []
        monkeypatch.setattr(langfuse, "run", lambda *_, **__: completed())
        monkeypatch.setattr(langfuse, "compose", lambda _: ["compose"])
        monkeypatch.setattr(langfuse, "passthrough", lambda cmd: ran.append(cmd) or 0)
        monkeypatch.setattr("builtins.input", lambda _: "delete")

        # Act
        code = langfuse.main(["reset"])

        # Assert
        assert code == 0
        assert ran == [["compose", "down", "--volumes"]]
        assert not (directory / ".env").exists()

    def test_down_keeps_the_volumes(self, langfuse, tmp_path, monkeypatch):
        directory = tmp_path / "langfuse"
        directory.mkdir()
        (directory / "docker-compose.override.yml").write_text(OVERRIDE.read_text())
        ran: list[list[str]] = []
        monkeypatch.setattr(langfuse, "compose", lambda _: ["compose"])
        monkeypatch.setattr(langfuse, "passthrough", lambda cmd: ran.append(cmd) or 0)

        langfuse.main(["down"])

        assert ran == [["compose", "down"]]

    @pytest.mark.parametrize("command", ["install", "up", "down", "status", "reset", "plugin"])
    def test_nothing_runs_inside_the_sandbox(self, langfuse, monkeypatch, capsys, command):
        # The sandbox closes the Docker socket, the plugin folder and the Keychain.
        monkeypatch.setenv("CLAUDE_SB_GUIDANCE", "/somewhere/agent-guidance.md")
        monkeypatch.setattr(langfuse, "run", lambda *_, **__: pytest.fail("ran a command"))
        monkeypatch.setattr(langfuse, "passthrough", lambda _: pytest.fail("ran a command"))

        code = langfuse.main([command])

        assert code == 1
        assert "normal terminal" in capsys.readouterr().err

    def test_up_without_an_install_says_how_to_get_one(self, langfuse, capsys):
        code = langfuse.main(["up"])

        assert code == 1
        assert "make langfuse-install" in capsys.readouterr().err

    def test_a_small_engine_is_a_warning_not_a_stop(self, langfuse, monkeypatch, capsys):
        monkeypatch.setattr(langfuse, "engine_memory_gib", lambda: 3.8)

        langfuse.require_engine()

        assert "3.8 GiB" in capsys.readouterr().out

    def test_no_engine_stops_with_the_command_to_start_one(self, langfuse, monkeypatch):
        monkeypatch.setattr(langfuse, "engine_memory_gib", lambda: None)

        with pytest.raises(langfuse.Stop, match="colima start"):
            langfuse.require_engine()


class TestDocs:
    def test_the_profile_lines_in_the_readme_are_the_ones_the_tool_prints(self, langfuse):
        readme = (REPO / "langfuse" / "README.md").read_text()

        for line in langfuse.PROFILE_LINES.splitlines():
            assert line in readme

    def test_each_key_is_exported_only_if_not_set_yet(self, langfuse):
        # A shell started inside claude-sb reads ~/.zprofile again; the Keychain read
        # fails there and would empty the key.
        for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
            line = next(ln for ln in langfuse.PROFILE_LINES.splitlines() if f"export {name}" in ln)
            assert line.startswith(f"[[ -z ${name} ]] && ")
            assert f"-s {name.lower().replace('_', '-')} " in line

    def test_every_make_target_is_in_the_readme(self):
        makefile = (REPO / "Makefile").read_text()
        readme = (REPO / "langfuse" / "README.md").read_text()

        targets = re.findall(r"^(langfuse-[a-z]+):", makefile, re.MULTILINE)

        assert len(targets) == 6
        assert [target for target in targets if f"make {target}" not in readme] == []
