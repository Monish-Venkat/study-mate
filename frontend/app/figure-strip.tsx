'use client';
import {useEffect, useState} from 'react';

/* Diagrams taken from the student's own prescribed textbook.
 *
 * A study map shows how ideas connect; it is not what a board paper means by
 * a diagram. These are the actual figures — the heart, the ray diagram — read
 * out of the indexed NCERT and PUC books, carrying the file and page so they
 * can be checked like any other claim.
 *
 * Nothing renders unless a caption clears the relevance floor on the server.
 * A plausible-but-wrong diagram beside a correct answer is a mistake a
 * student has no way to detect, so silence is the safer failure.
 */
type Figure = {
  id: string; label?: string; caption?: string;
  source?: string; page?: number | string;
  width?: number; height?: number;
  approximate?: boolean; plate?: boolean; rendered?: boolean; url: string;
};

type Group = {key: string; plate: boolean; items: Figure[]};

/* A plate — "Figure 2.4 (a) Dinoflagellates (b) Euglena (c) Slime mould" — is
 * one caption over several panels, and which panel is which is not knowable
 * from the PDF. Printing that caption under each panel separately reads as
 * three identical figures and quietly implies each one IS a dinoflagellate.
 * The panels are therefore shown together under the caption once, as the book
 * prints them.
 */
function group(figures: Figure[]): Group[] {
  const out: Group[] = [];
  for (const figure of figures) {
    const key = figure.plate ? `plate:${figure.source}:${figure.label}` : `one:${figure.id}`;
    const last = out[out.length - 1];
    if (last && last.key === key) last.items.push(figure);
    else out.push({key, plate: !!figure.plate, items: [figure]});
  }
  return out;
}

export default function FigureStrip({query, subject, level}: {query: string; subject: string; level: string}) {
  const [figures, setFigures] = useState<Figure[]>([]);

  useEffect(() => {
    if (!query.trim()) return;
    let live = true;
    const params = new URLSearchParams({q: query.slice(0, 300), subject, level, k: '3'});
    fetch(`/api/modules/figures/search?${params}`)
      .then(r => r.ok ? r.json() : {figures: []})
      .then(d => { if (live) setFigures(Array.isArray(d.figures) ? d.figures : []); })
      .catch(() => { if (live) setFigures([]); });
    return () => { live = false; };
  }, [query, subject, level]);

  if (!figures.length) return null;
  const groups = group(figures);

  return <section className="figure-strip" aria-label="Diagrams from your textbook">
    <h3>From your textbook</h3>
    <div className="figure-row">
      {groups.map(g => {
        const head = g.items[0];
        const alt = g.plate
          ? `${head.label || 'Figure'}, one panel of a plate showing: ${head.caption}`
          : head.caption ? `${head.label || 'Figure'}: ${head.caption}` : 'Textbook figure';
        return <figure key={g.key} className={g.plate ? 'figure-plate' : undefined}
                       style={g.plate && g.items.length > 1 ? {gridColumn: '1 / -1'} : undefined}>
          <div className="figure-panels">
            {/* Served through the module proxy, which streams the PNG rather
                than parsing it as JSON. Plain <img>: these are arbitrary-sized
                scans from a PDF, so Next's image optimiser has nothing to
                contribute. */}
            {g.items.map(figure => <img key={figure.id}
                 src={`/api/modules/figures/${figure.id}.png`}
                 alt={alt} loading="lazy"/>)}
          </div>
          <figcaption>
            <b>{head.label}</b> {head.caption}
            <small>
              {head.source}{head.page ? ` · page ${head.page}` : ''}
              {g.plate
                /* Not a hedge about the caption: the caption is exactly what
                   the book prints. It is a statement that the book labels the
                   group, not the individual panels. */
                ? <em> · the book captions these panels together; it does not say which is which</em>
                : head.approximate && <em> · caption matched by position on a multi-figure page</em>}
              {/* A line-art figure has no image to lift, so it is cropped from
                  the rendered page and the edges are inferred. */}
              {head.rendered && <em> · cropped from the page; the top edge may be trimmed</em>}
            </small>
          </figcaption>
        </figure>;
      })}
    </div>
  </section>;
}
