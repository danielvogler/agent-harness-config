---
name: house-style
description: Carries one house look for every visual. Use for any visual output - an HTML dashboard, board, report or one-pager, a README banner or hero graph, an architecture picture, a process map, a Mermaid chart, a slide-like page - even when the person only says "make it look good", "build a page that shows X" or "use X's corporate layout". Writes every page part out in words with exact values and ships a starter stylesheet that implements them, the rules for diagrams from a system sheet, the wording rules, a brand lookup (a named brand profile, else the repo's .house-style.json, else neutral), a brief, and a check script that renders the page or picture and fails bland or sloppy output. Scripts draw banners and architecture pictures as light and dark SVG pairs and fill an HTML report.
---

# House style

One look for every visual: dashboards, boards, reports, one-pagers, banners, hero graphs,
architecture pictures, diagrams and slide-like pages. Scripts draw the pictures; a
starter stylesheet carries the page parts; a check fails what the person rejected.

**What applies where.**

1. **Both** dashboards and diagrams: the colours, type and never list of
   [look.md](references/look.md) §12–§13, the words in [writing.md](references/writing.md),
   the brand lookup below, the brief, and the check.
2. **Dashboards only** (pages, boards, reports, one-pagers): every part in words with its
   values in [look.md](references/look.md) §1–§11, and which part for which content in
   [dashboards.md](references/dashboards.md).
3. **Diagrams only** (hero graphs, architecture, process maps, banners, Mermaid, slide
   pictures): the system sheet, tile, arrow, part colours, labels and sizes in
   [diagrams.md](references/diagrams.md).

| Read | When |
|---|---|
| [references/look.md](references/look.md) | first, for any page: each part in exact words and values |
| [references/dashboards.md](references/dashboards.md) | a dashboard, board, report or one-pager |
| [references/diagrams.md](references/diagrams.md) | a hero graph, architecture picture, diagram, banner, slide picture |
| [references/writing.md](references/writing.md) | any words on a page or picture |
| [references/brief.md](references/brief.md) | before starting, to fill the brief |

## Brand

The brand decides the accent, the fade, the ramp hue, the font, the logo and the mark;
the neutrals, sizes and parts stay. In this order:

1. **A named brand.** When the person names one ("use X's corporate layout", "for X"),
   read `${HOUSE_STYLE_BRANDS:-~/.config/house-style/brands}/<name>/brand.json` and run
   `python3 <skill>/scripts/brand.py --brand <name> --write`: it copies the logo and mark
   into `docs/assets/brand/` and writes the repo's `.house-style.json`. Profiles live in
   the person's own repository, never in this skill.
2. **The repo's `.house-style.json`**, when it exists.
3. **Brand files found in the repo**: `python3 <skill>/scripts/brand.py` proposes entries
   from a logo, a mark, a `--brand…` or `--accent` token and an `@font-face`, with their
   sources; `--write` writes them. Show them before using them.
4. **Nothing found**: the neutral default and a text wordmark.

**The repo's own rules win.** When its AGENTS.md (or a board's own AGENTS.md) says it stays
neutral or names its own look, the brand is not applied: say so in the brief and use only
the parts and neutrals.

A profile's `brand.json` holds `name`, `accent`, `accent_dark`, `font`, `font_file` (a
woff2 in the profile folder), `fade` and `fade_dark` (two or three stops, `"#RRGGBB 0%"`;
the dark ones lifted to read on near-black), optional `ramp` (`#RRGGBB`), and `logo`,
`logo_dark` and `mark` (file names in the profile folder). The company logo goes top
left on every page, 22px high; a product with a logo of its own (a tool, an app) shows
its own mark and name there instead, and no company logo. The mark marks only the one highlighted item. The font is bundled locally,
never fetched.

## Workflow

0. **An existing dashboard is improved in place**, never rebuilt
   ([dashboards.md](references/dashboards.md) §1).
1. **Brand**, as above. **Brief**: fill [the brief](references/brief.md): reader, what each
   page or picture shows, and one or two files of pages or pictures the person approved
   with the traits to copy named. An adjective is not a reference. Approved pictures
   already in the repo (hero graphs, an earlier page) are the reference; when they are off
   limits (a blind test) or older than the look, use `assets/example-dashboard.png` and
   say which in the brief. A diagram also needs the repo's system sheet
   ([diagrams.md](references/diagrams.md) §1).
