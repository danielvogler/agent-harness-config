# Dashboards, boards, reports and one-pagers

When to use which part of [look.md](look.md), and the rules for a whole page. Every
part's look is written out there; `assets/starter.css` implements it and
`assets/example.html` uses every part.

## Contents

1. Improve an existing dashboard in place
2. The frame of every page
3. Which exhibit for which content
4. Colour on a page
5. Each item once
6. Missing content
7. What the person rejected
8. Decisions and where they live

## 1. Improve an existing dashboard in place

When the repo already has a dashboard, improve it; never rebuild it from scratch. Keep
what the person liked (logo, navigation, lifted tiles, the left column, any part they
praised) and change only what breaks a rule here or in [look.md](look.md). List the
changes in the brief first, one line each with the rule it fixes. Copy the page's own
stylesheet in, then layer the starter's parts over it, part by part.

An engine-driven app (one stylesheet and shared markup render every page) is changed in
the engine first, then page by page; the variants step is skipped there. When the repo
has build or loop prompts, they change in the same commit, or the next round writes the
old look again.

## 2. The frame of every page

1. **Header** (look.md §1): logo with the board name under it, one row of text tabs.
   Groups first, then only the open group's pages. A product with two areas uses the
   same tabs; a flat set of up to seven pages has no groups. Only pages that exist are
   links; a planned one is faint text.
2. **Left column** (§2) on any page of more than three sections: the page name, then
   its numbered sections. It is navigation, not a second head.
3. **Page head** (§3): eyebrow, title, points line; three lines, then the first section.
   Key numbers go into the points or the first exhibit, never a KPI strip under the head.
4. **Sections** (§4), numbered by page ("3.1"), each with an optional lead sentence and
   one exhibit.
5. **Labels** are short nouns; a button says what it opens ("Show overview map").

## 3. Which exhibit for which content

| Content | Exhibit |
|---|---|
| items placed on two scales (likelihood × impact, effort × value, overlap × strength) | raster (§6) in a fig tile, with a side list (§8) of the three to six that matter |
| a few groups or options, each with one sentence | group cards (§9) |
| many items with attributes, a register | table (§10) on a tile, one coloured status column |
| the one thing the page proposes or points at | the highlight tile (§7), once per screen |
| a decision | the decision box: a lifted tile with a 5px fade spine on the left |
| how the pages or steps fit together | a page map: numbered lifted nodes, quiet grey arrows, left to right |
| an in-page choice (filter, view) | the segmented filter: grey track, the open pill white and lifted with an accent dot |

A raster's chips carry the ramp step of their score; when the position should say which
group an item belongs to, the chips carry the item's short name (`.n.nm`) in the ramp of
its score and the side list groups the names. A chip never stands alone with a code the
reader cannot decode: the hover names it and the key says what the number is.

## 4. Colour on a page

1. The accent, one semantic set and greys, at most three hue families on a screen.
2. The fade goes in its six places (look.md §12) and nowhere else.
3. Only the one exhibit that encodes a status or score carries the semantic set or the
   ramp; it carries it on many small marks (cells, chips, one table column), not on big
   fills.
4. A page of only ink and grey "looks the same everywhere" and fails the check; so does
   one with several codes on one screen.
5. The same item has the same status on every page; a colour without a key is a bug.

## 5. Each item once

Either an exhibit with a side list, or the items as cards; never both for the same items
on one page. A list line is one line (id, name, one value); a sentence per item opens on
click (`<details>`) or belongs in the table. The item that matters most sits in the
highlight tile, so the list is not dry.

## 6. Missing content

Missing content (not delivered, not computed, lost) is an empty-state box (look.md §11):
what is missing and where it would come from, in grey only. Several missing sections in a
row are one box that lists them, and the left column still lists each of them. Never a grey card that looks like content, never filler. A cut-off
source sentence keeps its cut, marked as cut.

## 7. What the person rejected

1. "Super bland boxes": tiles that all look alike, grey on white, flat outlines.
2. "Everything black and white and looks the same."
3. "Random colors all over the place": several codes on one screen.
4. A pill switch for navigation ("gimmicky"); groups and pages styled differently
   ("disjointed"); a black active pill ("too strong").
5. Count titles, AI statements, audience labels; the verb part of a title carrying the
   fade instead of the subject.
6. Seventeen tabs in a row; three navigation levels at once; a head of five lines.
7. Chips of different widths, numbers off centre, an ink ring round a chip; codes the
   reader cannot decode.
8. Invented shapes as faces; the brand mark scattered as decoration.
9. The same items as cards and as a list; a paragraph per list item.
10. Fade text on numbers.

## 8. Decisions and where they live

| Decision | Where |
|---|---|
| The look in exact values, each part one paragraph | look.md §1–§12 |
| One header row: logo and board name, text tabs, only the open group's pages | look.md §1 |
| The left column opens with the page name; sections aligned under it | look.md §2 |
| Title names the subject; the subject word carries the fade; no count titles | look.md §3, writing.md §1 |
| Section divider: hairline, solid number, plain heading | look.md §4 |
| Every tile lifted; exhibit tiles with a fade bar | look.md §5 |
| Raster: one-hue ramp, 28px chips, white ring and lift, hover names, key line | look.md §6, `assets/chips.js` |
| Highlight tile with a fade border and chip, once per screen | look.md §7 |
| One line per list item; each item once | look.md §8, §5 here |
| Counts and numbers solid, not fade | look.md §9, §12 |
| Accent + one semantic set + greys, at most three hue families (checked) | look.md §12, `check_visual.js` |
| The fade in six places, flat brand red only for warnings; a colliding accent turns good to ink | look.md §12 |
| Brand from a named profile, else the repo, else neutral | SKILL.md "Brand" |
| Improve an existing dashboard in place | §1 here |
| Before and after labelled when the person compares two versions | SKILL.md "The review" |
