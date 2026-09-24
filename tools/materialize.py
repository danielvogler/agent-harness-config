#!/usr/bin/env python3
"""Build the install tree: upstream ECC at the pinned SHA, plus our content.

This repo holds the pin and our own config, not a copy of ECC. ECC's installer
resolves module `paths` relative to its own repo root, so at install time we
materialize a tree that looks like a fork would have looked:

    .ecc/                     <- ECC cloned at upstream.json's sha (gitignored)
    .ecc/custom/              <- our custom/ copied in
    .ecc/manifests/*.json     <- upstream manifests + overlay/manifest-overlay.json

Then `.ecc/install.sh --profile custom` fans everything out to every harness.

Doing it this way rather than forking means bumping upstream is a one-line SHA
edit in upstream.json, and never a merge conflict.

Usage:
    python3 tools/materialize.py            # clone/checkout, copy, apply overlay
    python3 tools/materialize.py --check    # report what would happen, change nothing
    python3 tools/materialize.py --ecc-dir DIR --skip-clone
                                            # apply to an existing tree (used by tests)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(cmd)}\n{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"missing: {path.relative_to(REPO)}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path.relative_to(REPO)}: {exc}") from None


def clone_or_update(ecc_dir: Path, repo_url: str, sha: str, check: bool) -> None:
    """Get ecc_dir to exactly `sha`, cloning it first if it isn't there yet."""
    if ecc_dir.exists() and (ecc_dir / ".git").exists():
        current = run(["git", "rev-parse", "HEAD"], cwd=ecc_dir)
        if current == sha:
            print(f"  .ecc/ already at {sha[:10]}")
            return
        print(f"  .ecc/ is at {current[:10]}, moving to {sha[:10]}")
        if check:
            return
        run(["git", "fetch", "--quiet", "origin", sha], cwd=ecc_dir)
        run(["git", "checkout", "--quiet", "--force", sha], cwd=ecc_dir)
        run(["git", "clean", "-qfdx", "--exclude=node_modules"], cwd=ecc_dir)
        return

    print(f"  cloning {repo_url} at {sha[:10]}")
    if check:
        return
    if ecc_dir.exists():
        shutil.rmtree(ecc_dir)
    # Blobless clone: full history for the SHA fetch, blobs only as needed.
    run(["git", "clone", "--quiet", "--filter=blob:none", repo_url, str(ecc_dir)])
    run(["git", "checkout", "--quiet", "--force", sha], cwd=ecc_dir)


def restore_pristine(ecc_dir: Path, check: bool) -> None:
    """Undo a previous overlay run.

    The overlay is a patch against upstream's manifests, so it has to be applied to
    upstream's manifests — not to the result of the last run. Without this, a second
    `make install` fails the staleness check, because the modules it wants to remove
    were already removed.
    """
    if not (ecc_dir / ".git").exists():
        return
    print("  restoring upstream tree to its pinned state")
    if check:
        return
    # Paths upstream tracks: restore their pinned content, then sweep whatever we copied
    # in alongside it (checkout does not remove untracked files).
    tracked = ["manifests", "mcp-configs", "skills", "commands", "rules"]
    run(["git", "checkout", "--force", "HEAD", "--", *tracked], cwd=ecc_dir)

    # Paths upstream has never tracked, so `git checkout` would fail on the pathspec —
    # clean only. `custom` is a leftover: an early build copied custom/ in wholesale before
    # the path fix, nothing has referenced it since, and nothing was removing it, so it sat
    # in .ecc/ accumulating stale duplicates and padding the untracked count an editor
    # shows for the inner clone.
    untracked_only = ["custom"]
    run(["git", "clean", "-qfd", "--", *tracked, *untracked_only], cwd=ecc_dir)