2. **Start from the starter**: `python3 <skill>/scripts/starter.py <out> --example` writes
   `starter.css` in the brand's colours, the example page and `chips.js`. Copy parts from
   the example; delete it before the first commit.
3. **One page first, in two or three variants** side by side in a copy of
   `assets/compare.html`; the person picks. Without a person, use the pick rule in
   [the brief](references/brief.md) and write the counts down. When improving an
   engine-driven app in place (step 0), skip the variants and say so in the brief: the
   look is fixed by look.md, and the engine renders every page alike.
4. **Build the rest** in the picked variant, part by part as written in look.md.
5. **Check** until it exits 0, light and dark:
   `npm install --no-save --prefix "$TMPDIR/visual-check" playwright-core`, then
   `NODE_PATH="$TMPDIR/visual-check/node_modules" node <skill>/scripts/check_visual.js page.html`
   and again with `--dark`. A README picture also with `--shown 830`.
6. **Review against the reference**, both themes: render with `--shot`, put it beside the
   reference and list, part by part from look.md, what matches and what does not; fix
   before showing.
7. **Text pass** with [writing.md](references/writing.md).
8. **Keep it**: when the repo has its own build or loop prompts (an
   `engine/prompts/build.md`, a builder brief), update them in the same change so the
   next round writes the look: titles in words with the subject named, never a title that
   states a finding; the head of three lines; numbers once; the parts of look.md.

## Rules

1. **Colour is a code**: the accent, one semantic set and greys, at most three hue
   families on a screen (a diagram keeps up to four part colours). The coded exhibit
   carries its colour on many small marks, never on big fills. A page of only ink and
   grey fails as much as one with several codes.
2. **The fade** goes in its six places and nowhere else; numbers are solid; flat brand
   red only for a warning or the highest risk step; an accent that collides with a status
   hue turns good to ink (look.md §12).
3. **Every tile is lifted**, never a flat outlined box (look.md §5).
4. **Navigation is one header row** of text tabs: groups, a hairline, only the open
   group's pages (look.md §1). The left column holds the page name and its sections.
5. **The head is three lines**; the title names the subject, which alone carries the
   fade; no count title, no audience label, a number in one place (look.md §3,
   writing.md §1).
6. **Faces are real or neutral**: the item's real logo, else initials in a grey chip; the
   brand mark only on the one highlighted item; no invented shapes, no black icons.
7. **Each item once**, one line per list item, and every chip names itself on hover.
8. **Nothing overflows or is cut off**; missing content is an empty-state box.
9. **A diagram starts from the system sheet** and is judged at the width it is shown
   ([diagrams.md](references/diagrams.md)).

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

Dashboards, boards and one-pagers use the neutrals of [look.md](references/look.md) §12;
the accent and the brand are shared with everything else.

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

`visual` holds the repo's own additions for pages, the check and the review:

```json
{"accent": "#B03A2E", "visual": {
  "logo": "docs/assets/logo.svg",
  "mark": "M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Z",
  "fade": ["#B03A2E 0%", "#8E2E25 50%", "#5E1F19 100%"],
  "ramp": "#8E2E25",
  "references": [{"file": "docs/reference/summary.png", "traits": ["status column", "page head"]}],
  "extraPhrases": ["synergy", "best of breed"]}}
```

`logo` is the brand logo file shown in the page header (22px high); `logo_dark` its
variant for the dark theme. `fade_dark` holds the lifted fade stops for the dark theme.
`font_file` is a local woff2 for `font`; `starter.py` writes its `@font-face`. `mark` is the brand
mark used as the face of items that have no logo of their own: SVG path data on a 16×16
grid, or a file. `fade` is the brand accent as a gradient of two or three stops, in the
six places of look.md §12; with three stops, numbers take its middle stop. `ramp` is
the hue of the raster's five steps (default: the accent). `starter.py --example` puts the
logo and the mark into the example page. `references`
are screenshots of pages the person approved, committed in the repo, with the traits to
copy; the brief and the review use them. `extraPhrases` are words `check_visual.js`
fails on in this repo, on top of `references/banned-phrases.txt`. Any other key under
`visual` is an error.

