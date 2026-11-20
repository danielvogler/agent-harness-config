# Brief for a visual

Copy into the repo (beside the page or in its `docs/`), fill every field, and show it to
the person before building. A field left empty is a question to ask, not a guess to make.

```markdown
# Brief: <what is being made>

## Reader
Who opens it, what they know already, what they decide or do after reading.

## Pages or pictures
| Page | What it shows (one line, becomes the title) | The 3-4 points |
|---|---|---|
| Summary | ... | ... |

## Reference
Approved pictures already in the repo come first (README hero graphs, architecture
pictures, an earlier page): name them here and take their palette, faces and tiles.
1. `<path to a screenshot or file of a page the person approved>`
   Traits to copy: <e.g. the status column, the page head, the score dots>
   Traits not to copy: <e.g. its 17 tabs>
2. ...

An adjective is not a reference ("McKinsey level", "Apple quality", "clean"). Ask for a
file. A reference named and then forbidden ("like X, but not its look") is not one either.

## Colour code
| Colour | Means |
|---|---|
| accent (from `.house-style.json`) | the proposed or current one |
| status set | agreed / in work / waiting / late |
| <part colour> | <part>, the same in every picture |

## Variant pick
| Variant | Coloured marks with a meaning | Named items | Picked |
|---|---|---|---|
| A | ... | ... | by the person, or by the most marks and names when no person picks |

## Faces
Where the logos and pictures come from: <folder, vendor press kits, the product's own>.

## Language
English / German (Swiss spelling: yes or no).

## Done when
`check_visual.js` exits 0 on every page and picture, light and dark; the review list
against the reference has no open trait; the person picked the variant.
```

## Variant pick rule

When no person can pick (a loop, a subagent), count per variant and take the highest.

1. **A coloured mark with a meaning** is one element whose colour a legend or the colour
   code explains: a status chip or dot, a score dot, a filled number chip, a ramp-tinted
   cell that holds an item, a group-coloured dot or face, a coloured delta. Not counted:
   the accent underline of the open tab, the dots in the points line, outlines, logos,
   decoration. A filled fade chip on the highlight tile counts as a mark.
2. **A named item** is a distinct item the reader sees by name, not only by id: a card
   title, a top-list entry, a table row's name. Count each item once, however often it
   appears; showing the same five items as cards and again as a list adds nothing.
3. **Score** = marks + 2 × named items. Tie-break, in order: the closer fit to
   [look.md](look.md) part by part (count the parts that match), then fewer words on the
   first screen, then fewer hue families.
4. Write the counts and the pick into the brief's "Variant pick" table.

## A filled brief, in German

```markdown
# Brief: Risiko-Seite der Gruppe

## Leser
Verwaltungsrat und Geschäftsleitung; kennen die Firma, nicht die Methode. Entscheiden,
welche drei Risiken im Gespräch zuerst behandelt werden.

## Seiten
| Seite | Was sie zeigt (wird zum Titel) | Die 3–4 Punkte |
|---|---|---|
| Risiko | 53 Risiken nach Eintritt und Auswirkung, von aussen geschätzt | 7 mit 12 Punkten · 5 mit Auswirkung 5 · nicht intern geprüft |

## Referenz
1. `docs/reference/uebersicht.png` (vom Verwaltungsrat freigegeben)
   Übernehmen: Kopfzeile mit Punkten, Raster mit roter Stufe, Liste der fünf höchsten
   Nicht übernehmen: die zweite Navigationszeile

## Farbcode
| Farbe | Bedeutet |
|---|---|
| Akzent | die vorgeschlagene Reihenfolge |
| Rot in fünf Stufen | Punkte = Eintritt × Auswirkung |
| Statusfarben | geprüft / offen / fehlt |

## Varianten
| Variante | Farbmarken mit Bedeutung | Benannte Einträge | Gewählt |
|---|---|---|---|
| A Raster mit Stufen | 94 | 13 | ja (höchste Summe) |
| B Karten zuerst | 99 | 8 | nein |

## Gesichter
Keine Logos erlaubt: Kürzel auf der Farbe der Gruppe.

## Sprache
Deutsch, Schweizer Schreibweise (ss statt ß).

## Fertig, wenn
`check_visual.js` hell und dunkel 0 meldet, die Liste gegen die Referenz keinen offenen
Punkt hat und die Variante gewählt ist.
```
