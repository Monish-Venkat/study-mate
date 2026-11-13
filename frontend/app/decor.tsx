/* Margin illustration.
 *
 * The reference is a technical-drawing plate: both margins filled with
 * scientific line art at one light weight, with rendered formulas and small
 * accents scattered between them. Everything here is stroke-only and uses
 * currentColor so it inverts with the theme, and the whole layer is
 * aria-hidden and non-interactive — it carries no information a student needs.
 *
 * Drawings are built from <path> rather than imported as assets so they stay
 * one weight, one colour, and scale without a second file to keep in step.
 */
import type {CSSProperties} from 'react';

type P = {className?: string; size?: number; style?: CSSProperties};

const svg = (size: number, box = 120) => ({
  width: size, height: size, viewBox: `0 0 ${box} ${box}`,
  fill: 'none', stroke: 'currentColor', strokeWidth: 0.9,
  strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
  'aria-hidden': true, focusable: false as const,
});

export const Art = ({src, size = 150, aspect = 1, className, style}: P & {src: string; aspect?: number}) => (
  <span
    className={className}
    aria-hidden="true"
    style={{
      ...style,
      display: 'block',
      // `size` is the LONGEST side, not the width. The supplied drawings run
      // from a helix at 2.26:1 tall to a trig identity at 0.13:1 wide, so
      // sizing by width alone made one a sliver and the other a banner at the
      // same number. Bounding the longest side lets one layout scale read as
      // the same visual weight across all of them.
      width: aspect >= 1 ? Math.round(size / aspect) : size,
      height: aspect >= 1 ? size : Math.round(size * aspect),
      backgroundColor: 'currentColor',
      WebkitMaskImage: `url(${src})`,
      maskImage: `url(${src})`,
      WebkitMaskSize: 'contain',
      maskSize: 'contain',
      WebkitMaskRepeat: 'no-repeat',
      maskRepeat: 'no-repeat',
      WebkitMaskPosition: 'center',
      maskPosition: 'center',
    }}
  />
);

/* ---------- Physics ---------- */

export const Atom = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <ellipse cx="60" cy="60" rx="52" ry="20"/>
    <ellipse cx="60" cy="60" rx="52" ry="20" transform="rotate(60 60 60)"/>
    <ellipse cx="60" cy="60" rx="52" ry="20" transform="rotate(120 60 60)"/>
    <circle cx="60" cy="60" r="8" fill="currentColor" fillOpacity=".25"/>
    <circle cx="108" cy="52" r="3.4" fill="currentColor" fillOpacity=".3"/>
    <circle cx="34" cy="98" r="3.4" fill="currentColor" fillOpacity=".3"/>
    <circle cx="30" cy="26" r="3" fill="currentColor" fillOpacity=".3"/>
  </svg>
);

export const Cradle = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M12 96 L28 26 M108 96 L92 26"/>
    <path d="M12 96 H108"/>
    <path d="M28 26 H92"/>
    {[36, 48, 60, 72, 84].map(x => (
      <g key={x}><path d={`M${x} 28 V64`}/><circle cx={x} cy="72" r="8"/></g>
    ))}
  </svg>
);

export const Pendulum = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M20 18 H100"/>
    <path d="M60 18 L82 84"/>
    <circle cx="84" cy="92" r="10"/>
    <path d="M60 18 L38 84" strokeDasharray="3 5"/>
    <path d="M44 72 A30 30 0 0 0 76 74" strokeDasharray="3 5"/>
  </svg>
);

export const Prism = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M60 22 L96 88 H24 Z"/>
    <path d="M6 60 L42 60"/>
    {[56, 62, 68, 74, 80].map((y, i) => <path key={y} d={`M78 70 L116 ${y + i * 2}`}/>)}
  </svg>
);

export const Wave = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M8 86 H112"/>
    <path d="M14 60 V100"/>
    <path d="M14 80 C30 36 46 124 62 80 C78 36 94 124 110 80"/>
  </svg>
);

export const Magnet = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M34 96 V58 a26 26 0 0 1 52 0 V96"/>
    <path d="M34 78 H60 M60 78 H86"/>
    <path d="M34 96 H60 V78 M86 96 H60"/>
    <path d="M18 40 C40 18 80 18 102 40" strokeDasharray="3 4"/>
  </svg>
);

/* ---------- Chemistry ---------- */

