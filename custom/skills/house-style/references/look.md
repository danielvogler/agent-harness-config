# The look, in words and numbers

Every part of a dashboard, board or one-pager, written as one exact paragraph. Sizes are
given in px at a 16px root, with the rem value `assets/starter.css` uses. The starter
implements every value here; §14 lists the ones a test compares with it. `assets/look.html`
shows the parts on one page (`assets/look.png`, `assets/look-dark.png`), and
`assets/example.html` is a whole page built from them (`assets/example-dashboard.png`).

Diagrams share §12 (colours and type) and the never list; their own parts are in
[diagrams.md](diagrams.md).

## Contents

1. Header
2. Left column
3. Page head
4. Section divider
5. Lifted tile
6. Raster
7. Highlight tile
8. Side list
9. Group cards
10. Table
11. Empty state
12. Colours and type
13. Never
14. Values the test holds

## 1. Header

One row, sticky, on the paper colour, 64px high including a 1px `--hair` line along its
bottom edge; content 32px in from both sides, at most 1440px wide. **Left:** the company
logo, 22px high and left-aligned, never centred over the name (a text wordmark of 16.8px
bold when there is no logo; in the dark theme the profile's `logo_dark`, else the logo
drawn in `--ink`). Under it the board's name in 11.8px semibold `--ink-2`, one line: what
the board is about ("Depot renewal · plan, risks, decisions"). A product with a logo of
its own (a tool, an app) shows that instead: its mark 32px high with its name beside it
as a wordmark of 20px bold, the board line under the name; no company logo on it. The
company brand then lends at most its colours and font. **Right:** text tabs, nothing else: first the
groups, then a 1px `--line` divider that runs from 14px below the header's top to 14px
above its bottom, with 12px either side, then only the open group's pages. A tab is
weight 500, letter-spacing 0.01em, 12px padding left and right (pages 9px), as tall as
the header; the two levels differ by a step, not by a box: a group is 14.4px `--ink-2`,
a page 12.8px `--muted`. The open group and the open page are
`--ink`, weight 600, with a 2px fade underline that lies on the header's bottom line and
is inset by the tab's padding. A group or page that does not exist yet is `--faint` and
not a link. A group with one page shows no page tabs after the hairline. The open group's
pages sit in their own element with an `aria-label` ("Pages"), which the check counts as
one item. Controls the page needs (a theme toggle, a home link) go in the footer, not the
header. No pills, no track, no second row.
**A monitoring board** (it watches running things that can need the person at any
moment: agent loops, jobs, builds) also keeps its alarm figures in the middle of the header on every page, so
whatever starts waiting shows from any page: the number in `--ink` weight 600, the label
`--muted`, "waiting for you" in the accent and only when above zero, "needs a look" in
`--warn`; no dots, no pills, each a link to the list filtered to it. The page head then
does not repeat them. A report or analysis board (risks, a market, a plan) never does
this: its counts are content, not alarms, and the header keeps only logo and tabs.

## 2. Left column

A 216px column, 40px from the content, sticky 86px from the top. It opens with the open
page's name in 13.8px semibold `--ink`, 8px above the list. Each section is one line of
12.5px `--ink-2` with 4px above and below: its number in bold, solid `--num`, tabular, in a
column 2.3em wide, then 8px, then the section's short label; labels of one or two lines
align on the same left edge. A label is at most two lines and about 40 characters: a long
section title ("Runners compete; the gate follows the runner; …") gets a short label
("Runners and gates") here and keeps its full wording as the heading. No "On this page"
label, no pages of other groups.

## 3. Page head

At most three lines before the first exhibit. **Eyebrow:** 10.6px bold capitals,
letter-spacing 0.16em, `--ink-2`, led by a 7px dot in the solid accent and 8px gap; it
names the group and the page ("Assess · Risks"). **Title:** 21.6px bold, line-height 1.22,
letter-spacing −0.018em, 8px above and 4px below, one line where it fits; it names the
subject and the question in words, and the subject word alone carries the fade as text
colour ("Which **risks** the depot renewal has to carry"). **Points line:** 14.4px
`--muted`, one line, two to four short points separated by 6px fade dots with 10px either
side. No KPI strip, contents line or audience label under or above it, and no count a filter
row on the same page already shows. A page that comes
with a long thesis or lede keeps it out of the head: its first two lines become the lead
of the first section (§4), the rest goes into that section's body.

## 4. Section divider

