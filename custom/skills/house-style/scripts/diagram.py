#!/usr/bin/env python3
"""Draw the architecture picture, an SVG pair, from a small data description.

    python3 diagram.py docs/assets/architecture.py      # a file defining DIAGRAM = {...}
    python3 diagram.py architecture.json --out docs/assets

Tiles sit on a grid (`col`, `row`); a zone is drawn round the tiles that name it, so a
zone is never placed by hand. Arrows run orthogonally in the gutters between grid cells
and so never cross a tile. See the example in SKILL.md for every key.

Colours come from the repo's `.house-style.json` when there is one. Standard library only.
Exits 1, after writing, when text is estimated not to fit or a label lands on a tile.
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from itertools import permutations
from pathlib import Path

# No __pycache__ beside the scripts: the skill folder is copied into installs as it is.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

TILE_W, TILE_H = 256, 132
COL_GAP, ROW_GAP = 170, 104
MARGIN, HEADER = 48, 124
ZONE_PAD, ZONE_HEAD = 20, 34
LANE_STEP, CORNER = 10, 6
DEFAULT_MARK = "#3F3F46"  # a square mark without a brand colour; white glyph on both grounds
NUDGES = (0, -14, 14, -28, 28)
MAX_PERMUTED = 5  # lanes with more arrows keep their order; 5! routings is still instant
LANE_BELOW_ROW = ZONE_PAD + 14  # between a zone's bottom and the next zone's label
STATUSES = ("live", "planned", "to choose")
KINDS = ("main", "support")

# Zones are places, each tinted: (fill, border) per theme.
ZONE_TINTS = {
    "light": {
        "people": ("#F1F1EE", "#E5E4DE"),
        "cloud": ("#EDF3FB", "#D3E2F4"),
        "outside": ("#F3F0FA", "#E0D9F2"),
        "build": ("#EDF6F1", "#D0E8DA"),
    },
    "dark": {
        "people": ("#18181B", "#2E2E33"),
        "cloud": ("#121C28", "#22364D"),
        "outside": ("#1B1726", "#332B4A"),
        "build": ("#12211A", "#22402F"),
    },
}
EXTRA = {
    "light": {"cloud_mark": "#3B6FD4", "domain": "#C8772E", "plan": "#B7791F"},
    "dark": {"cloud_mark": "#6F9BEA", "domain": "#E0A060", "plan": "#E0B050"},
}


def load_description(path: Path) -> dict:
    if path.suffix == ".py":
        data = runpy.run_path(str(path)).get("DIAGRAM")
    else:
        data = json.loads(path.read_text())
    if not isinstance(data, dict):
        sys.exit(f"{path}: expected a dict (DIAGRAM = {{...}} in a .py file, or a JSON object)")
    return data


def validate(d: dict) -> None:
    zones = {z["id"]: z for z in d.get("zones", [])}
    for z in zones.values():
        if z.get("kind", "people") not in ZONE_TINTS["light"]:
            sys.exit(f"zone {z['id']}: kind must be one of {sorted(ZONE_TINTS['light'])}")
    tiles, cells = {}, {}
    for t in d.get("tiles", []):
        for key in ("id", "zone", "col", "row", "title"):
            if key not in t:
                sys.exit(f"tile {t.get('id', '?')}: missing {key!r}")
        if t["id"] in tiles:
            sys.exit(f"tile {t['id']}: id used twice")
        if t["zone"] not in zones:
            sys.exit(f"tile {t['id']}: unknown zone {t['zone']!r}")
        if t.get("status", "live") not in STATUSES:
            sys.exit(f"tile {t['id']}: status must be one of {STATUSES}")
        cell = (t["col"], t["row"])
        if cell in cells:
            sys.exit(f"tiles {cells[cell]} and {t['id']} share col/row {cell}")
        tiles[t["id"]], cells[cell] = t, t["id"]
    if not tiles:
        sys.exit("no tiles")
    for a in d.get("arrows", []):
        for end in ("from", "to"):
            if a.get(end) not in tiles:
                sys.exit(f"arrow {a}: unknown tile {a.get(end)!r}")
        if a.get("kind", "main") not in KINDS:
            sys.exit(f"arrow {a}: kind must be one of {KINDS}")
    for f in d.get("frames", []):
        missing = [t for t in f.get("tiles", []) if t not in tiles]
        if missing or not f.get("tiles"):
            sys.exit(f"frame {f.get('label')}: unknown or no tiles {missing}")


class Grid:
    def __init__(self, tiles: list[dict]):
        self.cols = max(t["col"] for t in tiles) + 1
        self.rows = max(t["row"] for t in tiles) + 1
        self.x0 = MARGIN + ZONE_PAD
        self.y0 = HEADER + ZONE_HEAD + ZONE_PAD
        self.occupied = {(t["col"], t["row"]) for t in tiles}

    def box(self, t: dict) -> tuple[float, float, float, float]:
        x = self.x0 + t["col"] * (TILE_W + COL_GAP)
        y = self.y0 + t["row"] * (TILE_H + ROW_GAP)
        return x, y, TILE_W, TILE_H

    def gutter_x(self, col: int) -> float:
        """Centre of the vertical gutter right of `col`."""
        return self.x0 + col * (TILE_W + COL_GAP) + TILE_W + COL_GAP / 2

    def lane_y(self, row: int) -> float:
        """The horizontal lane below `row`."""
        return self.y0 + row * (TILE_H + ROW_GAP) + TILE_H + LANE_BELOW_ROW

    @property
    def width(self) -> float:
        return self.x0 + self.cols * TILE_W + (self.cols - 1) * COL_GAP + ZONE_PAD + MARGIN

    @property
    def bottom(self) -> float:
        return self.y0 + self.rows * TILE_H + (self.rows - 1) * ROW_GAP + ZONE_PAD


def sides(src: dict, dst: dict, grid: Grid) -> tuple[str, str]:
    if src["col"] != dst["col"]:
        return ("right", "left") if dst["col"] > src["col"] else ("left", "right")
    if abs(dst["row"] - src["row"]) == 1:
        return ("bottom", "top") if dst["row"] > src["row"] else ("top", "bottom")
    if grid.cols == 1:
        sys.exit(f"{src['id']} -> {dst['id']}: same column, rows apart; add a column")
    side = "right" if src["col"] < grid.cols - 1 else "left"
    return side, side


def anchor(box, side: str, index: int, count: int) -> tuple[float, float]:
    x, y, w, h = box
    share = (index + 1) / (count + 1)
    return {
        "right": (x + w, y + h * share),
        "left": (x, y + h * share),
        "top": (x + w * share, y),
        "bottom": (x + w * share, y + h),
    }[side]


def skeleton(a: dict, src: dict, dst: dict, start, end, grid: Grid, lane) -> list:
    """The bend points of one arrow; `lane(key)` returns the offset of its lane."""
    (x1, y1), (x2, y2) = start, end
    sc, sr, tc, tr = src["col"], src["row"], dst["col"], dst["row"]
    if sc == tc and abs(tr - sr) == 1:
        if x1 == x2:
            return [start, end]
        y = grid.lane_y(min(sr, tr)) + lane(("h", min(sr, tr)))
        return [start, (x1, y), (x2, y), end]
    if sc == tc:
        g = sc if src["col"] < grid.cols - 1 else sc - 1
        x = grid.gutter_x(g) + lane(("v", g))
        return [start, (x, y1), (x, y2), end]
    step = 1 if tc > sc else -1
    g1 = sc if step > 0 else sc - 1
    g2 = tc - 1 if step > 0 else tc
    if g1 == g2:
        if y1 == y2:
            return [start, end]
        x = grid.gutter_x(g1) + lane(("v", g1))
        return [start, (x, y1), (x, y2), end]
    between = range(sc + step, tc, step)
    if sr == tr and y1 == y2 and not any((c, sr) in grid.occupied for c in between):
        return [start, end]
    row = lane_row(sr, tr, grid.rows)
    if row < 0:
        sys.exit(f"{a['from']} -> {a['to']}: no lane to route through; add a row or move a tile")
    xa = grid.gutter_x(g1) + lane(("v", g1))
    xb = grid.gutter_x(g2) + lane(("v", g2))
    y = grid.lane_y(row) + lane(("h", row))
    return [start, (xa, y1), (xa, y), (xb, y), (xb, y2), end]


def lane_row(sr: int, tr: int, rows: int) -> int:
    """The horizontal lane an arrow crosses columns in: beside the target's row."""
    if sr == tr:
        return sr if sr < rows - 1 else sr - 1
    return tr - 1 if tr > sr else tr


