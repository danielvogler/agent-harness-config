#!/usr/bin/env python3
"""Fill templates/report.html from a markdown file: one self-contained HTML page.

    uv run --with markdown python3 report.py notes.md -o report.html --eyebrow "Audit"

Markdown needs the `markdown` package, hence `uv run --with markdown`; everything else is
standard library. The first `# heading` becomes the title. Colours come from the repo's
`.house-style.json` when there is one. Raw HTML passes through, so a status chip is
`<span class="chip live">live</span>` (also planned, choose, blocked).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# No __pycache__ beside the scripts: the skill folder is copied into installs as it is.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "report.html"
DARK_BLOCK = "@media (prefers-color-scheme: dark)"
CSS_VARS = ("paper", "ink", "muted", "faint", "line", "surface", "accent")


def apply_palette(html: str, themes: dict) -> str:
    """Rewrite the CSS variables of the light and the dark block from the palette."""
    light, dark = html.split(DARK_BLOCK, 1)
    for name in CSS_VARS:
        light = re.sub(
            rf"--{name}: #[0-9A-Fa-f]{{6}};", f"--{name}: {themes['light'][name]};", light, count=1
        )
        dark = re.sub(
            rf"--{name}: #[0-9A-Fa-f]{{6}};", f"--{name}: {themes['dark'][name]};", dark, count=1
        )
    light = re.sub(r"--font: [^;]+;", lambda _: f"--font: {themes['font']};", light, count=1)
    return light + DARK_BLOCK + dark


def fill(html: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        html = html.replace("{{" + key + "}}", value)
    return html


def convert(text: str) -> tuple[str, str, str]:
    """(title, body html, contents html) from markdown."""
    try:
        import markdown
    except ImportError:
        sys.exit(
            "report.py needs the markdown package: uv run --with markdown python3 report.py ..."
        )
    title = ""
    match = re.search(r"^# (.+)$", text, re.M)
    if match:
        title = match.group(1).strip()
        text = text[: match.start()] + text[match.end() :]
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc"], extension_configs={"toc": {"toc_depth": "2-3"}}
    )
    body = md.convert(text)
    return title, body, md.toc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("source", type=Path, help="markdown file")
    p.add_argument("-o", "--output", type=Path, help="default: the source with .html")
    p.add_argument("--title", help="default: the first # heading")
    p.add_argument("--eyebrow", default="Report", help="small capitals above the title")
    p.add_argument("--footer", help=f"default: the date, {date.today():%Y-%m-%d}")
    p.add_argument(
        "--root", type=Path, default=Path.cwd(), help="where to look for .house-style.json"
    )
    args = p.parse_args(argv)

    title, body, toc = convert(args.source.read_text())
    html = apply_palette(TEMPLATE.read_text(), palette.load(args.root))
    html = fill(
        html,
        {
            "title": palette.esc(args.title or title or args.source.stem),
            "eyebrow": palette.esc(args.eyebrow),
            "footer": palette.esc(args.footer or f"{date.today():%Y-%m-%d}"),
            "toc": toc,
            "body": body,
        },
    )
    out = args.output or args.source.with_suffix(".html")
    out.write_text(html)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