22px above a section (14px for the first). A 1px `--hair` line, then 16px, then one row
on a common baseline: the section number in 10.9px bold, letter-spacing 0.14em, solid
`--num` ("3.1"); 14px; the heading in 16.3px semibold, letter-spacing −0.005em; on the
right an optional aside in 11.8px `--muted`. 14px below the row, an optional lead
sentence in 14.4px `--ink-2`, at most 110 characters a line, 14px above the exhibit. No
heavy rule, no "Section" word.

## 5. Lifted tile

Every tile (exhibit, card, list, table, decision) is white `--surface` with a 14px
radius and a lift instead of an outline: an inset 1px top highlight of white at 85 %, an
inset 1px ring of ink at 7 %, a 0 1px 2px shadow of ink at 4 % and a 0 12px 32px −18px
shadow of ink at 22 % (`--shadow`). On hover a link tile takes `--lift` and moves up 1px.
Padding 16px 18px; an exhibit tile (`.fig`) 22px 20px 16px with a 5px fade bar along its
top edge, rounded with the tile. Two tiles side by side split 1.45 : 1 with an 18px gap.

## 6. Raster

The two-axis matrix. Above it the vertical axis title in 11.2px `--muted` with the name in
semibold `--ink-2` ("Impact ↑ · 1 low to 5 high"). A grid of a 22px label column and five
equal columns, 4px gaps. Each cell is at least 62px high, 8px radius, 6px padding, and
tinted by its score with the ramp hue mixed into white at 3, 6, 9, 13 or 18 %; an empty
cell gets 1 % into `--sunk`. Chips sit top left, 4px apart: every chip **28 × 22px**
whatever its digits, 6px radius, 11.2px bold tabular numerals centred, filled in five
ramp steps (14, 30, 52, 76, 100 % of the hue into white), white text on the two darkest.
A chip that is named beside the raster is lifted: a 2px white ring and a 0 3px 8px −1px
shadow of ink at 35 %, moved up 1px; never an ink ring. A chip that carries a name
instead of a number (`.n.nm`) is as wide as its name, 8px padding, 10.9px semibold. Every
chip shows its id and name on hover (`assets/chips.js`). Under the grid the horizontal
axis in 11.2px `--muted`, then a key line in 11.5px `--muted`: five 16 × 10px ramp
swatches with what they measure, one lifted chip with what lifting means, and what the
number is ("number = entry in the register 3.3").

## 7. Highlight tile

One per screen, for the item or list the page points at: a lifted tile with a 2px fade
border (the white tile fill on the padding box, the fade on the border box) and, at the
top, a filled fade chip: 9.9px bold white capitals, letter-spacing 0.06em, 3px 10px
padding, fully rounded, 10px above the content ("Highest impact", "Recommended").
Choices inside it (the answers to a question) are buttons as wide as their words, side by
side and wrapping, never full-width bars.

## 8. Side list

The short list beside an exhibit, inside a tile: three to six items, one line each,
34px high, a 1px `--hair` line between them, 13.4px. A line is the id in bold tabular
(2.4em wide), the name in semibold, and at most one value on the right in 12.2px
`--muted`. A group label row is 9.6px bold capitals in `--muted`, letter-spacing 0.14em.
A note under the list is 12.2px `--muted` after a hairline. The list never repeats items
shown as cards on the same page.

## 9. Group cards

A row of up to four lifted cards, 14px apart, 16px 18px padding. The head is the group
name in 14.7px bold (line-height 1.3) and, on the right, its count in 20.8px bold,
letter-spacing −0.03em, tabular, in solid `--num`. Under it one sentence in 13.1px
`--ink-2`, led by a quiet tag when the grouping is a guess: 9.6px bold capitals on
`--sunk` in `--muted`, fully rounded, 1px 6px padding ("assumption"). The members are
named in the exhibit or list that follows, not on the card.

## 10. Table

A table sits on a lifted tile with 4px 8px padding. Header cells are 10.2px bold
capitals, letter-spacing 0.12em, `--muted`, with a 1px `--line` under them; body cells are
13.8px with 11px above and below, 16px to the right, a 1px `--hair` between rows and none
under the last. The name cell holds the name in semibold and a short line in 12.5px
`--muted`. One column carries colour, the status, as a chip: 11.5px semibold, 2px 9px
padding, fully rounded, in the status set (good, watch, bad) or neutral `--sunk`.

## 11. Empty state

