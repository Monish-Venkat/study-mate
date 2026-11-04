"use client";
import {useCallback, useEffect, useRef, useState} from 'react';
import {DownloadSimple, ArrowsOutSimple, WarningCircle} from '@phosphor-icons/react';

let probe: CanvasRenderingContext2D | null = null;

/** Convert any CSS colour the browser understands into an sRGB hex string.
 *
 *  The design tokens are authored in OKLCH, and the browser serialises them
 *  through getComputedStyle as `lab(...)`. Mermaid's colour library cannot
 *  parse either notation and throws before it ever looks at the diagram, so
 *  the value has to be reduced to a form every library accepts. Painting one
 *  pixel and reading it back does that conversion in the browser's own colour
 *  code, rather than reimplementing OKLCH to sRGB here. */
function toHex(value: string): string | null {
  if (!probe) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    probe = canvas.getContext('2d', {willReadFrequently: true});
  }
  if (!probe) return null;
  try {
    probe.clearRect(0, 0, 1, 1);
    probe.fillStyle = '#000000';
    probe.fillStyle = value;
    probe.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = probe.getImageData(0, 0, 1, 1).data;
    if (a === 0) return null;
    return '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
  } catch {
    return null;
  }
}

/** Read a design token, so the diagram is themed by the stylesheet rather than
 *  by a second palette kept in sync by hand. */
function token(name: string, fallback: string) {
  if (typeof window === 'undefined') return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!value) return fallback;
  // --font-sans and similar are not colours; leave anything non-colour alone.
  if (!/^(oklch|lab|lch|color|rgb|hsl|#)/i.test(value)) return value;
  return toHex(value) ?? fallback;
}

/** Pin Mermaid's twelve section colours to four tints from this product's own
 *  palette, cycled. Branches stay distinguishable, and the diagram stops
 *  introducing hues that appear nowhere else in the interface. */
function sections() {
  const fills = ['--accent-soft', '--amber-soft', '--info-soft', '--positive-soft'];
  const defaults = ['#e8f0e7', '#f6efe2', '#eaeff8', '#e7f1ea'];
  const vars: Record<string, string> = {};
  for (let i = 0; i < 12; i++) {
    vars[`cScale${i}`] = token(fills[i % 4], defaults[i % 4]);
    vars[`cScaleLabel${i}`] = token('--ink', '#24362e');
    vars[`cScaleInv${i}`] = token('--ink', '#24362e');
  }
  return vars;
}

export default function DiagramView({code, title}: {code: string; title: string}) {
  const [svg, setSvg] = useState('');
  const [failed, setFailed] = useState(false);
  const [full, setFull] = useState(false);
  const holder = useRef<HTMLDivElement>(null);
  const seq = useRef(0);

  const draw = useCallback(async () => {
    if (!code) return;
    const id = ++seq.current;
    try {
      const mermaid = (await import('mermaid')).default;
      mermaid.initialize({
        startOnLoad: false,
        // Labels come from a language model, so never let them become markup.
        securityLevel: 'strict',
        theme: 'base',
        fontFamily: token('--font-sans', 'DM Sans, system-ui, sans-serif'),
        themeVariables: {
          background: token('--surface-2', '#f3f5f1'),
          primaryColor: token('--accent-soft', '#e8f0e7'),
          primaryTextColor: token('--ink', '#24362e'),
          primaryBorderColor: token('--accent', '#235c42'),
          lineColor: token('--line-strong', '#627068'),
          secondaryColor: token('--amber-soft', '#f6efe2'),
          tertiaryColor: token('--info-soft', '#eaeff8'),
          fontSize: '16px',
          // A mindmap branch is structure, not a data category, so it does not
          // need an encoding palette of its own. Mermaid ships one anyway and
          // it lands outside this product's colours entirely, so each section
          // is pinned to a tint already in the system.
          ...sections(),
        },
        mindmap: {padding: 14},
        flowchart: {curve: 'basis', padding: 16, useMaxWidth: true},
      });
      const out = await mermaid.render(`diagram-${id}-${Date.now()}`, code);
      // A newer render may have finished first; never overwrite it.
      if (id !== seq.current) return;
      setSvg(out.svg);
      setFailed(false);
    } catch (error) {
      if (id !== seq.current) return;
      // The student sees the structure, not the parser message; the message
      // still belongs somewhere a developer can find it.
      console.error('[StudyMate] diagram render failed:', error);
      setFailed(true);
      setSvg('');
    }
  }, [code]);

  useEffect(() => {void draw();}, [draw]);

  // Re-render on a theme change: the SVG bakes in the colours it was drawn with.
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => void draw();
    media.addEventListener('change', onChange);
    const observer = new MutationObserver(onChange);
    observer.observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
    return () => {media.removeEventListener('change', onChange); observer.disconnect();};
  }, [draw]);

  function download() {
    const blob = new Blob([svg], {type: 'image/svg+xml;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `studymate-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 48) || 'diagram'}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (failed) {
    return <div className="diagram-failed" role="alert">
      <WarningCircle size={22}/>
      <div>
        <strong>This diagram could not be drawn.</strong>
        <p>The structure below is what the diagram would have shown.</p>
        <pre>{code}</pre>
      </div>
    </div>;
  }

  return <figure className={full ? 'diagram-figure is-full' : 'diagram-figure'}>
    <div className="diagram-tools">
      <button type="button" onClick={() => setFull(v => !v)} title={full ? 'Fit to column' : 'Expand diagram'}
              aria-label={full ? 'Fit diagram to column' : 'Expand diagram'} aria-pressed={full}>
        <ArrowsOutSimple size={18}/>
      </button>
      <button type="button" onClick={download} disabled={!svg} title="Download diagram as SVG"
              aria-label="Download diagram as SVG">
        <DownloadSimple size={18}/>
      </button>
    </div>
    <div className="diagram-canvas" ref={holder} role="img" aria-label={`Diagram: ${title}`}
         dangerouslySetInnerHTML={{__html: svg}}/>
    {!svg && <div className="diagram-skeleton" aria-hidden="true"/>}
  </figure>;
}
