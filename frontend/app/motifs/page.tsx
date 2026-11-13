'use client';
import * as D from '../decor';

/* Proof sheet — a development route, not part of the product.
 *
 * The plate renders every motif at about 5% opacity, which is too faint to
 * judge or even to screenshot. This shows the same components at full
 * strength and full size, so a drawing can be reviewed and named before it
 * goes near the page. It imports the real components, so it cannot drift
 * from what the hero actually renders.
 *
 * Delete app/motifs/ when the drawings are settled.
 */
const DRAWINGS: [string, string, (p: {size?: number}) => React.JSX.Element][] = [
  ['Atom', 'physics', D.Atom],
  ['Cradle', 'physics', D.Cradle],
  ['Pendulum', 'physics', D.Pendulum],
  ['Prism', 'physics', D.Prism],
  ['Wave', 'physics', D.Wave],
  ['Magnet', 'physics', D.Magnet],
  ['Flask', 'chemistry', D.Flask],
  ['Benzene', 'chemistry', D.Benzene],
  ['Naphthalene', 'chemistry', D.Naphthalene],
  ['HeartArt', 'biology — supplied', D.HeartArt],
  ['Neuron', 'biology — unused', D.Neuron],
  ['Helix', 'biology', D.Helix],
  ['Cell', 'biology', D.Cell],
  ['Microscope', 'biology', D.Microscope],
  ['Leaf', 'biology', D.Leaf],
  ['Ecg', 'biology', D.Ecg],
  ['Triangle', 'maths', D.Triangle],
  ['Axes', 'maths', D.Axes],
  ['Compass', 'maths', D.Compass],
  ['Cylinder', 'maths', D.Cylinder],
  ['Cone', 'maths', D.Cone],
  ['Cube', 'maths', D.Cube],
  ['CircleRadius', 'maths', D.CircleRadius],
  ['Angle', 'maths', D.Angle],
  ['Venn', 'maths', D.Venn],
  ['Protractor', 'instrument', D.Protractor],
  ['SetSquare', 'instrument', D.SetSquare],
  ['Calculator', 'instrument', D.Calculator],
  ['Pencil', 'instrument', D.Pencil],
];

const TYPE: [string, (p: {size?: number}) => React.JSX.Element][] = [
  ['Fma', D.Fma], ['Pi', D.Pi], ['Quadratic', D.Quadratic],
  ['Pythagoras', D.Pythagoras], ['Identity', D.Identity],
  ['SqrtX', D.SqrtX], ['Perimeter', D.Perimeter],
];

const ACCENTS: [string, (p: {size?: number}) => React.JSX.Element][] = [
  ['Spark', D.Spark], ['Plus', D.Plus], ['Dot', D.Dot],
];

// Which plate each drawing currently sits on, so a complaint about "the right
// side" can be tied to specific names.
const RIGHT = new Set(['Helix', 'HeartArt', 'Ecg', 'Microscope', 'Cell', 'Leaf', 'Benzene', 'Identity']);

export default function Motifs() {
  return <main style={{padding: 28, fontFamily: 'var(--font-sans)', background: 'var(--surface)', minHeight: '100dvh'}}>
    <h1 style={{fontSize: 22, margin: '0 0 6px', letterSpacing: '-.5px'}}>Motif proof sheet</h1>
    <p style={{color: 'var(--muted)', fontSize: 13, margin: '0 0 24px'}}>
      Full strength and full size. Names match the exports in <code>decor.tsx</code>.
      Items marked <b>R</b> are on the right-hand plate of the hero.
    </p>

    <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(176px, 1fr))', gap: 18}}>
      {DRAWINGS.map(([name, group, C]) => (
        <figure key={name} style={{
          margin: 0, padding: 14, textAlign: 'center',
          border: '1px solid var(--line)', borderRadius: 12, background: 'var(--canvas)',
        }}>
          <div style={{color: 'var(--ink)', display: 'flex', justifyContent: 'center', minHeight: 160}}>
            <C size={150}/>
          </div>
          <figcaption style={{fontSize: 12, marginTop: 10}}>
            <b>{name}</b>{RIGHT.has(name) && <span style={{
              marginLeft: 6, padding: '1px 5px', borderRadius: 4,
              border: '1px solid var(--line-strong)', fontSize: 10,
            }}>R</span>}
            <span style={{display: 'block', color: 'var(--muted)', fontSize: 11, marginTop: 3}}>{group}</span>
          </figcaption>
        </figure>
      ))}
    </div>

    <h2 style={{fontSize: 15, margin: '32px 0 12px'}}>Type</h2>
    <div style={{display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'center', color: 'var(--ink)'}}>
      {TYPE.map(([name, C]) => (
        <figure key={name} style={{margin: 0, textAlign: 'center'}}>
          <C/>
          <figcaption style={{fontSize: 11, color: 'var(--muted)', marginTop: 8}}>{name}</figcaption>
        </figure>
      ))}
    </div>

    <h2 style={{fontSize: 15, margin: '32px 0 12px'}}>Accents</h2>
    <div style={{display: 'flex', gap: 24, alignItems: 'center', color: 'var(--ink)'}}>
      {ACCENTS.map(([name, C]) => (
        <figure key={name} style={{margin: 0, textAlign: 'center'}}>
          <C size={26}/>
          <figcaption style={{fontSize: 11, color: 'var(--muted)', marginTop: 8}}>{name}</figcaption>
        </figure>
      ))}
    </div>
  </main>;
}