One box per run of missing parts, never filler, always grey (never a status or brand
colour): a 2px dashed `--faint` line on the left,
12px padding, 13.8px `--muted` text saying what is missing and where it would come from,
led by a label in 9.6px bold capitals, letter-spacing 0.1em ("not written yet").

## 12. Colours and type

A page uses the accent, one semantic set and greys: at most three hue families on a
screen, a ramp of one hue counted as one. A monitoring board (§1) shows process states
and may use five: the accent plus done, running, warn and bad; it says so with
`<html data-board="monitoring">`, which the check reads. The brand (§ Brand in SKILL.md) sets the accent,
the fade, the ramp hue and the font; the neutrals stay.

| Token | Light | Dark | Role |
|---|---|---|---|
| `--paper` | `#FDFDFB` | `#0E0E10` | page ground |
| `--surface` | `#FFFFFF` | `#18181B` | tiles |
| `--ink` | `#0E0E10` | `#FDFDFB` | titles, names, the open tab |
| `--ink-2` | `#3A3A3D` | `#D6D6D1` | body text, the board name, the eyebrow |
| `--muted` | `#6A6A67` | `#A3A39D` | points line, tabs, labels, notes |
| `--faint` | `#9C9B96` | `#6F6F6B` | tabs that do not exist yet, footers |
| `--line` | `#D9D8D2` | `#54545A` | under table headers |
| `--hair` | `#E5E4DE` | `#3A3A40` | header edge, section line, rows |
| `--sunk` | `#F4F3EF` | `#232327` | tags, neutral chips, faces, empty cells |
| `--accent` | `#1F6F5C` | `#5FBFA6` | the neutral default; a brand replaces it |
| `--warn` / `--warn-bg` | `#B45309` / `#FDF0E3` | `#FDD663` / `#3A2C08` | watch: waiting, at risk |
| `--bad` / `--bad-bg` | `#B3261E` / `#FBEAE7` | `#F28B82` / `#3B1513` | bad: late, failed, the highest risk step |
| `--done` / `--done-bg` | `#1E8E5A` / `#E3F3EA` | `#5CC98F` / `#123224` | done well: a step or check that finished clean, a trend that converges |
| `--run` / `--run-bg` | `#2563A8` / `#E6EEF8` | `#7DB3EE` / `#16263A` | busy: running, in progress; never green, which reads as done |

**The fade** is the brand accent as a gradient of two or three stops, left to right
(top to bottom for a spine). It goes in exactly six places: the open tab's underline,
the subject word of the title, the points-line dots, the 5px bar on exhibit tiles, the
highlight tile's border and chip, the decision box's spine. The eyebrow dot and the open
filter pill's dot are the solid accent. Nowhere else, and never on numbers. In the dark
theme the fade takes the profile's `fade_dark` stops (lifted, so they read on
near-black), else the dark accent.

**Numbers** (section numbers, contents numbers, card counts) are solid `--num`: the
fade's middle stop when the brand has a three-stop fade, else the accent; in the dark
theme the middle stop of `fade_dark`.

**Process colours.** A board that tracks steps, runs or rounds shows each step's state:
done well `--done` (green: concluded), running `--run` (blue), a gate or check that said
no `--warn` (its marks, dots and squares, in a clear orange `#E8770E`, never brown), failed `--bad`, skipped or not run `--faint`. Green is never "running". A
trend of open problems is `--done` with the word "converging" while it falls, `--warn`
with "not converging" while it is flat or rising; a cost trend stays neutral.

**Good** is the accent at 12 % on white. **When the accent collides with a status hue**
(a red or amber accent; `starter.py` decides by hue and writes the tokens, by hand
`<html data-accent-red>`): good is ink on `--sunk`; "needs you" is the accent as a solid
fill with a white dot (`.chip.you`; in the dark theme dark text on the lifted accent); "failed" is the bad tint with a cross (`.chip.bad`),
so the two never share a treatment; scores use the wine or deep end of the fade as their
ramp, never the flat accent, so a top score does not read as an alarm.
**The ramp** is the accent unless the brand sets `ramp`; with a colliding accent and no
`ramp`, the fade's deep stop. A raster whose one code is a risk may use the accent itself.