export const Flask = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M48 14 h24"/>
    <path d="M52 16 V48 L24 100 a6 6 0 0 0 5 9 h62 a6 6 0 0 0 5 -9 L68 48 V16"/>
    <path d="M36 78 h48" />
    <path d="M38 86 C50 80 58 92 70 86 C78 82 82 88 86 86"/>
    <circle cx="52" cy="94" r="2.5"/><circle cx="68" cy="98" r="2"/><circle cx="60" cy="88" r="1.8"/>
  </svg>
);

export const Benzene = ({className, size = 150, style}: P) => (
  <Art src="/decor/benzene.png" size={size} aspect={1.0993} className={className} style={style}/>
);

export const Naphthalene = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M38 26 L66 26 L80 50 L66 74 L38 74 L24 50 Z"/>
    <path d="M66 26 L94 26 L108 50 L94 74 L66 74"/>
    <path d="M40 34 L62 34"/><path d="M74 44 L74 56"/><path d="M40 66 L62 66"/>
  </svg>
);

/* ---------- Biology ---------- */

/* Replaces the heart. Five hand-drawn attempts at an anatomical heart all
 * read as a leaf or a valentine: freeform organic curves are where this
 * approach breaks down. A neuron is just as much PUC biology and is built
 * from straight radiating lines and regular ovals, which it holds up well. */
export const Neuron = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M40 46 L52 39 L63 46 L65 59 L54 67 L41 60 Z"/>
    <circle cx="52" cy="53" r="5.5"/>
    <circle cx="52" cy="53" r="1.8" strokeWidth=".6"/>
    <path d="M40 46 C31 41 25 33 18 28"/>
    <path d="M27 36 C22 31 15 29 9 30" strokeWidth=".75"/>
    <path d="M22 31 C20 25 20 19 22 14" strokeWidth=".7"/>
    <path d="M52 39 C50 28 53 18 49 9"/>
    <path d="M51 21 C55 15 61 13 66 10" strokeWidth=".75"/>
    <path d="M50 14 C46 10 41 8 36 8" strokeWidth=".7"/>
    <path d="M41 60 C33 66 27 74 23 83"/>
    <path d="M31 71 C26 76 19 79 13 79" strokeWidth=".75"/>
    <path d="M26 79 C25 85 26 91 29 96" strokeWidth=".7"/>
    <path d="M63 46 C66 38 65 30 62 24" strokeWidth=".8"/>
    <path d="M65 59 H112" strokeWidth=".85"/>
    <ellipse cx="76" cy="59" rx="8" ry="4.5"/>
    <ellipse cx="94" cy="59" rx="8" ry="4.5"/>
    <path d="M112 59 C116 54 118 50 117 45" strokeWidth=".75"/>
    <path d="M112 59 C117 60 119 64 118 69" strokeWidth=".75"/>
    <path d="M112 59 C116 63 117 68 114 73" strokeWidth=".75"/>
  </svg>
);

export const Helix = ({className, size = 150, style}: P) => (
  <Art src="/decor/helix.png" size={size} aspect={2.2624} className={className} style={style}/>
);

export const Cell = ({className, size = 150, style}: P) => (
  <Art src="/decor/cell.png" size={size} aspect={1.0377} className={className} style={style}/>
);

export const Microscope = ({className, size = 150, style}: P) => (
  <Art src="/decor/microscope.png" size={size} aspect={1.7743} className={className} style={style}/>
);

export const Leaf = ({className, size = 150, style}: P) => (
  <Art src="/decor/leaf.png" size={size} aspect={1.0523} className={className} style={style}/>
);

export const Ecg = ({className, size = 150, style}: P) => (
  <Art src="/decor/ecg.png" size={size} aspect={0.3193} className={className} style={style}/>
);

/* ---------- Mathematics ---------- */

export const Triangle = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M18 98 H102 L18 26 Z"/>
    <path d="M18 86 H30 V98"/>
    <text x="6" y="64" fontSize="13" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">a</text>
    <text x="58" y="112" fontSize="13" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">b</text>
    <text x="64" y="54" fontSize="13" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">c</text>
  </svg>
);

export const Axes = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M22 14 V96 H112"/>
    <path d="M22 14 l-4 7 M22 14 l4 7"/>
    <path d="M112 96 l-7 -4 M112 96 l-7 4"/>
    <path d="M22 78 C44 20 72 20 96 72"/>
    <text x="8" y="22" fontSize="13" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">y</text>
    <text x="104" y="114" fontSize="13" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">x</text>
  </svg>
);

export const Compass = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <circle cx="60" cy="18" r="7"/>
    <path d="M57 24 L34 104"/>
    <path d="M63 24 L86 104"/>
    <path d="M34 104 l-5 8"/>
    <path d="M86 104 l5 8"/>
    <path d="M48 66 C56 62 66 62 73 66"/>
  </svg>
);