Brand colours never live in this skill: a named brand profile (see "Brand") or the repo
itself holds them.

## Layout

The look of a banner is what `banner.py` draws (run it once to see the pair):

1. **Eyebrow**: an accent dot and small spaced capitals in muted grey.
2. **Title**: big and bold in ink, an optional suffix in muted regular weight, then an
   accent full stop.
3. **Description**: one sentence in muted grey, at most two lines, wrapped evenly.
4. **Footer**: one faint line, and a hairline along the bottom edge.
5. Plenty of paper. One accent, used sparingly: the dot, the main flow, a `live` chip.

Before calling any of it done, render both themes (see "Rendering to look at it" below)
and look at every image yourself; a picture nobody looked at is not done.

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

Flows, sequences and state machines are Mermaid, themed with the one `%%{init}%%` line in
[diagrams.md](references/diagrams.md) §10 (straight connectors, the "Google style"
values). Draw the trust boundary, not the call graph. Colour the node where a human
approves.

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

## Dashboards, boards and one-pagers

[references/look.md](references/look.md) writes out each part; `assets/starter.css`
implements it, light and dark: header with text tabs, left column, page head, section
divider, lifted and exhibit tiles, raster, highlight tile, side list, group cards, table
with a status column, empty state, decision box, segmented filter. `assets/look.html`
shows the parts on one sheet (`assets/look.png`, `assets/look-dark.png`; a spec sheet,
not checked). `assets/example.html` is a whole page built from them, and
`assets/example-dashboard.png` its reference picture. The report template above stays for
long reading; a page with exhibits starts from the starter.

## The check

```bash
npm install --no-save --prefix "$TMPDIR/visual-check" playwright-core
NODE_PATH="$TMPDIR/visual-check/node_modules" \
  node <skill>/scripts/check_visual.js page.html     # also a URL, an .svg, a .png
```

It renders with the installed Chrome (`CHROME_PATH` to override) and exits 1 when a check
fails, 2 when it cannot render. A page fails with fewer than five coloured marks or rows
and cards without one on the first screen; with a raster or card grid anywhere on the
page whose chips or cards mostly lack a coloured mark; with fewer coloured elements than
half its rows, chips and cards; with more than three hue families on any one screen
(logos, pictures and charts wider than 300px hidden; a colour-token sheet opts out with
`data-visual-skip="hues"`); more than nine top-level nav items; no page head (eyebrow,
title of at most two lines, text below); any clipped or truncated text; or a banned
phrase. A table without a coloured column is named in the output but does not fail on
its own: reference tables (terms, codes) may stay ink. A page also fails with a title
that opens with a number, the same number in
three or more heads, or more than four text rows above the first exhibit, or a left-column label longer than two
lines or about 40 characters. The header (its row and logo link) is never counted as
content or as a nav item; a labelled tab group (`aria-label`) counts as one item. An SVG fails
on overflowing labels, more than four hue families, banned phrases, a median label below
7.5px or any label below 5px at the width it is shown (`--shown 830`, a README column, by
default), or a width above 1320px; a PNG gets the hue count only. `--shot
first.png` writes the first screen for the review; `--dark` renders the dark theme.
Run it on both themes.

## The review

Before showing anything, open the render beside its reference (the brief's screenshot,
`visual.references`, or `assets/example-dashboard.png` and `assets/example-flow-light.png`),
light and dark, and write a short list: for each trait named in the brief, matches or
not, and what differs. Then look for the rejected patterns in
[dashboards.md](references/dashboards.md) §7, [diagrams.md](references/diagrams.md) §12 and
the never list in [references/look.md](references/look.md) §13. When the person compares
two versions, label each side ("before", "after") on the page itself.
Fix what does not match, render again, and only then show it, with the list.

## Rendering to look at it

```bash
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$chrome" --headless=new --disable-gpu --hide-scrollbars --window-size=1200,340 \
  --screenshot=banner-light.png "file://$PWD/docs/assets/banner-light.svg"
```

Size the window to the SVG's `width` and `height`. The dark SVG is its own file; for the
report's dark theme add `--force-dark-mode`.