def route_all(d: dict, tiles: dict, grid: Grid) -> list[list]:
    arrows = d.get("arrows", [])
    ends: dict[tuple, list] = {}
    plan = []
    for i, a in enumerate(arrows):
        s_side, t_side = sides(tiles[a["from"]], tiles[a["to"]], grid)
        ends.setdefault((a["from"], s_side), []).append(i)
        ends.setdefault((a["to"], t_side), []).append(i)
        plan.append((s_side, t_side))

    def other(i, tile_id):
        a = arrows[i]
        return tiles[a["to"] if a["from"] == tile_id else a["from"]]

    # Order each side's arrows by where they go, so they leave without crossing.
    for (tile_id, side), users in ends.items():
        vertical_side = side in ("left", "right")
        users.sort(
            key=lambda i, t=tile_id, v=vertical_side: (
                (other(i, t)["row"], other(i, t)["col"])
                if v
                else (other(i, t)["col"], other(i, t)["row"])
            )
        )

    def raw(tile_id, side, i):
        users = ends[(tile_id, side)]
        return anchor(grid.box(tiles[tile_id]), side, users.index(i), len(users))

    nudges: dict[tuple, float] = {}

    def point(tile_id, side, i):
        """An end alone on its side lines up with the far end when that keeps it straight."""
        here = raw(tile_id, side, i)
        if len(ends[(tile_id, side)]) > 1:
            return here
        a = arrows[i]
        far_id = a["to"] if a["from"] == tile_id else a["from"]
        far = raw(far_id, plan[i][1] if a["from"] == tile_id else plan[i][0], i)
        x, y, w, h = grid.box(tiles[tile_id])
        shift = nudges.get((i, tile_id), 0)
        if side in ("left", "right"):
            if y + 16 <= far[1] <= y + h - 16 and not shift:
                return here[0], far[1]
            return here[0], here[1] + shift
        if x + 16 <= far[0] <= x + w - 16 and not shift:
            return far[0], here[1]
        return here[0] + shift, here[1]

    lanes: dict[tuple, list] = {}

    def build():
        out = []
        for i, a in enumerate(arrows):
            s_side, t_side = plan[i]
            start, end = point(a["from"], s_side, i), point(a["to"], t_side, i)
            out.append(skeleton(a, tiles[a["from"]], tiles[a["to"]], start, end, grid, lane_of(i)))
        return out

    def lane_of(i):
        def offset(key):
            users = lanes.setdefault(key, [])
            if i not in users:
                users.append(i)
            return (users.index(i) - (len(users) - 1) / 2) * LANE_STEP

        return offset

    def best(options, apply):
        """Apply each option, keep the one whose routing tangles least."""
        scored = []
        for option in options:
            apply(option)
            scored.append((tangle(build()), option))
        apply(min(scored, key=lambda pair: pair[0])[1])

    build()  # records which arrows share which lane
    for key, users in list(lanes.items()):
        if 1 < len(users) <= MAX_PERMUTED:
            best([list(o) for o in permutations(users)], lambda o, k=key: lanes.update({k: o}))
    # Arrows that cross a gutter in opposite directions can still share a stretch of line;
    # moving a lone end a little along its side separates them.
    for (tile_id, _side), users in ends.items():
        if len(users) == 1:
            best(NUDGES, lambda dy, k=(users[0], tile_id): nudges.update({k: dy}))
    return build()