/* ---------- Geometry: solids drawn with hidden edges dashed ---------- */

export const Cylinder = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <ellipse cx="60" cy="26" rx="30" ry="11"/>
    <path d="M30 26 V92"/><path d="M90 26 V92"/>
    <path d="M30 92 A30 11 0 0 0 90 92"/>
    <path d="M30 92 A30 11 0 0 1 90 92" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M60 26 V92" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M60 92 H90" strokeDasharray="4 4" strokeWidth=".7"/>
    <text x="64" y="62" fontSize="11" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">h</text>
    <text x="72" y="104" fontSize="11" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">r</text>
  </svg>
);

export const Cone = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M60 14 L26 88"/><path d="M60 14 L94 88"/>
    <path d="M26 88 A34 12 0 0 0 94 88"/>
    <path d="M26 88 A34 12 0 0 1 94 88" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M60 14 V88" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M60 88 H94" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M60 82 h6 v6" strokeWidth=".6"/>
    <text x="48" y="60" fontSize="11" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">h</text>
    <text x="80" y="54" fontSize="11" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">l</text>
    <text x="74" y="100" fontSize="11" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">r</text>
  </svg>
);

export const Cube = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M24 40 h56 v56 h-56 Z"/>
    <path d="M24 40 L46 20 h56 L80 40"/>
    <path d="M102 20 V76 L80 96"/>
    <path d="M46 20 V76" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M46 76 H102" strokeDasharray="4 4" strokeWidth=".7"/>
    <path d="M46 76 L24 96" strokeDasharray="4 4" strokeWidth=".7"/>
  </svg>
);

export const CircleRadius = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <circle cx="60" cy="60" r="46"/>
    <circle cx="60" cy="60" r="2" fill="currentColor"/>
    <path d="M60 60 H106" strokeDasharray="5 4"/>
    <text x="76" y="54" fontSize="12" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">r</text>
  </svg>
);

export const Angle = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M12 92 H112"/>
    <path d="M12 92 L108 30"/>
    <path d="M52 92 A40 40 0 0 0 46 76" strokeWidth=".7"/>
    <text x="54" y="84" fontSize="11" fontFamily="Georgia,serif" stroke="none" fill="currentColor">30&#176;</text>
  </svg>
);

export const Venn = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <circle cx="46" cy="46" r="26"/><circle cx="76" cy="46" r="26"/><circle cx="61" cy="74" r="26"/>
    <text x="32" y="42" fontSize="12" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">a</text>
    <text x="84" y="42" fontSize="12" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">b</text>
    <text x="57" y="92" fontSize="12" fontStyle="italic" fontFamily="Georgia,serif" stroke="none" fill="currentColor">c</text>
  </svg>
);

/* ---------- Instruments ---------- */

export const Protractor = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M14 86 A46 46 0 0 1 106 86 Z"/>
    <path d="M24 86 A36 36 0 0 1 96 86" strokeWidth=".7"/>
    {Array.from({length: 13}, (_, i) => {
      const t = Math.PI * (1 - i / 12), inner = i % 3 === 0 ? 32 : 37;
      // Rounded because the raw floats differ in their last digit between the
      // server and the browser, which React reports as a hydration mismatch.
      const r = (n: number) => Math.round(n * 100) / 100;
      return <path key={i} strokeWidth=".6"
        d={`M${r(60 + 44 * Math.cos(t))} ${r(86 - 44 * Math.sin(t))} L${r(60 + inner * Math.cos(t))} ${r(86 - inner * Math.sin(t))}`}/>;
    })}
    <circle cx="60" cy="86" r="2"/>
  </svg>
);

export const SetSquare = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M22 100 H104 L22 24 Z"/>
    <path d="M34 92 H92 L34 38 Z" strokeWidth=".7"/>
    <path d="M22 88 h12 v12" strokeWidth=".6"/>
    {Array.from({length: 9}, (_, i) =>
      <path key={i} strokeWidth=".55" d={`M${32 + i * 8} 100 V${i % 2 ? 94 : 91}`}/>)}
  </svg>
);

export const Calculator = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M22 12 h76 a6 6 0 0 1 6 6 v84 a6 6 0 0 1 -6 6 h-76 a6 6 0 0 1 -6 -6 v-84 a6 6 0 0 1 6 -6 Z"/>
    <path d="M26 22 h68 v18 h-68 Z"/>
    {[0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c =>
      <rect key={`${r}${c}`} x={27 + c * 17} y={50 + r * 13} width="12" height="9" rx="2" strokeWidth=".7"/>))}
  </svg>
);