**Greys on the paper** are tokens, never fixed ink at an alpha, so they turn in the dark
theme: `--track` (a filter track, ink 7 % / white 8 %), `--rule` (the tab hairline, ink
12 % / white 14 %), `--inset` (a face's edge, ink 6 % / white 8 %). The dark tokens are
written once, under `prefers-color-scheme`; the starter copies them under
`[data-theme="dark"]` for pages with a theme toggle, and `data-theme="light"` keeps a
page light.

**Type:** one family, the brand font (bundled as a local woff2 from the profile's
`font_file`, never loaded from the network) or `Inter, ui-sans-serif, -apple-system, "Segoe
UI", Helvetica, Arial, sans-serif`; body 15.2px, line-height 1.55; numbers tabular. Sizes
on a page: 21.6 title, 16.3 section heading, 14.4 points and leads, 13.8 tabs, table and
body in tiles, 12.5 contents, 11.2–11.8 axes and asides, 9.6–10.9 capitals. Weights 400,
500, 600, 700.

## 13. Never

1. Pills or a grey track for page navigation; a second header row of tabs.
2. An ink-filled chip, pill or ring for "selected".
3. Fade text on numbers; a gradient on a whole title; flat brand red for anything but a
   warning or the highest risk step.
4. A count as a title ("53 risks …"), the same number in three heads, an audience label
   in the eyebrow.
5. Flat outlined boxes where a tile belongs; a heavy rule above a section.
6. Chips of different widths in one raster; numbers off centre.
7. Shapes or colours invented per item as faces; black or generic icons; emoji.
8. The brand mark as a decoration on every row; it marks the one highlighted item.
9. The same items as cards and as a list on one page.
10. More than three hue families on a screen; a colour without a key.
11. Text cut off or running out of its box; `#000` text or a `#FFFFFF` page ground.

## 14. Values the test holds

`tests/test_house_style.py` checks that each rule in `assets/starter.css` carries these
declarations.

| Part | Selector | Declaration |
|---|---|---|
| header | `.top` | `border-bottom: 1px solid var(--hair)` |
| header | `.top-row` | `padding: 0 32px` |
| header | `.brand img, .brand svg` | `height: 22px` |
| header | `.brand .board` | `font-size: .74rem` |
| header | `.tabs a, .tabs span.off` | `font-size: .86rem` |
| header | `.tabs a, .tabs span.off` | `padding: 0 12px` |
| header | `.tabs a.on` | `font-weight: 600` |
| header | `.tabs a.on::after` | `height: 2px` |
| header | `.tabs a.on::after` | `bottom: -1px` |
| header | `.tabs .sep` | `margin: 14px 12px` |
| left column | `main.paged` | `grid-template-columns: 216px minmax(0, 1fr)` |
| left column | `.toc-name` | `font-size: .86rem` |
| left column | `.toc` | `font-size: .78rem` |
| left column | `.toc b` | `min-width: 2.3em` |
| page head | `.eyebrow` | `font-size: .66rem` |
| page head | `.eyebrow` | `letter-spacing: .16em` |
| page head | `h1.title` | `font-size: 1.35rem` |
| page head | `h1.title` | `letter-spacing: -.018em` |
| page head | `.points` | `font-size: .9rem` |
| page head | `.points span + span::before` | `width: 6px` |
| section | `.sec-head` | `border-top: 1px solid var(--hair)` |
| section | `.sec-head` | `padding-top: 16px` |
| section | `.sec-no` | `font-size: .68rem` |
| section | `.sec-title` | `font-size: 1.02rem` |
| section | `.sec-title` | `font-weight: 600` |
| tile | `:root` | `--radius: 14px` |
| tile | `.fig::before` | `height: 5px` |
| tile | `.split` | `grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr)` |
| raster | `.raster .cell` | `min-height: 62px` |
| raster | `.n` | `width: 28px` |
| raster | `.n` | `height: 22px` |
| raster | `.n` | `font-size: .7rem` |
| raster | `.n.hi` | `box-shadow: var(--chip-lift)` |
| highlight | `.rec` | `border: 2px solid transparent` |
| highlight | `.chip.fade` | `font-size: .62rem` |
| side list | `.lines li` | `min-height: 34px` |
| side list | `.lines li` | `font-size: .84rem` |
| cards | `.count` | `font-size: 1.3rem` |
| cards | `.count` | `color: var(--num)` |
| cards | `.tag` | `background: var(--sunk)` |
| table | `th` | `font-size: .64rem` |
| table | `table` | `font-size: .86rem` |
| empty | `.empty` | `border-left: 2px dashed var(--faint)` |
| colour | `.chip.you` | `background: var(--accent)` |
| colour | `.eyebrow::before` | `background: var(--accent)` |
| type | `body` | `font: 400 .95rem/1.55 var(--font)` |