def tangle(routes: list[list]) -> int:
    """Crossings between arrows, with a shared stretch of line weighing ten crossings."""
    segs = [(i, a, b) for i, pts in enumerate(routes) for a, b in zip(pts, pts[1:], strict=False)]
    score = 0
    for n, (i, (ax, ay), (bx, by)) in enumerate(segs):
        for j, (cx, cy), (dx, dy) in segs[n + 1 :]:
            if i == j:
                continue
            h1, h2 = ay == by, cy == dy
            if h1 == h2:
                same_line = (ay == cy) if h1 else (ax == cx)
                lo1, hi1 = sorted((ax, bx) if h1 else (ay, by))
                lo2, hi2 = sorted((cx, dx) if h1 else (cy, dy))
                if same_line and min(hi1, hi2) - max(lo1, lo2) > 0:
                    score += 10
                continue
            (hx1, hx2, hy), (vx, vy1, vy2) = (
                ((ax, bx, ay), (cx, cy, dy)) if h1 else ((cx, dx, cy), (ax, ay, by))
            )
            if min(hx1, hx2) < vx < max(hx1, hx2) and min(vy1, vy2) < hy < max(vy1, vy2):
                score += 1
    return score


def path_d(points: list) -> str:
    """Orthogonal polyline with small rounded corners."""
    out = [f"M {points[0][0]:g} {points[0][1]:g}"]
    for prev, here, nxt in zip(points, points[1:], points[2:], strict=False):
        r_in = min(CORNER, (abs(here[0] - prev[0]) + abs(here[1] - prev[1])) / 2)
        r_out = min(CORNER, (abs(nxt[0] - here[0]) + abs(nxt[1] - here[1])) / 2)
        r = min(r_in, r_out)

        def toward(a, b, dist):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = abs(dx) + abs(dy) or 1
            return a[0] + dx / length * dist, a[1] + dy / length * dist

        p1, p2 = toward(here, prev, r), toward(here, nxt, r)
        out.append(f"L {p1[0]:g} {p1[1]:g} Q {here[0]:g} {here[1]:g} {p2[0]:g} {p2[1]:g}")
    out.append(f"L {points[-1][0]:g} {points[-1][1]:g}")
    return " ".join(out)