def place_custom(ecc_dir: Path, overlay: dict, check: bool) -> dict[str, list[str]]:
    """Copy our content into ECC's own skills/, commands/ and rules/ directories.

    It must go there, not into a `custom/` directory of its own. Each harness
    adapter remaps only the paths it recognises — `claude-home.js`, for instance,
    remaps `skills/...` to `~/.claude/skills/` and `rules/...` to
    `~/.claude/rules/ecc/`. Anything else falls through a passthrough that keeps
    the relative path, so a module declaring `custom/skills` installs to
    `~/.claude/custom/skills/`, which no harness ever reads. The install looks
    like it worked and nothing is discoverable.

    Returns {module id: [repo-relative paths]} for the manifest to declare.
    """
    generated: dict[str, list[str]] = {}

    for module in overlay["addModules"]:
        spec = module.get("$source")
        if spec is None:
            # Cherry-pick module: the paths already exist in upstream's tree, so there is
            # nothing to copy. Declaring them is the whole job — it is how a handful of
            # skills from a 36-skill module get installed without the other 32, and
            # without duplicating upstream files under a colliding name.
            generated[module["id"]] = list(module["paths"])
            print(f"  cherry-pick -> {module['id']} ({len(module['paths'])} path(s))")
            continue
        src = REPO / spec["from"]
        dest_root = ecc_dir / spec["into"]
        ignore = set(spec.get("ignore", []))

        entries = sorted(e for e in src.iterdir() if e.name not in ignore and e.name != ".DS_Store")
        paths = [f"{spec['into']}/{e.name}" for e in entries]
        generated[module["id"]] = paths
        print(f"  {spec['from']}/ -> .ecc/{spec['into']}/ ({len(entries)} entries)")

        if check:
            continue

        dest_root.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            target = dest_root / entry.name
            if target.exists():
                # The collision check in validate-manifests.py should have caught
                # this. Refuse rather than silently shadow upstream content.
                raise SystemExit(
                    f"refusing to overwrite upstream {spec['into']}/{entry.name} "
                    f"with {spec['from']}/{entry.name} — rename ours to custom-{entry.name}"
                )
            if entry.is_dir():
                shutil.copytree(entry, target, ignore=shutil.ignore_patterns(".DS_Store"))
            else:
                shutil.copy2(entry, target)

    return generated


