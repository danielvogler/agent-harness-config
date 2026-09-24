#!/usr/bin/env python3
"""Validate the pin and the manifest overlay.

A bad overlay breaks the install for everyone in the team at once, and it breaks
it quietly — the installer just resolves fewer files. This runs as a pre-commit
hook so that never reaches `main`.

Always checked (no network, no `.ecc/` needed):
  1. upstream.json and overlay/manifest-overlay.json parse, and the pin is a full SHA.
  2. Every module the overlay adds has all schema-required fields and valid values.
  3. Every path an added module declares exists in this repo.
  4. Every module a profile names is either added by the overlay or expected upstream.
  5. Every skill in custom/skills/ has a SKILL.md whose `name` matches its directory.
  6. Every source in custom/skills/skills-lock.json has its license in THIRD_PARTY_LICENSES/.

Also checked when `.ecc/` has been materialized (`make plan` or `make install`):
  7. The resulting manifests validate against upstream's own JSON Schemas.
  8. Nothing the overlay removes or adds has drifted out of sync with upstream.
  9. No custom skill name collides with an upstream one — both install into the
     same directory, so a collision would silently shadow.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ECC = REPO / ".ecc"
LICENSES = REPO / "THIRD_PARTY_LICENSES"

REQUIRED_MODULE_FIELDS = {
    "id",
    "kind",
    "description",
    "paths",
    "targets",
    "dependencies",
    "defaultInstall",
    "cost",
    "stability",
}
VALID_KINDS = {
    "rules",
    "agents",
    "commands",
    "hooks",
    "platform",
    "orchestration",
    "skills",
    "docs",
}
VALID_TARGETS = {
    "claude",
    "claude-project",
    "cursor",
    "antigravity",
    "codex",
    "gemini",
    "opencode",
    "codebuddy",
    "joycode",
    "qwen",
    "zed",
    "hermes",
    "openclaw",
    "kimi",
}
VALID_COST = {"light", "medium", "heavy"}
VALID_STABILITY = {"experimental", "beta", "stable"}

errors: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"{path.name}: missing")
    except json.JSONDecodeError as exc:
        fail(f"{path.name}: invalid JSON — {exc}")
    return None


def keys(section: dict) -> set[str]:
    """Overlay sections use `$comment` keys for documentation; ignore them."""
    return {k for k in section if not k.startswith("$")}


def check_pin(pin: dict) -> None:
    up = pin.get("upstream", {})
    sha = up.get("sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        fail(f"upstream.json: sha must be a full 40-character commit hash, got {sha!r}")
    if not up.get("repo", "").startswith("https://"):
        fail("upstream.json: repo should be an https clone URL")
    if not up.get("pinnedOn"):
        fail("upstream.json: pinnedOn is required — it dates the last upstream review")


def check_overlay(overlay: dict) -> None:
    added = overlay.get("addModules", [])
    ids = [m.get("id") for m in added]

    for module in added:
        mid = module.get("id", "<unnamed>")
        # `$`-prefixed keys are ours; materialize.py strips them before the manifest.
        fields = {k for k in module if not k.startswith("$")}
        missing = REQUIRED_MODULE_FIELDS - fields
        if missing:
            fail(
                f"overlay: module {mid!r} is missing required field(s): {', '.join(sorted(missing))}"
            )
        extra = fields - REQUIRED_MODULE_FIELDS
        if extra:
            fail(f"overlay: module {mid!r} has unknown field(s): {', '.join(sorted(extra))}")

        src = module.get("$source")
        if src is None and module.get("paths"):
            # A cherry-pick module: no content of ours, just a selection of paths that
            # already exist in upstream's tree. This is how we take 4 skills out of a
            # 36-skill module without installing the other 32, and without copying
            # upstream files into custom/ where they would collide on name.
            if ECC.exists():
                for rel in module["paths"]:
                    if not (ECC / rel).exists():
                        fail(
                            f"overlay: module {mid!r} cherry-picks {rel!r}, which does not "
                            f"exist upstream. Re-check it against the pinned SHA."
                        )
            else:
                notes.append(
                    f"module {mid!r} cherry-picks upstream paths — not verified "
                    f"(run `make plan` to materialize .ecc/ first)"
                )
        elif not isinstance(src, dict) or not src.get("from") or not src.get("into"):
            fail(
                f"overlay: module {mid!r} needs either a $source with `from` and `into`, "
                f"or a non-empty `paths` list cherry-picking upstream content"
            )
        else:
            from_dir = REPO / src["from"]
            if not from_dir.is_dir():
                fail(f"overlay: module {mid!r} $source.from {src['from']!r} is not a directory")
            elif not [
                e
                for e in from_dir.iterdir()
                if e.name not in set(src.get("ignore", [])) and e.name != ".DS_Store"
            ]:
                fail(f"overlay: module {mid!r} $source.from {src['from']!r} is empty")
            # The adapters key off the *first* segment, so a subdirectory such as
            # rules/custom is fine — it is how we namespace away from upstream files.
            if src["into"].split("/")[0] not in {"skills", "commands", "rules", "agents"}:
                fail(
                    f"overlay: module {mid!r} $source.into is {src['into']!r}. It must start with "
                    f"one of ECC's own content directories (skills, commands, rules, agents), or "
                    f"the harness adapters will not remap it and the files install to a path "
                    f"nothing reads."
                )
        if not re.fullmatch(r"[a-z0-9-]+", mid):
            fail(f"overlay: module id {mid!r} must match ^[a-z0-9-]+$")
        if module.get("kind") not in VALID_KINDS:
            fail(f"overlay: module {mid!r} has invalid kind {module.get('kind')!r}")
        if module.get("cost") not in VALID_COST:
            fail(f"overlay: module {mid!r} has invalid cost {module.get('cost')!r}")
        if module.get("stability") not in VALID_STABILITY:
            fail(f"overlay: module {mid!r} has invalid stability {module.get('stability')!r}")
        for target in module.get("targets", []):
            if target not in VALID_TARGETS:
                fail(f"overlay: module {mid!r} targets unknown harness {target!r}")
        if not module.get("targets"):
            fail(f"overlay: module {mid!r} declares no targets")

    for dup in {i for i in ids if ids.count(i) > 1}:
        fail(f"overlay: duplicate module id {dup!r}")

    upstream_expected = {
        "rules-core",
        "agents-core",
        "commands-core",
        "hooks-runtime",
        "platform-configs",
        "framework-language",
        "database",
        "skill-unified-memory",
        "workflow-quality",
        "optimization-workflows",
        "security",
        "research-apis",
        "operator-workflows",
        "orchestration",
        "swift-apple",
        "agentic-patterns",
        "devops-infra",
        "machine-learning",
        "document-processing",
    }
    removed = keys(overlay.get("removeModules", {}))
    available = (upstream_expected - removed) | set(ids)

    for name, profile in overlay.get("addProfiles", {}).items():
        if not profile.get("modules"):
            fail(f"overlay: profile {name!r} lists no modules")
        for mid in profile.get("modules", []):
            if mid in removed:
                fail(f"overlay: profile {name!r} names {mid!r}, which the overlay also removes")
            elif mid not in available:
                fail(f"overlay: profile {name!r} names unknown module {mid!r}")


def check_custom_skills() -> None:
    root = REPO / "custom" / "skills"
    if not root.is_dir():
        fail("custom/skills/ is missing")
        return
    for skill in sorted(p for p in root.iterdir() if p.is_dir()):
        manifest = skill / "SKILL.md"
        if not manifest.exists():
            fail(f"custom/skills/{skill.name}/: no SKILL.md")
            continue
        head = manifest.read_text().split("---")
        if len(head) < 3:
            fail(f"custom/skills/{skill.name}/SKILL.md: no YAML frontmatter")
            continue
        match = re.search(r"^name:\s*(\S+)", head[1], re.MULTILINE)
        if not match:
            fail(f"custom/skills/{skill.name}/SKILL.md: frontmatter has no `name`")
        elif match.group(1) != skill.name:
            fail(
                f"custom/skills/{skill.name}/SKILL.md: frontmatter name is "
                f"{match.group(1)!r}, which must match the directory name"
            )


def check_third_party_licenses() -> None:
    lock = load(REPO / "custom" / "skills" / "skills-lock.json")
    if lock is None:
        return
    for source in sorted({s["source"] for s in lock.get("skills", {}).values()}):
        text = LICENSES / f"{source.replace('/', '-')}.txt"
        if not text.exists():
            fail(
                f"skills-lock.json: skills come from {source!r}, but "
                f"{text.relative_to(REPO)} is missing. Add its license text."
            )


def check_against_materialized(overlay: dict) -> None:
    if not (ECC / "manifests").is_dir():
        notes.append(
            "`.ecc/` not materialized — skipped schema and collision checks "
            "(run `make plan` to enable them)"
        )
        return

    modules_doc = load(ECC / "manifests" / "install-modules.json")
    if modules_doc is None:
        return
    present = {m["id"] for m in modules_doc["modules"]}
    added = {m["id"] for m in overlay.get("addModules", [])}

    # After materialize, removed ids must be gone and added ids must be present.
    for mid in sorted(keys(overlay.get("removeModules", {})) & present):
        fail(f".ecc/: module {mid!r} should have been removed by the overlay but is present")
    for mid in sorted(added - present):
        fail(f".ecc/: module {mid!r} should have been added by the overlay but is absent")

    try:
        import jsonschema
    except ImportError:
        notes.append("jsonschema not installed — skipped JSON Schema validation")
    else:
        pairs = [
            ("install-modules.json", "install-modules.schema.json"),
            ("install-profiles.json", "install-profiles.schema.json"),
            ("install-components.json", "install-components.schema.json"),
        ]
        for manifest, schema_name in pairs:
            doc = load(ECC / "manifests" / manifest)
            schema = load(ECC / "schemas" / schema_name)
            if doc is None or schema is None:
                continue
            validator = jsonschema.Draft7Validator(schema)
            for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
                where = "/".join(str(p) for p in err.path) or "(root)"
                fail(f".ecc/manifests/{manifest}: {where}: {err.message}")

    # Our content is copied into ECC's own skills/, commands/ and rules/ directories,
    # so any name we reuse would shadow upstream's file. Compare against upstream's
    # *pinned* tree, not the working tree — materialize.py has already copied ours in,
    # so the working tree would report every one of ours as colliding with itself.
    import subprocess

    def upstream_names(prefix: str) -> set[str] | None:
        try:
            out = subprocess.run(
                ["git", "ls-tree", "--name-only", f"HEAD:{prefix}"],
                cwd=ECC,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        return {line.strip() for line in out.splitlines() if line.strip()}

    for module in overlay.get("addModules", []):
        src = module.get("$source") or {}
        frm, into = src.get("from"), src.get("into")
        if not frm or not into:
            continue
        theirs = upstream_names(into)
        if theirs is None:
            # `into` may be a directory upstream does not have (e.g. rules/custom),
            # which is exactly the namespacing that avoids collisions.
            continue
        ignore = set(src.get("ignore", []))
        ours = {
            e.name for e in (REPO / frm).iterdir() if e.name not in ignore and e.name != ".DS_Store"
        }
        for name in sorted(ours & theirs):
            fail(
                f"{frm}/{name}: collides with upstream {into}/{name}. Ours is copied into "
                f"that same directory, so it would shadow upstream's — rename ours to "
                f"custom-{name}, or namespace the module under {into}/custom."
            )

    # ECC also ships .agents/skills/; a skill name colliding there shadows too.
    agents_skills = upstream_names(".agents/skills")
    if agents_skills:
        ours = {p.name for p in (REPO / "custom" / "skills").glob("*") if p.is_dir()}
        for name in sorted(ours & agents_skills):
            fail(f"custom/skills/{name}: collides with upstream .agents/skills/{name}")


def main() -> int:
    pin = load(REPO / "upstream.json")
    overlay = load(REPO / "overlay" / "manifest-overlay.json")
    if pin is None or overlay is None:
        print("validation failed:", *errors, sep="\n  - ", file=sys.stderr)
        return 1

    check_pin(pin)
    check_overlay(overlay)
    check_custom_skills()
    check_third_party_licenses()
    check_against_materialized(overlay)

    for note in notes:
        print(f"note: {note}", file=sys.stderr)

    if errors:
        print(f"validation failed ({len(errors)} problem(s)):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    skills = len([p for p in (REPO / "custom" / "skills").glob("*") if p.is_dir()])
    print(
        f"OK — pin {pin['upstream']['sha'][:10]}, "
        f"{len(overlay['addModules'])} modules added, "
        f"{len(keys(overlay['removeModules']))} removed, "
        f"{skills} custom skills"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
