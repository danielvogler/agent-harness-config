#!/usr/bin/env python3
"""Copy the starter stylesheet (and optionally the example page) into a project.

    python3 starter.py <out-dir> [--example]

Writes <out-dir>/starter.css. Its own values are the look in references/look.md; the
colours the nearest `.house-style.json` sets (accent, accent_dark, paper, ink, paper_dark,
ink_dark, font, visual.fade, visual.fade_dark, visual.ramp, visual.font_file; found from
the working directory up to the git root) replace them in both blocks. A red or amber
accent turns "good" to ink and, without a ramp of its own, the ramp to the fade's deep
stop. The dark tokens are written once; a copy under :root[data-theme="dark"] at the end
serves pages with a theme toggle. With --example it also writes <out-dir>/example.html to
start a page from. Standard library only.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand  # noqa: E402
import palette  # noqa: E402
import report  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"


TOGGLE_START = "/* theme toggle: the dark tokens above, for <html data-theme=\"dark\">; written by starter.py */"
TOGGLE_END = "/* end theme toggle */"
DARK_RULE = re.compile(r'@media \(prefers-color-scheme: dark\) \{\n  (:root:not\(\[data-theme="light"\]\)(?: \*)?) \{\n(.*?)\n  \}\n\}', re.S)


def theme_toggle(css: str) -> str:
    """Copy every dark token block under :root[data-theme="dark"], replacing an older copy."""
    css = re.sub(re.escape(TOGGLE_START) + r".*?" + re.escape(TOGGLE_END) + r"\n?", "", css, flags=re.S)
    blocks = []
    for selector, body in DARK_RULE.findall(css):
        target = selector.replace(':not([data-theme="light"])', '[data-theme="dark"]')
        blocks.append(target + " {\n" + body.replace("\n    ", "\n  ").replace("    ", "  ", 1) + "\n}")
    return css.rstrip("\n") + "\n" + TOGGLE_START + "\n" + "\n".join(blocks) + "\n" + TOGGLE_END + "\n"


def collides(hex_colour: str) -> bool:
    """A red or amber accent: it would read as a warning, so good turns ink."""
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return sat > .4 and .15 < light < .85 and (hue * 360 <= 50 or hue * 360 >= 335)


def apply_override(css: str, root: Path | None = None) -> str:
    """Put the colours the repo's .house-style.json sets into both blocks; keep the rest."""
    path = palette.find_override(root or Path.cwd())
    if path is None:
        return css
    themes = palette.load(root)
    keys = json.loads(path.read_text())
    light, dark = css.split(report.DARK_BLOCK, 1)
    for key, (theme, name) in palette.OVERRIDE_KEYS.items():
        if key not in keys:
            continue
        pattern, value = rf"--{name}: #[0-9A-Fa-f]{{6}};", f"--{name}: {themes[theme][name]};"
        if theme == "light":
            light = re.sub(pattern, value, light, count=1)
        else:
            dark = re.sub(pattern, value, dark, count=1)
    visual = keys.get("visual") or {}
    fade = visual.get("fade")
    if fade:
        stops = ", ".join(fade)
        light = re.sub(r"--fade: [^;]+;", lambda _: f"--fade: linear-gradient(90deg, {stops});", light, count=1)
        light = re.sub(r"--fade-v: [^;]+;", lambda _: f"--fade-v: linear-gradient(180deg, {stops});", light, count=1)
        if len(fade) == 3:
            # numbers take the fade's middle stop: solid, and the brand's own deeper accent
            middle = fade[1].split()[0]
            light = re.sub(r"--num: [^;]+;", lambda _: f"--num: {middle};", light, count=1)
    fade_dark = visual.get("fade_dark")
    if fade_dark:
        stops = ", ".join(fade_dark)
        dark = re.sub(r"--fade: [^;]+;", lambda _: f"--fade: linear-gradient(90deg, {stops});", dark, count=1)
        dark = re.sub(r"--fade-v: [^;]+;", lambda _: f"--fade-v: linear-gradient(180deg, {stops});", dark, count=1)
        if len(fade_dark) == 3:
            dark = re.sub(r"--num: [^;]+;", lambda _: f"--num: {fade_dark[1].split()[0]};", dark, count=1)
    red = collides(themes["light"]["accent"])
    ramp = visual.get("ramp") or (fade[-1].split()[0] if red and fade and len(fade) == 3 else None)
    if ramp:
        light = re.sub(r"--ramp: [^;]+;", lambda _: f"--ramp: {ramp};", light, count=1)
    if red:
        light = re.sub(r"--ok: [^;]+; --ok-bg: [^;]+;", "--ok: var(--ink); --ok-bg: var(--sunk);", light, count=1)
    if "font" in keys:
        light = re.sub(r"--font: [^;]+;", lambda _: f"--font: {themes['font']};", light, count=1)
    font_file = visual.get("font_file")
    if font_file and "font" in keys:
        face = (f'@font-face {{ font-family: "{keys["font"]}"; src: url("{palette.esc(font_file)}") format("woff2"); '
                f'font-weight: 100 900; font-display: swap; }}\n')
        light = re.sub(r"(\*/\n)", lambda m: m.group(1) + face, light, count=1)
    return light + report.DARK_BLOCK + dark


