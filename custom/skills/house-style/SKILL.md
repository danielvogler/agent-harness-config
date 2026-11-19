---
name: house-style
description: Use when making a README banner, an architecture picture (what runs where), a diagram, an HTML report or a slide-like page. Scripts draw banner and architecture SVG pairs, light and dark, and fill a single-file HTML report, in one neutral palette with each repo's accent read from its .house-style.json.
---

# House style

One look for banners, diagrams and reports, drawn by scripts instead of copied between
repos. Every script writes a light and a dark version and reads the repo's colours.

## Palette

Neutral ink, with one accent per repo.

| Role | Light | Dark | Used for |
|---|---|---|---|
| paper | `#FDFDFB` | `#0E0E10` | background |
| ink | `#0E0E10` | `#FDFDFB` | titles, body text |
| muted | `#6F6F6B` | `#A3A39D` | descriptions, suffixes, eyebrows |
| faint | `#A3A39D` | `#6F6F6B` | footers, supporting arrows |
| line | `#E5E4DE` | `#54545A` | hairlines, tile borders |
| accent | `#1F6F5C` | `#5FBFA6` | the dot, the main flow, `live` |

Font: Inter, falling back to `ui-sans-serif, -apple-system, Segoe UI, Helvetica, Arial,
sans-serif`; code in `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`. The dark
accent is the same hue lifted, since the print accent disappears on near-black.

**A repo sets its own colours** in a committed `.house-style.json` at its root; every
script finds it from the working directory up to the git root:

```json
{"accent": "#B03A2E", "accent_dark": "#E8857A", "font": "Source Sans 3"}
```

Keys: `accent`, `accent_dark`, and optionally `paper`, `ink`, `paper_dark`, `ink_dark`
(`#RRGGBB`) and `font` (put in front of the fallbacks). An unknown key is an error.

Brand colours never live in this skill; a brand's own repository or folder-level
instructions say where its tokens are, and that `.house-style.json` takes them from there.

## Layout

The reference look is the banner of `agent-harness-config`, the repo this skill ships
from (`docs/assets/banner-{light,dark}.svg`), which `banner.py` redraws:

1. **Eyebrow**: an accent dot and small spaced capitals in muted grey.
2. **Title**: big and bold in ink, an optional suffix in muted regular weight, then an
   accent full stop.
3. **Description**: one sentence in muted grey, at most two lines, wrapped evenly.
4. **Footer**: one faint line, and a hairline along the bottom edge.
5. Plenty of paper. One accent, used sparingly: the dot, the main flow, a `live` chip.

Before calling any of it done, follow "Look at it before calling it done" in `docs.md`:
render both themes and read every image.

## Banner

```bash
python3 <skill>/scripts/banner.py --title my-tool --suffix=-cli \
  --eyebrow "Data pipeline" --description "Loads the nightly feed into the warehouse." \
  --footer "One make target per step." \
  --side-label "Runs as" --side-chip "make load" --side-note "one command" \
  --side-item Ingest --side-item Clean --side-item Publish
```

It writes `docs/assets/banner-light.svg` and `banner-dark.svg` (`--out` to change). The
side column is optional: a chip fanning out to up to six items, or the items alone. The
title shrinks and the description rewraps to fit; when they still do not, the script
writes the files, prints a warning and exits 1. Show the pair in the README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner-dark.svg">
  <img alt="One line on what it does" src="docs/assets/banner-light.svg">
</picture>
```

## Architecture picture

What runs where is an SVG pair, `docs/assets/architecture-{light,dark}.svg`, drawn from a
description beside it (`docs/assets/architecture.py`) and shown atop
`docs/ARCHITECTURE.md`. It shows how things are: a change to a service, a cloud resource,
an outside provider or a flow between them updates the description and both SVGs in the
same pull request.

```bash
cp <skill>/examples/architecture.py docs/assets/architecture.py   # then edit
python3 <skill>/scripts/diagram.py docs/assets/architecture.py      # or a .json file
```

1. **Zones are places**, each tinted: `people` (grey), `cloud` (light blue, its region as
   a `pill`), `outside` services (lavender), `build` and operate (green). A domain is a
   name, not a place: a dashed orange `frame` round what it points at. A part that runs
   in another region gets its own dashed frame (`"kind": "region"`), labelled.
2. **Tiles** sit on a grid (`col`, `row`), white on their zone; the zone is drawn round
   its tiles. Each has a mark (`"mark": "cloud"` for a cloud product's blue hexagon,
   otherwise a rounded square in its brand `color`), a title saying what it is for, the
   product's name, a thin rule, and two lines on what runs there. A chip says `live`,
   `planned` or `to choose`; a tile not running yet has a dashed border.
3. **Arrows** are orthogonal and run in the gutters between cells, never through a tile:
   accent and numbered (`step`) for the main flow, grey (`"kind": "support"`) for
   supporting ones, each with a short `label` on a plate. The legend lists the numbered
   steps (`note` for a longer wording) and the chips.

The script orders shared lanes to avoid crossings, and warns (exit 1) when text is too
wide for its tile or a label lands on a tile or another label. Moving a tile one cell is
usually the fix.

## Other diagrams

Flows, sequences and state machines are mermaid, themed with one `%%{init}%%` line before
the graph:

```text
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#FFFFFF","primaryTextColor":"#202124","primaryBorderColor":"#DADCE0","lineColor":"#5F6368","secondaryColor":"#F8F9FA","tertiaryColor":"#F8F9FA","clusterBkg":"#F8F9FA","clusterBorder":"#DADCE0","edgeLabelBackground":"#FFFFFF"},"flowchart":{"curve":"basis","nodeSpacing":40,"rankSpacing":64,"useMaxWidth":true}} }%%
```

Draw the trust boundary, not the call graph. Colour the node where a human approves.

## HTML report

`templates/report.html` is one self-contained page: the palette as CSS variables, light
and dark by `prefers-color-scheme`, a sticky contents column, tables, and status chips
(`<span class="chip live">live</span>`; also `planned`, `choose`, `blocked`). Fill
`{{title}}`, `{{eyebrow}}`, `{{toc}}`, `{{body}}` and `{{footer}}` by hand, or from
markdown:

```bash
uv run --with markdown python3 <skill>/scripts/report.py notes.md -o report.html --eyebrow Review
```

The first `# heading` becomes the title, `##` and `###` the contents. For a slide-like
page, use the same template with one `##` section per slide.

## Rendering to look at it

```bash
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$chrome" --headless=new --disable-gpu --hide-scrollbars --window-size=1200,340 \
  --screenshot=banner-light.png "file://$PWD/docs/assets/banner-light.svg"
```

Size the window to the SVG's `width` and `height`. The dark SVG is its own file; for the
report's dark theme add `--force-dark-mode`.