def label_spot(points: list, plate_w: float, blocked) -> tuple[float, float]:
    """Where the label plate goes: the first segment, from the arrow's start, that holds it
    clear of tiles, other labels and other arrows; else the first that holds it at all."""
    segments = list(zip(points, points[1:], strict=False))

    def centre(seg):
        (ax, ay), (bx, by) = seg
        return (ax + bx) / 2, (ay + by) / 2

    def fits(seg):
        (ax, ay), (bx, by) = seg
        return ay == by and abs(bx - ax) >= plate_w + 8

    def clear(seg):
        cx, cy = centre(seg)
        return not blocked((cx - plate_w / 2, cy - 10, plate_w, 20))

    for test in (lambda g: fits(g) and clear(g), clear, fits):
        chosen = next((seg for seg in segments if test(seg)), None)
        if chosen is not None:
            return centre(chosen)
    return centre(max(segments, key=lambda g: abs(g[1][0] - g[0][0]) + abs(g[1][1] - g[0][1])))


def seg_box(a, b, pad: float = 1) -> tuple[float, float, float, float]:
    return (
        min(a[0], b[0]) - pad,
        min(a[1], b[1]) - pad,
        abs(b[0] - a[0]) + 2 * pad,
        abs(b[1] - a[1]) + 2 * pad,
    )


