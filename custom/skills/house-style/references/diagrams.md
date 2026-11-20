# Diagrams, hero graphs, banners and slide pictures

The rules for pictures, written from 258 corrections the person made to diagrams and
from the hero graphs they kept. Three quarters of the corrections were findable without
them: a third by a script on the rendered picture, the largest share by a reviewer
looking at it with their questions. A quarter needed knowledge of the system, and those
came first in every long run. So a diagram starts from a written system sheet, follows
the anatomy below, and is checked on the picture, not on its source.

Shared with dashboards: the neutrals and type of [look.md](look.md) §12, the wording of
[writing.md](writing.md), the brand lookup in SKILL.md. `assets/example-flow-light.png`
and `-dark.png` are a neutral picture drawn with `scripts/diagram.py`.

## Contents

1. The system sheet, before any picture
2. Which picture for which job
3. Tile
4. Arrow
5. Part colours and the key
6. Logos and marks
7. Step numbers and the legend
8. Labels and text
9. Size, width, light and dark
10. Mermaid
11. Slides and one-pagers
12. Never

## 1. The system sheet, before any picture

Every repo with more than one diagram has `docs/assets/system.md` (or the `parts`
module of its generator), written from the code before the first picture:

1. The parts, each with its name as a reader outside the team says it, its code path,
   its colour, its position (left, middle, right; top, bottom) and its symbol.
2. What starts it, and the order of the steps.
3. The words that stay inside the team and never appear in a picture.

Every picture of the repo reads the sheet: the same part has the same name, colour,
position and symbol in every diagram, and a small key of the whole system sits beside
each detailed picture. A diagram whose mechanism was not written down first took up to
eight rounds; none with a sheet needed a mechanism correction.

## 2. Which picture for which job

| Picture | Shows | Leaves out |
|---|---|---|
| banner | the name, one sentence, at most six items | how it works |
| hero graph | what goes in, the system, what comes out, in three columns read left to right | code paths, every option |
| architecture | what runs where: zones as places, tiles per service, the main flow numbered | the call graph |
| process map | steps of a process as tiles left to right, one row per lane | system internals |
| flow, sequence, state | Mermaid (§10), at most twelve nodes, one screen high | anything a hero graph should carry |

A design's main picture is drawn, not Mermaid.

## 3. Tile

White `--surface`, 12px radius, a 1px hairline in `#DADCE0` (dark: `--line`), and the
soft shadow of a lifted tile; a tile of a part takes its part's 1.5px outline and its
pastel tint (the part colour at about 12 % on white) instead. Inside, 16px padding: the
symbol or logo top left (20–24px), the title in 14px semibold `--ink` saying what the
part is for, the product name under it in 12px `--muted`, a 1px hairline, then at most
two lines of 12px `--ink-2` on what runs there. A part that is not running yet has a
dashed outline (4px dash, 3px gap). A status chip (`live`, `planned`, `to choose`) sits
bottom right, 10px bold capitals, fully rounded. A group of tiles sits on a zone: a
tinted area (`--sunk` or the part tint at 40 %), 16px radius, its name in 10.6px bold
capitals top left. The top tile of a hero may carry the fade as a 5px bar on its top
edge, like a dashboard's exhibit tile.

## 4. Arrow

Straight lines, orthogonal where they turn, 2px thick, never thinner; a filled triangle
head of 9px at least. The main flow is in the part colour of where it starts, or the
accent; supporting flows are `--muted` grey. An arrow ends exactly at the edge of the box
it points to, never short of it and never through a tile; it runs in the gutters. A label
on an arrow is 12px `--muted` on a small white plate. One arrow style per picture: no
mix of curved, swooping and straight; no arrow drawn twice.

## 5. Part colours and the key

