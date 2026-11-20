#!/usr/bin/env python3
"""Find a repo's corporate design and propose its `.house-style.json`.

    python3 brand.py [--write]
    python3 brand.py --brand NAME [--write]

With --brand, the design comes from a named brand profile instead:
`${HOUSE_STYLE_BRANDS:-~/.config/house-style/brands}/NAME/brand.json` with its logo and mark
files. --write then copies the logo and mark into `docs/assets/brand/` and writes the
`.house-style.json`. Profiles live outside this skill, in the person's own repository.

Looks from the git root for a logo (`*logo*.svg|png`, `brand/`, `assets/brand*`), a mark
(`*mark*.svg`, `*symbol*.svg`, `favicon.svg`), an accent (a `--brand…` or `--accent` token
in the repo's CSS) and a font (`@font-face`). Prints the proposed entries; with --write it
writes `.house-style.json` at the git root, never over an existing one. Brand values only
ever come from the repo, never from this skill. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

SKIP = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".next", "site"}
MAX_DEPTH = 5
TOKEN = re.compile(r"--(?:brand[\w-]*|accent)\s*:\s*(#[0-9A-Fa-f]{6})\b")
FONT_FACE = re.compile(r"@font-face\s*\{[^}]*font-family\s*:\s*[\"']?([^\"';}]+)", re.S)


def git_root(start: Path) -> Path:
    for folder in [start.resolve(), *start.resolve().parents]:
        if (folder / ".git").exists():
            return folder
    return start.resolve()


def files(root: Path):
    """Every file under root up to MAX_DEPTH, skipping build and vendor folders."""
    stack = [(root, 0)]
    while stack:
        folder, depth = stack.pop()
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.name in SKIP or entry.name.startswith(".") and entry.name != ".github":
                continue
            if entry.is_dir() and depth < MAX_DEPTH:
                stack.append((entry, depth + 1))
            elif entry.is_file():
                yield entry


def _in_brand_folder(path: Path, root: Path) -> bool:
    parts = [p.lower() for p in path.relative_to(root).parts[:-1]]
    return any(p == "brand" or p.startswith("brand") for p in parts)


def detect(root: Path) -> dict:
    """The proposed `.house-style.json` entries, with the file each came from."""
    logo = mark = accent = font = None
    found: dict[str, str] = {}
    for path in files(root):
        name, rel = path.name.lower(), path.relative_to(root).as_posix()
        if path.suffix.lower() in (".svg", ".png"):
            if logo is None and ("logo" in name or (_in_brand_folder(path, root) and "mark" not in name)):
                logo = rel
            if mark is None and path.suffix.lower() == ".svg" and ("mark" in name or "symbol" in name):
                mark = rel
            if name == "favicon.svg" and mark is None:
                found["favicon"] = rel
        elif path.suffix.lower() in (".css", ".scss") and path.stat().st_size < 2_000_000:
            text = path.read_text(errors="ignore")
            if accent is None and (m := TOKEN.search(text)):
                accent, found["accent"] = m.group(1).upper(), rel
            if font is None and (m := FONT_FACE.search(text)):
                font, found["font"] = m.group(1).strip(), rel
    mark = mark or found.pop("favicon", None)
    proposal: dict = {}
    if accent:
        proposal["accent"] = accent
    if font:
        proposal["font"] = font
    visual = {k: v for k, v in (("logo", logo), ("mark", mark)) if v}
    if visual:
        proposal["visual"] = visual
    return {"proposal": proposal, "sources": found}


PROFILE_KEYS = {"name", "accent", "accent_dark", "font", "font_file", "fade", "fade_dark", "ramp",
                "logo", "logo_dark", "mark"}
BRAND_DIR = "docs/assets/brand"


def brands_home() -> Path:
    return Path(os.environ.get("HOUSE_STYLE_BRANDS") or Path.home() / ".config" / "house-style" / "brands")


def from_profile(name: str) -> tuple[dict, dict[str, Path]]:
    """The `.house-style.json` a named brand profile gives, and the files to copy into the repo."""
    folder = brands_home() / name
    path = folder / "brand.json"
    if not path.is_file():
        known = sorted(p.parent.name for p in brands_home().glob("*/brand.json"))
        sys.exit(f"no brand profile {name!r} in {brands_home()}; known: {known or 'none'}")
    data = json.loads(path.read_text())
    unknown = set(data) - PROFILE_KEYS
    if unknown:
        sys.exit(f"{path}: unknown keys {sorted(unknown)}; allowed: {sorted(PROFILE_KEYS)}")
    config: dict = {k: data[k] for k in ("accent", "accent_dark", "font") if k in data}
    visual: dict = {k: data[k] for k in ("fade", "fade_dark", "ramp") if k in data}
    copies: dict[str, Path] = {}
    for key in ("logo", "logo_dark", "mark", "font_file"):
        if key in data:
            src = folder / data[key]
            if not src.is_file():
                sys.exit(f"{path}: {key} file {src} is missing")
            name = "logo-dark" if key == "logo_dark" else "font" if key == "font_file" else key
            dest = f"{BRAND_DIR}/{name}{src.suffix.lower()}"
            visual[key], copies[dest] = dest, src
    if visual:
        config["visual"] = visual
    return config, copies


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write .house-style.json at the git root")
    parser.add_argument("--brand", help="take the design from this named brand profile")
    args = parser.parse_args(argv)
    root = git_root(Path.cwd())
    existing = palette.find_override(Path.cwd())
    if existing:
        print(f"{existing} exists; it decides the brand")
        return 0
    if args.brand:
        config, copies = from_profile(args.brand)
        print(json.dumps(config, indent=2))
        if args.write:
            for dest, src in copies.items():
                (root / dest).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, root / dest)
            (root / palette.OVERRIDE_FILE).write_text(json.dumps(config, indent=2) + "\n")
            print(f"wrote {root / palette.OVERRIDE_FILE} and {len(copies)} brand files")
        return 0
    result = detect(root)
    proposal = result["proposal"]
    if not proposal:
        print("no brand found: the neutral default and a text wordmark")
        return 0
    print(json.dumps(proposal, indent=2))
    for key, source in result["sources"].items():
        print(f"  {key} from {source}")
    if args.write:
        (root / palette.OVERRIDE_FILE).write_text(json.dumps(proposal, indent=2) + "\n")
        print(f"wrote {root / palette.OVERRIDE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