def overlaps(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def draw_tile(t: dict, box, c: dict, x: dict, warnings: list) -> list[str]:
    bx, by, w, h = box
    status = t.get("status", "live")
    dash = "" if status == "live" else ' stroke-dasharray="5 4"'
    out = [
        f'<rect x="{bx}" y="{by}" width="{w}" height="{h}" rx="12" fill="{c["surface"]}" '
        f'stroke="{c["faint"] if dash else c["line"]}" stroke-width="1"{dash}/>'
    ]
    mx, my = bx + 16, by + 16
    glyph = palette.esc(t.get("glyph", t["title"][:1].upper()))
    if t.get("mark") == "cloud":
        pts = " ".join(
            f"{mx + 15 + 15 * dx:g},{my + 15 + 15 * dy:g}"
            for dx, dy in ((0, -1), (0.87, -0.5), (0.87, 0.5), (0, 1), (-0.87, 0.5), (-0.87, -0.5))
        )
        out.append(f'<polygon points="{pts}" fill="{x["cloud_mark"]}"/>')
    else:
        out.append(
            f'<rect x="{mx}" y="{my}" width="30" height="30" rx="7" '
            f'fill="{t.get("color", DEFAULT_MARK)}" stroke="{c["line"]}" stroke-width="1"/>'
        )
    out.append(
        f'<text x="{mx + 15}" y="{my + 19.5}" font-size="13" font-weight="700" '
        f'text-anchor="middle" fill="#FFFFFF">{glyph}</text>'
    )
    room = w - 56 - 14
    texts = [(t["title"], 14, True, by + 30, c["ink"])]
    if t.get("product"):
        texts.append((t["product"], 12, False, by + 48, c["muted"]))
    for text, size, bold, y, fill in texts:
        if palette.text_width(text, size, bold) > room:
            warnings.append(f"tile {t['id']}: {text!r} is wider than the tile")
        weight = ' font-weight="700"' if bold else ""
        out.append(
            f'<text x="{bx + 56}" y="{y}" font-size="{size}"{weight} fill="{fill}">'
            f"{palette.esc(text)}</text>"
        )
    chip_w = palette.text_width(status.upper(), 9.5, True, 0.8) + 16
    rule_y = by + 66
    out.append(
        f'<rect x="{bx + 16}" y="{rule_y}" width="{w - 32 - chip_w - 8:g}" height="1" '
        f'fill="{c["line"]}"/>'
    )
    out += chip(bx + w - 16 - chip_w, rule_y - 9, status, c, x)
    runs = t.get("runs", [])[:2]
    for i, line in enumerate(runs):
        if palette.text_width(line, 12) > w - 32:
            warnings.append(f"tile {t['id']}: {line!r} is wider than the tile")
        out.append(
            f'<text x="{bx + 16}" y="{by + 92 + 18 * i}" font-size="12" fill="{c["muted"]}">'
            f"{palette.esc(line)}</text>"
        )
    return out


def chip(cx: float, cy: float, status: str, c: dict, x: dict) -> list[str]:
    w = palette.text_width(status.upper(), 9.5, True, 0.8) + 16
    fill, stroke, ink = {
        "live": (c["accent"], c["accent"], c["paper"]),
        "planned": (c["surface"], c["faint"], c["muted"]),
        "to choose": (c["surface"], x["plan"], x["plan"]),
    }[status]
    return [
        f'<rect x="{cx:g}" y="{cy:g}" width="{w:g}" height="18" rx="9" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1"/>',
        f'<text x="{cx + w / 2:g}" y="{cy + 12.5:g}" font-size="9.5" font-weight="700" '
        f'letter-spacing="0.8" text-anchor="middle" fill="{ink}">{status.upper()}</text>',
    ]


def draw_zones(d: dict, tiles: dict, grid: Grid, c: dict, tints: dict) -> list[str]:
    out = []
    for z in d.get("zones", []):
        members = [grid.box(t) for t in tiles.values() if t["zone"] == z["id"]]
        if not members:
            continue
        left = min(b[0] for b in members) - ZONE_PAD
        top = min(b[1] for b in members) - ZONE_PAD - ZONE_HEAD
        right = max(b[0] + b[2] for b in members) + ZONE_PAD
        bottom = max(b[1] + b[3] for b in members) + ZONE_PAD
        fill, border = tints[z.get("kind", "people")]
        out.append(
            f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="16" '
            f'fill="{fill}" stroke="{border}" stroke-width="1"/>'
        )
        label = z.get("label", z["id"]).upper()
        out.append(
            f'<text x="{left + 18}" y="{top + 24}" font-size="11" font-weight="700" '
            f'letter-spacing="1.4" fill="{c["muted"]}">{palette.esc(label)}</text>'
        )
        if z.get("pill"):
            px = left + 18 + palette.text_width(label, 11, True, 1.4) + 10
            pw = palette.text_width(z["pill"], 10.5) + 16
            out.append(
                f'<rect x="{px:g}" y="{top + 11}" width="{pw:g}" height="18" rx="9" '
                f'fill="{c["surface"]}" stroke="{border}"/>'
            )
            out.append(
                f'<text x="{px + pw / 2:g}" y="{top + 24}" font-size="10.5" text-anchor="middle" '
                f'fill="{c["muted"]}">{palette.esc(z["pill"])}</text>'
            )
    return out


def draw_frames(d: dict, tiles: dict, grid: Grid, c: dict, x: dict) -> list[str]:
    out = []
    for f in d.get("frames", []):
        boxes = [grid.box(tiles[t]) for t in f["tiles"]]
        left, top = min(b[0] for b in boxes) - 10, min(b[1] for b in boxes) - 10
        right = max(b[0] + b[2] for b in boxes) + 10
        bottom = max(b[1] + b[3] for b in boxes) + 10
        colour = x["domain"] if f.get("kind", "domain") == "domain" else c["muted"]
        out.append(
            f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="14" '
            f'fill="none" stroke="{colour}" stroke-width="1.2" stroke-dasharray="6 4"/>'
        )
        label = f.get("label", "")
        lw = palette.text_width(label, 11, True) + 12
        out.append(
            f'<rect x="{right - lw - 12:g}" y="{top - 8}" width="{lw:g}" height="16" rx="4" '
            f'fill="{c["paper"]}"/>'
        )
        out.append(
            f'<text x="{right - lw / 2 - 12:g}" y="{top + 4}" font-size="11" font-weight="700" '
            f'text-anchor="middle" fill="{colour}">{palette.esc(label)}</text>'
        )
    return out


def draw_arrows(d, routes, tiles, grid, c, warnings) -> list[str]:
    lines, plates, placed = [], [], []
    boxes = [grid.box(t) for t in tiles.values()]
    for n, (a, points) in enumerate(zip(d.get("arrows", []), routes, strict=True)):
        others = [
            seg_box(p, q)
            for m, pts in enumerate(routes)
            if m != n
            for p, q in zip(pts, pts[1:], strict=False)
        ]
        main = a.get("kind", "main") == "main"
        colour = c["accent"] if main else c["faint"]
        lines.append(
            f'<path d="{path_d(points)}" fill="none" stroke="{colour}" stroke-width="1.6" '
            f'marker-end="url(#head-{"main" if main else "support"})"/>'
        )
        label = a.get("label", "")
        step = a.get("step")
        if not label and step is None:
            continue
        text_w = palette.text_width(label, 11) if label else 0
        lead = 24 if step is not None else 8
        plate_w = lead + text_w + (8 if label else 0)
        cx, cy = label_spot(
            points,
            plate_w,
            lambda r, near=boxes + placed + others: any(overlaps(r, o) for o in near),
        )
        rect = (cx - plate_w / 2, cy - 10, plate_w, 20)
        if any(overlaps(rect, b) for b in boxes):
            warnings.append(f"label of {a['from']} -> {a['to']} lands on a tile; move a tile")
        if any(overlaps(rect, p) for p in placed):
            warnings.append(f"label of {a['from']} -> {a['to']} overlaps another label")
        placed.append(rect)
        plates.append(
            f'<rect x="{rect[0]:g}" y="{rect[1]:g}" width="{plate_w:g}" height="20" rx="10" '
            f'fill="{c["paper"]}" stroke="{c["line"]}"/>'
        )
        if step is not None:
            plates.append(
                f'<circle cx="{rect[0] + 11:g}" cy="{cy:g}" r="8.5" fill="{colour}"/>'
                f'<text x="{rect[0] + 11:g}" y="{cy + 3.8:g}" font-size="10.5" font-weight="700" '
                f'text-anchor="middle" fill="{c["paper"]}">{step}</text>'
            )
        if label:
            plates.append(
                f'<text x="{rect[0] + lead:g}" y="{cy + 3.8:g}" font-size="11" '
                f'fill="{c["ink"]}">{palette.esc(label)}</text>'
            )
    return lines + plates


def draw_legend(d, top: float, width: float, c, x) -> tuple[list[str], float]:
    out = [
        f'<text x="{MARGIN}" y="{top}" font-size="11" font-weight="700" letter-spacing="1.4" '
        f'fill="{c["muted"]}">STEPS</text>'
    ]
    px, py = MARGIN, top + 26
    steps = sorted(
        (a for a in d.get("arrows", []) if a.get("step") is not None), key=lambda a: a["step"]
    )
    for a in steps:
        text = a.get("note", a.get("label", ""))
        w = 26 + palette.text_width(text, 12) + 28
        if px + w > width - MARGIN and px > MARGIN:
            px, py = MARGIN, py + 26
        out.append(
            f'<circle cx="{px + 9}" cy="{py - 4}" r="8.5" fill="{c["accent"]}"/>'
            f'<text x="{px + 9}" y="{py - 0.2}" font-size="10.5" font-weight="700" '
            f'text-anchor="middle" fill="{c["paper"]}">{a["step"]}</text>'
            f'<text x="{px + 26}" y="{py}" font-size="12" fill="{c["ink"]}">{palette.esc(text)}</text>'
        )
        px += w
    py += 34
    px = MARGIN
    for status in STATUSES:
        out += chip(px, py - 13, status, c, x)
        px += palette.text_width(status.upper(), 9.5, True, 0.8) + 30
    out.append(
        f'<path d="M {px + 6} {py - 4} L {px + 40} {py - 4}" stroke="{c["faint"]}" '
        f'stroke-width="1.6" marker-end="url(#head-support)"/>'
        f'<text x="{px + 50}" y="{py}" font-size="12" fill="{c["muted"]}">supporting flow</text>'
    )
    out.append(
        f'<text x="{px + 170}" y="{py}" font-size="12" fill="{c["muted"]}">'
        f"dashed tile: not running yet</text>"
    )
    return out, py


def render(d: dict, theme: str, themes: dict) -> tuple[str, list[str]]:
    c, x, tints = themes[theme], EXTRA[theme], ZONE_TINTS[theme]
    tiles = {t["id"]: t for t in d["tiles"]}
    grid = Grid(list(tiles.values()))
    warnings: list[str] = []
    width = max(grid.width, 900)
    routes = route_all(d, tiles, grid)
    legend, legend_bottom = draw_legend(d, grid.bottom + 44, width, c, x)
    height = legend_bottom + MARGIN - 10
    title = palette.esc(d.get("title", "Architecture"))
    heads = "".join(
        f'<marker id="head-{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        f'fill="{colour}"/></marker>'
        for name, colour in (("main", c["accent"]), ("support", c["faint"]))
    )
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height:g}" '
        f'viewBox="0 0 {width:g} {height:g}" role="img" aria-label="{title}">',
        f"<title>{title}</title>",
        f"<defs>{heads}</defs>",
        f'<rect width="{width:g}" height="{height:g}" fill="{c["paper"]}"/>',
        f'<g font-family="{themes["font"]}">',
    ]
    if d.get("eyebrow"):
        o.append(f'<circle cx="{MARGIN + 4}" cy="48" r="4" fill="{c["accent"]}"/>')
        o.append(
            f'<text x="{MARGIN + 20}" y="53" font-size="13" font-weight="600" '
            f'letter-spacing="2.2" fill="{c["muted"]}">{palette.esc(d["eyebrow"].upper())}</text>'
        )
    o.append(
        f'<text x="{MARGIN}" y="96" font-size="30" font-weight="700" letter-spacing="-1" '
        f'fill="{c["ink"]}">{title}</text>'
    )
    o += draw_zones(d, tiles, grid, c, tints)
    for t in tiles.values():
        o += draw_tile(t, grid.box(t), c, x, warnings)
    o += draw_frames(d, tiles, grid, c, x)
    o += draw_arrows(d, routes, tiles, grid, c, warnings)
    o += legend
    o += ["</g>", "</svg>"]
    return "\n".join(o) + "\n", warnings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("description", type=Path, help="a .py file defining DIAGRAM, or a .json file")
    p.add_argument("--out", type=Path, help="output folder (default: beside the description)")
    p.add_argument("--name", default="architecture", help="file stem: <name>-light.svg")
    p.add_argument(
        "--root", type=Path, default=Path.cwd(), help="where to look for .house-style.json"
    )
    args = p.parse_args(argv)

    d = load_description(args.description)
    validate(d)
    themes = palette.load(args.root)
    out = args.out or args.description.parent
    out.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    for theme in ("light", "dark"):
        svg, warnings = render(d, theme, themes)
        path = out / f"{args.name}-{theme}.svg"
        path.write_text(svg)
        print(f"wrote {path}")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
