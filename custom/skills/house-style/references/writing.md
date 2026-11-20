# Writing on pages and pictures

What the words on a dashboard, a diagram or a slide say. The person stopped at AI
statements, verdicts in headlines and wishy-washy titles, and asked for neutral statements
that say what a page shows. Examples are in English and German; client pages are often
German. `banned-phrases.txt` holds the phrases `check_visual.js` fails on, and a repo adds
its own in `.house-style.json` (see SKILL.md).

## Contents

1. Page head: eyebrow, title, points
2. Bad phrase and what to write instead
3. Labels
4. Section heads and empty states
5. German

## 1. Page head

**Eyebrow**: the page's name, then its group or a few words of context. Small caps, no
sentence, no count, and no audience: "for the board" or "Für den Verwaltungsrat" says
nothing about the page (the check fails it).

| Good | Bad |
|---|---|
| Summary · Understand | Welcome to your dashboard |
| Open items · Due before the January board | For the board · 53 risks |
| Risiko · Bewerten | Für den Verwaltungsrat |

**Title**: one line naming the subject and the question in words. A reader who reads
only the title knows what is on the page. Not what wins, not what to think, and not a
count: a title that opens with a number ("53 risks of the group …", "15 vendors in four
groups …") fails the check. The subject word, and only it, is wrapped in `<span
class="em">` and carries the fade: "Which <em>risks</em> the group has to carry", not
"Which risks the group <em>has to carry</em>". A title with no subject word gets one
("Welche Wettbewerber der Gruppe Aufträge streitig machen").

| Good | Bad |
|---|---|
| Which risks the group has to carry | 53 Risiken der Gruppe nach Eintritt und Auswirkung |
| Welche Anbieter der Gruppe Aufträge streitig machen | 15 Anbieter in vier Gruppen, nach Überschneidung und Stärke |
| How the frontend stacks compare on cost, speed and fit | React wins on the canvas; Next.js wins once we sell |
| Which vehicles the depot should run from 2028, and what is still open | Battery buses: the clear path to a greener future |

**A number appears once**, in one place: a KPI or the points line. Not again in the
eyebrow, the title, a section title and a list head; the same number in three heads fails
the check.

**Points**: three or four facts, one line, divided by dots. Each is a number or a plain
statement, not an adjective.

| Good | Bad |
|---|---|
| Battery buses fit 31 of 34 routes · Night charging needs 4.2 MW · Two decisions due in January | Robust · Scalable · Future-proof |
| Account, sign-in, organisations, roles · One provider for all three tiers | A best-in-class identity experience |
| 12 open items · 3 late · 2 waiting on the utility | Lots of progress, some risks remain |

## 2. Bad phrase and what to write instead

| Instead of | Write |
|---|---|
| "X wins once we sell" | "Five stacks compared on cost, speed and fit"; the recommendation goes in a chip on the card |
| "seamless integration" | "Connects to the timetable export, no manual step" |
| "robust", "scalable" | the number: "handles 34 routes, tested to 60" |
| "unlock", "empower", "leverage" | the verb of what happens: "lets planners export", "uses the existing data" |
| "game-changer", "cutting-edge", "best-in-class", "world-class" | delete it, or name the comparison: "fastest of the three in the test" |
| "In today's fast-paced world" | delete the sentence |
| "It's not just X, it's Y" | "Y" |
| "From X to Y: …" | what the page shows |
| "might potentially", "arguably", "to some extent" | say it, or say what is unknown: "not tested in winter yet" |
| "AI-powered insights" | what is computed: "cost per route, from the timetable" |
| "the future of mobility" | the scope: "the 2028 depot" |

## 3. Labels

1. Neutral nouns, with what the group holds after a colon: "Identity and trust: account,
   sign-in, organisations, roles". Not "Trust layer that keeps everyone safe".
2. Say what a control opens: "Show overview map", not "Show map" or "Explore".
3. A stack, column or group of options gets its number and name at the top: "Stack 3 ·
   Svelte + Go", so the reader knows which one they look at.
4. The product's full name in the header, consistently, the same on every page.
5. One term for one thing across all pages; no synonyms for variety.
6. Status words are fixed: agreed, in work, waiting, late (en); vereinbart, in Arbeit,
   wartet, verspätet (de).

## 4. Section heads and empty states

Section heads say what the section holds:

| Good | Bad |
|---|---|
| 2 · Open items before the January board | Next steps |
| 1 · The three options, scored on what the board weighs | Section 1 · Overview |
| 3 · Kosten pro Jahr nach Variante | Abschnitt 3 · Die Zahlen |

Empty states say what is missing and where it comes from:

1. "No open items. New ones come from the weekly review."
2. "No score yet: the range test on route 12 is due 30 Nov."
3. "Keine offenen Punkte. Neue kommen aus der Wochenbesprechung."
4. "Noch keine Zahlen: Die Offerte des Netzbetreibers kommt bis 15. Dezember."

A missing part of an exhibit or a section is an empty-state box (see `dashboards.md`
§14) with a chip and one sentence:

5. "not yet · No cost per route yet. The figures come with the tender prices on 10 Jan."
6. "nicht erhalten · Die übrigen 51 Zeilen liegen in keiner Quelle vor; bekannt sind nur
   Nummer und Bewertung aus dem Raster."

## A title that breaks the rules

A repo's own build or loop prompt that asks for "a title that states a finding" or "one
thesis per view" is changed to these rules in the same change, so the next round keeps
them.

When the content arrives with a title that states a finding or a verdict ("Grosse
Verbünde kaufen Spezialisten zu"), rewrite it into what the page shows ("15 Anbieter in
vier Gruppen, nach Überschneidung und Stärke"), move the finding into the points line,
and keep the original in an HTML comment beside the title.

## 5. German

| Statt | Schreiben |
|---|---|
| "nahtlose Integration" | "Übernimmt den Fahrplan-Export, ohne Handarbeit" |
| "ganzheitlicher Ansatz" | was es umfasst: "Fahrzeuge, Laden und Depot in einem Plan" |
| "massgeschneiderte Lösung" | wofür: "für die 34 Linien des Depots" |
| "zukunftsweisend", "bahnbrechend" | streichen, oder den Vergleich nennen |
| "In der heutigen schnelllebigen Zeit" | den Satz streichen |
| "Variante B gewinnt" | "Drei Varianten nach Kosten, Risiko und Emissionen"; die Empfehlung als Chip |

Page heads in German:

1. Eyebrow: "Übersicht · Drei Varianten für das Depot".
2. Title: "Die drei Fahrzeugvarianten, ihre Kosten pro Jahr und was noch offen ist".
3. Points: "Batteriebusse decken 31 von 34 Linien · Nachtladen braucht 4,2 MW · Zwei
   Entscheide im Januar".

Write Swiss German spelling (ss, not ß) when the repo or client is Swiss; the banned list
holds both.