export const Pencil = ({className, size = 150, style}: P) => (
  <svg {...svg(size)} className={className} style={style}>
    <path d="M86 12 l18 14 -62 80 -22 6 4 -22 Z"/>
    <path d="M78 22 l18 14" strokeWidth=".7"/>
    <path d="M24 90 l18 14" strokeWidth=".7"/>
    <path d="M20 112 l12 -4" strokeWidth=".7"/>
    <path d="M82 17 l18 14" strokeWidth=".6"/>
  </svg>
);

/* ---------- Formulas, set as type rather than drawn ---------- */

const formulaStyle: CSSProperties = {
  fontFamily: 'Georgia, "Times New Roman", serif',
  fontStyle: 'italic',
  color: 'currentColor',
  whiteSpace: 'nowrap',
  lineHeight: 1,
};

export const Fma = ({className, size = 42, style}: P) => (
  <span className={className} aria-hidden style={{...formulaStyle, fontSize: size, ...style}}>F = ma</span>
);

export const Pi = ({className, size = 54, style}: P) => (
  <span className={className} aria-hidden style={{...formulaStyle, fontSize: size, ...style}}>&pi;</span>
);

export const Quadratic = ({className, size = 26, style}: P) => (
  <span className={className} aria-hidden style={{...formulaStyle, fontSize: size, ...style}}>
    <span style={{display: 'inline-flex', alignItems: 'center', gap: '.35em'}}>
      <span>x =</span>
      <span style={{display: 'inline-flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1.15}}>
        <span>&minus;b &plusmn; &radic;<span style={{borderTop: '1px solid currentColor', paddingTop: 1}}>b&sup2; &minus; 4ac</span></span>
        <span style={{borderTop: '1px solid currentColor', width: '100%', textAlign: 'center', paddingTop: 2}}>2a</span>
      </span>
    </span>
  </span>
);

/* ---------- Accents ---------- */

export const Spark = ({className, size = 14, style}: P) => (
  <svg {...svg(size, 24)} className={className} style={style}>
    <path d="M12 2 C12 8 16 12 22 12 C16 12 12 16 12 22 C12 16 8 12 2 12 C8 12 12 8 12 2 Z"/>
  </svg>
);

export const Plus = ({className, size = 12, style}: P) => (
  <svg {...svg(size, 24)} className={className} style={style}>
    <path d="M12 3 V21 M3 12 H21"/>
  </svg>
);

export const Dot = ({className, size = 7, style}: P) => (
  <svg {...svg(size, 24)} className={className} style={style}>
    <circle cx="12" cy="12" r="9"/>
  </svg>
);

export const Ring = ({className, size = 220, style}: P) => (
  <svg {...svg(size, 240)} className={className} style={style}>
    <circle cx="120" cy="120" r="118"/>
  </svg>
);


export const Pythagoras = ({className, size = 26, style}: P) => (
  <span className={className} aria-hidden style={{...formulaStyle, fontSize: size, ...style}}>
    a&sup2; + b&sup2; = c&sup2;
  </span>
);

export const Identity = ({className, size = 150, style}: P) => (
  <Art src="/decor/identity.png" size={size} aspect={0.1329} className={className} style={style}/>
);

export const SqrtX = ({className, size = 34, style}: P) => (
  <span className={className} aria-hidden style={{...formulaStyle, fontSize: size, ...style}}>
    &radic;<span style={{borderTop: '1px solid currentColor', paddingTop: 1}}>x</span>
  </span>
);

export const Perimeter = ({className, size = 28, style}: P) => (
  <span className={className} aria-hidden style={{...formulaStyle, fontSize: size, ...style}}>P = 4a</span>
);

/* A slot for supplied artwork.
 *
 * Drawn motifs inherit the plate's colour through `currentColor`. A flat
 * image cannot, so the file is used as a CSS mask instead: its alpha gives
 * the shape and the colour comes from the page. That means one asset works
 * in both themes and sits at the same watermark opacity as everything else.
 *
 * Prepare the file with its background removed and its alpha carrying the
 * ink (see the conversion in scripts, or any "remove white" export).
 */


/* The supplied anatomical heart. 253x373 after cropping to the ink. */
export const HeartArt = ({className, size = 150, style}: P) => (
  <Art src="/decor/heartart.png" size={size} aspect={1.5224} className={className} style={style}/>
);

export const subjectMotif = {physics: Prism, chemistry: Benzene, mathematics: Axes, biology: HeartArt};
