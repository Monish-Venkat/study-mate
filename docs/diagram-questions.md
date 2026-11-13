# Questions that return a textbook diagram

Every question below was run against the live index on 13 Nov 2026 (522
figures, 8,191 vectors) and the figure it returns is recorded beside it.
Set the **subject and year** as listed — the index is filtered by both, so the
right question under the wrong year returns nothing.

The score is cosine similarity against the figure's caption. The floor is
0.55; anything below that shows no figure at all, which is deliberate — a
plausible-but-wrong diagram beside a correct answer is a mistake a student
cannot detect.

## Biology — 1st PUC (163 figures, the best covered)

| Ask | Returns | Score |
|---|---|---|
| Draw a labelled diagram of the human heart | Figure 15.2 Section of a human heart | 0.82 |
| Draw a labelled diagram showing blood circulation in humans | Figure 15.4 Schematic plan of blood circulation | 0.82 |
| Draw a labelled diagram of the vertebral column | Figure 17.7 Vertebral column (right lateral view) | 0.80 |
| Draw a labelled diagram of a cnidoblast | Figure 4.7 Diagrammatic view of Cnidoblast | 0.79 |
| Draw a labelled diagram of T.S. of a dicot stem | Figure 6.4 T.S. of stem Dicot / Monocot | 0.78 |
| Draw a labelled diagram of the cell cycle | Figure 10.1 Diagrammatic view of cell cycle | 0.75 |

## Biology — 2nd PUC (18 figures)

| Ask | Returns | Score |
|---|---|---|
| Draw a labelled diagram of the female reproductive system | Figure 3.3 Diagrammatic sectional view | 0.68 |

## Physics (277 figures, the largest set)

| Ask | Year | Returns | Score |
|---|---|---|---|
| Draw a diagram showing a system of three charges | 2nd | FIGURE 1.8 A system of three charges | 0.88 |
| Draw a ray diagram for a convex lens | 2nd | FIGURE 9.17 Tracing rays through convex lens | 0.77 |
| Draw a diagram of heat conduction through a bar | 1st | Fig. 10.14 Steady state heat flow by conduction | 0.73 |
| Draw a labelled diagram of an AC generator | 2nd | FIGURE 6.16 AC Generator | 0.67 |
| Draw a diagram of the scalar product of two vectors | 1st | Fig. 5.1 The scalar product of two vectors | 0.68 |

## Chemistry (59 figures)

| Ask | Year | Returns | Score |
|---|---|---|---|
| Draw a labelled diagram of a cathode ray discharge tube | 1st | Fig. 2.1 A cathode ray discharge tube | 0.86 |
| Draw the shapes of molecules with no lone pair on the central atom | 1st | Fig. 4.6 Shapes of molecules | 0.78 |
| Draw a diagram of a nickel-cadmium rechargeable cell | 2nd | Fig. 3.11 Rechargeable nickel-cadmium cell | 0.77 |
| Draw a diagram showing the formation of H2O molecule | 1st | Fig. 4.14 Formation of H2O molecule | 0.75 |

## Mathematics (5 figures — see the gap below)

| Ask | Year | Returns | Score |
|---|---|---|---|
| Draw a right handed coordinate system | 2nd | Fig. 10.22 Right handed coordinate system | 0.73 |
| Draw a diagram for the vector product of two vectors | 2nd | Fig. 10.22 Vector product definition | 0.61 |

---

## Known gaps, found while testing these

**Write the formula the way the book does, not the way you say it.** "Formation
of a water molecule" returns nothing at 0.52, while "formation of H2O molecule"
returns the right figure at 0.75. The caption says H2O, and the embedding does
not bridge the two. This is the most likely reason a reasonable question comes
back empty.

**Mathematics is effectively uncovered.** Only 5 figures were extracted, and
three of them are chapter-opening pages rather than diagrams. "Draw a diagram
for relations and functions" returns Fig. 2.1 at 0.60 — which is the chapter
title page carrying a **portrait of Leibnitz**. That clears the floor and will
be shown as though it were a diagram. Maths figures are vector art rather than
embedded raster images, which is why so few were extracted.

**Some captions carry PDF junk.** A few read like `Unit 4.indd 122 9/12/2022`
or, where the source PDF uses a custom font encoding, as mojibake such as
`3DpHU FKURPDWRJUDpK\`. Those figures are in the index but are close to
unsearchable, because the caption is what gets embedded.

**Not everything is there.** "Draw a labelled diagram of the human eye" returns
nothing — correctly, since no such figure was extracted. An empty result means
the figure is absent, not that the question was poor.

## Reproducing this

With the backend running on port 8000:

```bash
curl -s "http://127.0.0.1:8000/figures/search?q=human+heart&subject=biology&level=1st&k=3" | python -m json.tool
```