Up to four part colours plus ink, each with one meaning, the same in every picture and
in the code; a fifth meaning becomes a grey. The liked set used blue `#2F6FBF`, violet
`#7D4FB0`, red `#D2402C` and teal `#007B83`, each with its tint (`#E8F0FA`, `#F3EDF9`,
`#FBEAE7`, `#E0F2F1`); a brand replaces them with its own, the accent first. Status keeps
the status set; everything else is ink and neutrals. A key along the bottom shows one
swatch per colour and says the rule in one line ("One colour per part, the same in
every diagram"). Hot is red and cold is blue where the subject has temperature. No
colour without a meaning, no thick black outlines.

## 6. Logos and marks

A service tile carries the service's real logo; without one, a 20px rounded square in
the service's colour with its initial, or the cloud hexagon for a cloud product. A
brand's own logo is checked where it is shown: in a 40px circle (an avatar), on an app
badge, at README width. Shapes inside one mark are of one family (all round or all
square). No clip-art, no generic or black pictograms, no emoji.

## 7. Step numbers and the legend

The main steps are numbered: a 18px circle, filled in the flow colour, the white number
centred in 11px bold. The legend lists the numbered steps in one line each ("1 The
planner uploads the timetable"), and the chips and line styles in a second row. Steps
nobody can find in the docs are a bug: every number in the picture is a heading or a
numbered line in the text beside it.

## 8. Labels and text

1. A picture has an eyebrow (accent dot, 10.6px bold capitals) and a title that is the
   question it answers, then the picture; no paragraph between them.
2. Labels are short nouns or verb phrases ("uploads", "Plan service"); no internal
   words, version names or ticket numbers in a public picture.
3. Text never leaves its box; a label that does not fit moves the tile, not the font.
4. Labels use the brand font of the page or README they sit in (the profile's `font`,
   bundled locally); a Mermaid chart's `fontFamily` puts the brand font first.
5. Labels keep 11px at the size the picture is shown (§9).

## 9. Size, width, light and dark

1. A README picture is at most 1280px wide and keeps at least 55 % of its canvas as
   paper; the liked set had a median of three hues and 43 text elements, the rejected
   set five hues and 78.
2. It is judged at the width it is shown: about 830px in a GitHub README column, so a
   1280px picture shrinks by 0.65 and its 14px labels show at 9px. Aim for 11px shown:
   draw labels at 16px or more for a full-width README picture. The check fails a
   median label below 7.5px or any label below 5px at the shown width (`--shown 830` by
   default), and a picture wider than 1320px.
3. Always a light and a dark file, embedded with `<picture>`; the dark accent is the
   light one lifted.
4. A script or generator draws it, beside the picture; a test regenerates it and fails
   on a diff, so the picture cannot go stale.

## 10. Mermaid

For flows, sequences and state machines only. The person's "Google style" values, with
straight connectors (a curve of `basis` draws the swooping arrows they rejected):

```text
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Google Sans, Roboto, Helvetica Neue, Arial, sans-serif","fontSize":"14px","primaryColor":"#FFFFFF","primaryTextColor":"#202124","primaryBorderColor":"#DADCE0","lineColor":"#5F6368","secondaryColor":"#F1F3F4","tertiaryColor":"#F1F3F4","clusterBkg":"#F8F9FA","clusterBorder":"#DADCE0","edgeLabelBackground":"#FFFFFF"},"flowchart":{"curve":"linear","nodeSpacing":40,"rankSpacing":56,"useMaxWidth":true}} }%%
```

Left to right (`flowchart LR`) when it fits one screen; at most twelve nodes; draw the
trust boundary as a subgraph, colour only the node where a person approves.

## 11. Slides and one-pagers

1. One layout for every slide: same title position, same tile colours, same text size.
2. Text bigger, tiles smaller: a slide is read from the back of the room.
3. A one-pager starts with an overview picture, then at most six blocks per section, in
   the order a reader goes through them.
4. A one-pager or HTML guide uses the dashboard header, page head and section dividers.

## 12. Never

1. A mechanism drawn before it was checked against the code.
2. Curved swooping arrows, arrows that stop short or cross a tile, mixed arrow styles.
3. More than four part colours; a colour that changes meaning between pictures; a
   colour without a key.
4. Text overflowing a tile; labels below 11px where the picture is shown.
5. Boxes stretched wide with one word in them; the same white box repeated ("poor and
   monotonous"); a page of text drawn as a picture.
6. Thick black outlines, clip-art, emoji, black pictograms.
7. Numbers in circles off centre; steps in the picture that the text does not have.
8. A Mermaid chart as a design's main picture, or one taller than a screen.
9. A picture judged only in the agent's own preview or source, never at the size and
   in the place it is shown.