def apply_overlay(
    ecc_dir: Path, overlay: dict, generated: dict[str, list[str]], check: bool
) -> None:
    remove = {k: v for k, v in overlay["removeModules"].items() if not k.startswith("$")}
    add_modules = []
    for module in overlay["addModules"]:
        entry = {k: v for k, v in module.items() if not k.startswith("$")}
        entry["paths"] = generated[module["id"]]
        if not entry["paths"]:
            raise SystemExit(
                f"module {module['id']!r} resolved to no paths — "
                f"{module['$source']['from']}/ is empty"
            )
        add_modules.append(entry)
    add_profiles = overlay["addProfiles"]
    drop_servers = {k for k in overlay["removeMcpServers"] if not k.startswith("$")}
    add_servers = {
        k: v for k, v in overlay.get("addMcpServers", {}).items() if not k.startswith("$")
    }

    manifests = ecc_dir / "manifests"

    # --- modules ---
    path = manifests / "install-modules.json"
    doc = load_json(path)
    known = {m["id"] for m in doc["modules"]}
    unknown = sorted(set(remove) - known)
    if unknown:
        raise SystemExit(
            "overlay is stale: removeModules names modules that no longer exist upstream: "
            + ", ".join(unknown)
            + "\nRe-check the overlay against the new SHA."
        )
    clashing = sorted({m["id"] for m in add_modules} & known)
    if clashing:
        raise SystemExit(
            "overlay collides with upstream: addModules re-uses existing module ids: "
            + ", ".join(clashing)
        )
    doc["modules"] = [m for m in doc["modules"] if m["id"] not in remove]
    for module in doc["modules"]:
        module["dependencies"] = [d for d in module["dependencies"] if d not in remove]
    doc["modules"].extend(add_modules)
    print(f"  modules: -{len(remove)} +{len(add_modules)} -> {len(doc['modules'])}")
    if not check:
        path.write_text(json.dumps(doc, indent=2) + "\n")

    # --- profiles: prune dead references, then add ours ---
    path = manifests / "install-profiles.json"
    doc = load_json(path)
    for profile in doc["profiles"].values():
        kept = [m for m in profile["modules"] if m not in remove]
        if not kept:
            kept = ["rules-core"]
        profile["modules"] = kept
    doc["profiles"].update(add_profiles)
    print(f"  profiles: +{len(add_profiles)} -> {len(doc['profiles'])}")
    if not check:
        path.write_text(json.dumps(doc, indent=2) + "\n")

    # --- components: prune dead references, drop any left empty ---
    path = manifests / "install-components.json"
    doc = load_json(path)
    before = len(doc["components"])
    components = []
    for component in doc["components"]:
        component["modules"] = [m for m in component["modules"] if m not in remove]
        if component["modules"]:
            components.append(component)
    doc["components"] = components
    print(f"  components: {before} -> {len(components)}")
    if not check:
        path.write_text(json.dumps(doc, indent=2) + "\n")

    # --- files dropped from the materialized tree ---
    # Modules install whole directories (rules-core is paths: ["rules"]), so there is no
    # per-file switch in the manifests. Deleting here is the only lever. Every .md under
    # ~/.claude/rules/ is loaded as an instruction in every session, so a README shipped
    # in that tree is documentation billed as context to every person, forever.
    drop_files = [k for k in overlay.get("removeFiles", {}) if not k.startswith("$")]
    dropped = []
    for rel in drop_files:
        target = ecc_dir / rel
        if not target.exists():
            raise SystemExit(
                f"removeFiles names a path that is not in the materialized tree: {rel}\n"
                "Upstream may have moved or deleted it — check before the next pin bump."
            )
        dropped.append(rel)
        if not check:
            target.unlink()
    if drop_files:
        print(f"  files dropped: {len(dropped)} ({', '.join(dropped)})")

    # --- MCP servers ---
    path = ecc_dir / "mcp-configs" / "mcp-servers.json"
    doc = load_json(path)
    removed = [k for k in drop_servers if k in doc["mcpServers"]]
    for key in removed:
        del doc["mcpServers"][key]
    comments = doc.get("_comments")
    if isinstance(comments, dict):
        for key in [k for k in comments if any(s in k for s in drop_servers)]:
            del comments[key]

    # Symmetric with removeModules' staleness guard: refuse to shadow a server upstream
    # already ships rather than silently replacing whatever it configured.
    clashing = sorted(set(add_servers) & set(doc["mcpServers"]))
    if clashing:
        raise SystemExit(
            "overlay collides with upstream: addMcpServers re-uses existing server ids: "
            + ", ".join(clashing)
            + "\nRename ours, or remove it in removeMcpServers first."
        )
    doc["mcpServers"].update(add_servers)

    # The activation list names ids the team actually runs, from either side of the merge.
    # Validate here so a typo or an upstream rename fails the build rather than silently
    # activating nothing when someone runs `make mcp`.
    activate = overlay.get("activateMcpServers", {}).get("ids", [])
    unknown = [s for s in activate if s not in doc["mcpServers"]]
    if unknown:
        raise SystemExit(
            "activateMcpServers names servers that are not in the merged catalog: "
            + ", ".join(unknown)
            + "\nAdd them under addMcpServers, or fix the id."
        )

    print(
        f"  mcp servers: -{len(removed)} +{len(add_servers)} -> {len(doc['mcpServers'])}"
        f" ({len(activate)} activated by `make mcp`)"
    )
    if not check:
        path.write_text(json.dumps(doc, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report only, change nothing")
    parser.add_argument("--ecc-dir", default=str(REPO / ".ecc"))
    parser.add_argument("--skip-clone", action="store_true", help="use the tree as it is")
    args = parser.parse_args()

    pin = load_json(REPO / "upstream.json")["upstream"]
    overlay = load_json(REPO / "overlay" / "manifest-overlay.json")
    ecc_dir = Path(args.ecc_dir).resolve()

    print(f"upstream: {pin['repo']} @ {pin['sha'][:10]} (pinned {pin['pinnedOn']})")
    if not args.skip_clone:
        clone_or_update(ecc_dir, pin["repo"], pin["sha"], args.check)
    if not (ecc_dir / "manifests").exists():
        if args.check:
            print("  (nothing materialized yet)")
            return 0
        raise SystemExit(f"{ecc_dir} does not look like an ECC checkout")

    restore_pristine(ecc_dir, args.check)
    generated = place_custom(ecc_dir, overlay, args.check)
    apply_overlay(ecc_dir, overlay, generated, args.check)

    print("ready:", "would install from" if args.check else "install from", ecc_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