DEFAULT_MARK = re.compile(r'(<span class="face mark"><svg viewBox="0 0 16 16" aria-hidden="true"><path d=")([^"]+)(")')


def brand_example(html: str, root: Path | None = None) -> str:
    """Put the repo's logo into the header and its mark into the item faces."""
    path = palette.find_override(root or Path.cwd())
    visual = (json.loads(path.read_text()).get("visual") or {}) if path else {}
    logo, logo_dark, mark = visual.get("logo"), visual.get("logo_dark"), visual.get("mark")
    if logo:
        imgs = (f'<img class="on-light" src="{palette.esc(logo)}" alt="">'
                f'<img class="on-dark" src="{palette.esc(logo_dark)}" alt="">' if logo_dark
                else f'<img src="{palette.esc(logo)}" alt="">')
        html = re.sub(r'<span class="word">[^<]*</span>', lambda _: imgs, html, count=1)
    if mark and re.match(r"^[Mm][\d\s.,MmLlHhVvCcSsQqTtAaZz-]+$", mark):
        html = DEFAULT_MARK.sub(lambda m: m.group(1) + palette.esc(mark) + m.group(3), html)
    elif mark:
        html = re.sub(r'<span class="face mark"><svg[^>]*>.*?</svg></span>',
                      f'<span class="face mark"><img src="{palette.esc(mark)}" alt=""></span>', html)
    return html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, help="folder to write starter.css into")
    parser.add_argument("--example", action="store_true", help="also write example.html")
    parser.add_argument("--detect-brand", action="store_true",
                        help="without a .house-style.json, find the repo's logo, mark, accent and font and write one")
    args = parser.parse_args(argv)
    if args.detect_brand:
        brand.main(["--write"])
    css = theme_toggle(apply_override((ASSETS / "starter.css").read_text()))
    font_file = ((json.loads(path.read_text()).get("visual") or {}).get("font_file")
                 if (path := palette.find_override(Path.cwd())) else None)
    if font_file:
        # the stylesheet sits in <out>; the font path in .house-style.json is from the repo root
        rel = os.path.relpath(path.parent / font_file, args.out.resolve())
        css = css.replace(f'url("{palette.esc(font_file)}")', f'url("{palette.esc(rel)}")', 1)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "starter.css").write_text(css)
    if args.example:
        (args.out / "example.html").write_text(brand_example((ASSETS / "example.html").read_text()))
        (args.out / "chips.js").write_text((ASSETS / "chips.js").read_text())
    print(f"wrote {args.out / 'starter.css'}" + (", example.html and chips.js" if args.example else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
