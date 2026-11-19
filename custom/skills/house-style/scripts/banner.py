#!/usr/bin/env python3
"""Write a README banner pair, docs/assets/banner-light.svg and banner-dark.svg.

    python3 banner.py --title agent-harness --suffix=-config \
        --eyebrow "Shared agent config" \
        --description "One agent config, installed into every coding harness you use." \
        --footer "Pinned upstream plus the team's own skills. One make install." \
        --side-label "This repo" --side-chip "make install" --side-note "one command" \
        --side-item "Claude Code" --side-item Codex --side-item opencode

Colours come from the repo's `.house-style.json` when there is one. Standard library only.
Exits 1, after writing, when a line is estimated not to fit; render and look either way.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# No __pycache__ beside the scripts: the skill folder is copied into installs as it is.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

WIDTH, HEIGHT = 1200, 340
LEFT = 72
SIDE_X = 800
RIGHT_MARGIN = 40
MAX_SIDE_ITEMS = 6
ITEM_GAP = 45
FAN_Y = 185
TITLE_SIZES = range(62, 38, -2)
DESCRIPTION_SIZES = (25, 22, 20)


def fit_title(title: str, suffix: str, width: float) -> tuple[int, bool]:
    for size in TITLE_SIZES:
        spacing = -size * 0.042
        used = palette.text_width(title + ".", size, True, spacing)
        used += palette.text_width(suffix, size, False, spacing)
        if used <= width:
            return size, True
    return TITLE_SIZES[-1], False


def fit_description(text: str, width: float) -> tuple[int, list[str], bool]:
    for size in DESCRIPTION_SIZES:
        lines = palette.balanced(text, size, width)
        if len(lines) <= 2:
            return size, lines, True
    return DESCRIPTION_SIZES[-1], lines[:2], False


def side_block(args, c: dict, font: str, warnings: list[str]) -> list[str]:
    items = args.side_item or []
    if len(items) > MAX_SIDE_ITEMS:
        sys.exit(f"at most {MAX_SIDE_ITEMS} --side-item values fit, got {len(items)}")
    out: list[str] = [f'<g font-family="{font}">']
    if args.side_label:
        out.append(
            f'<text x="{SIDE_X}" y="150" font-size="12" font-weight="600" letter-spacing="1.6" '
            f'fill="{c["faint"]}">{palette.esc(args.side_label.upper())}</text>'
        )
    dot_x = SIDE_X + 6
    if args.side_chip:
        chip_w = max(120, round(palette.mono_width(args.side_chip, 15) + 44))
        out.append(
            f'<rect x="{SIDE_X}" y="163" width="{chip_w}" height="44" rx="22" fill="{c["ink"]}"/>'
        )
        out.append(
            f'<text x="{SIDE_X + chip_w / 2:g}" y="190" font-family="{palette.MONO}" font-size="15" '
            f'font-weight="600" text-anchor="middle" fill="{c["paper"]}">'
            f"{palette.esc(args.side_chip)}</text>"
        )
        for i, line in enumerate(palette.balanced(args.side_note or "", 13, chip_w + 20)[:2]):
            out.append(
                f'<text x="{SIDE_X}" y="{232 + 18 * i}" font-size="13" fill="{c["faint"]}">'
                f"{palette.esc(line)}</text>"
            )
        dot_x = SIDE_X + chip_w + 58
    out.append("</g>")
    if not items:
        return out

    top = FAN_Y - ITEM_GAP * (len(items) - 1) / 2
    ys = [top + ITEM_GAP * i for i in range(len(items))]
    if args.side_chip:
        start = dot_x - 58
        out.append(
            f'<g fill="none" stroke="{c["stroke"]}" stroke-width="1.6" stroke-linecap="round">'
        )
        for y in ys:
            out.append(
                f'<path d="M {start} {FAN_Y} C {start + 33} {FAN_Y}, {start + 23} {y:g}, '
                f'{dot_x - 6} {y:g}"/>'
            )
        out.append("</g>")
    out.append("<g>")
    out += [f'<circle cx="{dot_x}" cy="{y:g}" r="4.5" fill="{c["accent"]}"/>' for y in ys]
    out.append("</g>")
    out.append(f'<g font-family="{font}" font-size="16" font-weight="600" fill="{c["ink"]}">')
    room = WIDTH - RIGHT_MARGIN + 10 - (dot_x + 16)
    for item, y in zip(items, ys, strict=True):
        if palette.text_width(item, 16, True) > room:
            warnings.append(f"side item {item!r} is wider than the {room:.0f}px left for it")
        out.append(f'<text x="{dot_x + 16}" y="{y + 5.5:g}">{palette.esc(item)}</text>')
    out.append("</g>")
    return out


def render(args, c: dict, font: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    has_side = bool(args.side_item or args.side_chip)
    column = (SIDE_X - 40 if has_side else WIDTH - RIGHT_MARGIN) - LEFT
    size, title_fits = fit_title(args.title, args.suffix, column)
    if not title_fits:
        warnings.append(f"title does not fit {column}px even at {size}px; shorten it")
    desc_size, desc_lines, desc_fits = fit_description(args.description, column)
    if not desc_fits:
        warnings.append("description needs more than two lines; shorten it")
    if args.footer and palette.text_width(args.footer, 14) > column + (360 if has_side else 0):
        warnings.append("footer is wider than the banner; shorten it")

    label = palette.esc(f"{args.title}{args.suffix} — {args.description}")
    title = palette.esc(args.title + args.suffix)
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{label}">',
        f"<title>{title}</title>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{c["paper"]}"/>',
        f'<rect y="{HEIGHT - 1}" width="{WIDTH}" height="1" fill="{c["line"]}"/>',
        f'<g font-family="{font}">',
    ]
    if args.eyebrow:
        o.append(f'<circle cx="{LEFT}" cy="74" r="4" fill="{c["accent"]}"/>')
        o.append(
            f'<text x="{LEFT + 16}" y="79" font-size="14" font-weight="600" letter-spacing="2.2" '
            f'fill="{c["muted"]}">{palette.esc(args.eyebrow.upper())}</text>'
        )
    o.append(
        f'<text x="{LEFT - 2}" y="172" font-size="{size}" letter-spacing="{-size * 0.042:.1f}">'
        f'<tspan fill="{c["ink"]}" font-weight="700">{palette.esc(args.title)}</tspan>'
        f'<tspan fill="{c["muted"]}" font-weight="400">{palette.esc(args.suffix)}</tspan>'
        f'<tspan fill="{c["accent"]}" font-weight="700">.</tspan></text>'
    )
    for i, line in enumerate(desc_lines):
        o.append(
            f'<text x="{LEFT}" y="{232 + 36 * i}" font-size="{desc_size}" fill="{c["muted"]}">'
            f"{palette.esc(line)}</text>"
        )
    if args.footer:
        o.append(
            f'<text x="{LEFT}" y="312" font-size="14" fill="{c["faint"]}">'
            f"{palette.esc(args.footer)}</text>"
        )
    o.append("</g>")
    if has_side:
        o += side_block(args, c, font, warnings)
    o.append("</svg>")
    return "\n".join(o) + "\n", warnings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--title", required=True, help="the name, in ink")
    p.add_argument(
        "--suffix",
        default="",
        help="the tail of the name, in muted grey (write --suffix=-x when it starts with -)",
    )
    p.add_argument("--description", required=True, help="one line on what it does")
    p.add_argument("--eyebrow", help="small capitals above the title")
    p.add_argument("--footer", help="faint line at the bottom")
    p.add_argument("--side-label", help="small capitals over the right-hand column")
    p.add_argument("--side-chip", help="a command or name in a dark pill, fanning out")
    p.add_argument("--side-note", help="faint text under the chip")
    p.add_argument("--side-item", action="append", help="one per item on the right (max 6)")
    p.add_argument("--out", type=Path, default=Path("docs/assets"), help="output folder")
    p.add_argument(
        "--root", type=Path, default=Path.cwd(), help="where to look for .house-style.json"
    )
    args = p.parse_args(argv)

    themes = palette.load(args.root)
    args.out.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    for theme in ("light", "dark"):
        svg, warnings = render(args, themes[theme], themes["font"])
        path = args.out / f"banner-{theme}.svg"
        path.write_text(svg)
        print(f"wrote {path}")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
