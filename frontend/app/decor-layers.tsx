'use client';
import type {CSSProperties} from 'react';
import {
  Atom, Cradle, Pendulum, Prism, Wave, Magnet,
  Flask, Benzene, Naphthalene,
  HeartArt, Helix, Cell, Microscope, Leaf, Ecg,
  Triangle, Axes, Compass,
  Cylinder, Cone, Cube, CircleRadius, Angle, Venn,
  Protractor, SetSquare, Calculator, Pencil,
  Fma, Pi, Quadratic, Pythagoras, Identity, SqrtX, Perimeter,
  Spark, Plus, Dot, Ring,
  subjectMotif,
} from './decor';

/* Composed margin plates.
 *
 * Positions are percentages from the page edge so the plate widens with the
 * window instead of sliding under the text column. Each item carries its own
 * opacity: the large drawings sit lower so they read as paper texture, the
 * formulas slightly higher because type disappears faster than line work.
 */
type Item = {
  C: (p: {size?: number; style?: CSSProperties; className?: string}) => React.JSX.Element;
  top: number; left?: number; right?: number; size: number; o?: number; rotate?: number;
};

const at = (i: Item): CSSProperties => ({
  position: 'absolute',
  top: i.top,
  ...(i.left !== undefined ? {left: `${i.left}%`} : {}),
  ...(i.right !== undefined ? {right: `${i.right}%`} : {}),
  opacity: i.o ?? 1,
  ...(i.rotate ? {transform: `rotate(${i.rotate}deg)`} : {}),
});

const HERO_LEFT: Item[] = [
  {C: Atom, top: 50, left: 1, size: 160},
  {C: Fma, top: 228, left: 1.5, size: 40, o: 1.3},
  {C: Cradle, top: 284, left: 0.8, size: 168},
  {C: Pythagoras, top: 1660, left: 9.5, size: 23, o: 1.25},
  {C: Flask, top: 470, left: 1.2, size: 150},
  {C: Cylinder, top: 506, left: 11.5, size: 118, o: .85},
  {C: Axes, top: 650, left: 0.8, size: 150},
  {C: Pi, top: 734, left: 9.5, size: 54, o: 1.25},
  {C: Cone, top: 804, left: 11, size: 116, o: .85},
  {C: Triangle, top: 822, left: 1.5, size: 152},
  {C: Quadratic, top: 944, left: 10.5, size: 23, o: 1.25},
  {C: Protractor, top: 980, left: 1.2, size: 150},
  {C: Cube, top: 1012, left: 11, size: 118, o: .85},
  {C: Compass, top: 1142, left: 2.5, size: 146, o: .9},
  {C: SqrtX, top: 1186, left: 11.5, size: 32, o: 1.2},
  {C: SetSquare, top: 1316, left: 1, size: 148, o: .85},
  {C: Calculator, top: 1300, left: 11, size: 108, o: .8},
  {C: Wave, top: 1424, left: 1.5, size: 144, o: .8},
  {C: Venn, top: 1444, left: 10.5, size: 118, o: .8},
  {C: Perimeter, top: 1596, left: 2, size: 26, o: 1.2},
];

/* The right side is the supplied artwork: real scientific line drawings
 * rather than the shapes drawn here, which is why this plate kept reading as
 * chaos however it was arranged -- an organic form drawn from a path either
 * looks right or looks like a beetle, and these never looked right.
 *
 * Laid out as one calm right-aligned column. Tops are computed from each
 * drawing's RENDERED height (longest side bounded by `size`, so the helix at
 * 2.26:1 and the identity at 0.13:1 carry the same visual weight) with a
 * uniform 74px gap, so nothing overlaps at any size and the rhythm is even
 * instead of clustered. Offsets stay within 3.5-4.5% so the right edges line
 * up; the earlier plate ranged 2-9% and the ragged edge was most of the mess.
 */
const HERO_RIGHT: Item[] = [
  {C: Helix, top: 60, right: 4, size: 170},
  {C: HeartArt, top: 304, right: 4, size: 160},
  {C: Ecg, top: 538, right: 3.5, size: 180, o: .85},
  {C: Microscope, top: 669, right: 4, size: 165},
  {C: Cell, top: 908, right: 4, size: 158},
  {C: Leaf, top: 1140, right: 4, size: 156},
  {C: Benzene, top: 1370, right: 4.5, size: 140, o: .9},
  {C: Identity, top: 1584, right: 3.5, size: 150, o: 1.15},
];

const ACCENTS: Item[] = [
  {C: Spark, top: 118, left: 14.5, size: 15}, {C: Plus, top: 236, left: 9.5, size: 12},
  {C: Dot, top: 436, left: 13, size: 8}, {C: Spark, top: 626, left: 12.5, size: 13},
  {C: Plus, top: 782, left: 7, size: 11}, {C: Dot, top: 952, left: 13.5, size: 7},
  {C: Spark, top: 1110, left: 13, size: 14}, {C: Plus, top: 1380, left: 10, size: 12},
  {C: Dot, top: 1540, left: 12, size: 8},
  // Fewer on the right, and kept out of the gaps between drawings.
  {C: Spark, top: 108, right: 1.5, size: 15}, {C: Dot, top: 268, right: 13, size: 8},
  {C: Plus, top: 496, right: 12, size: 11}, {C: Spark, top: 804, right: 13, size: 13},
  {C: Dot, top: 1056, right: 12.5, size: 7}, {C: Plus, top: 1280, right: 12, size: 12},
];

function Plate({items, className = 'decor'}: {items: Item[]; className?: string}) {
  return <>{items.map((item, i) => {
    const {C} = item;
    return <C key={i} className={className} size={item.size} style={at(item)}/>;
  })}</>;
}

export function HeroDecor() {
  return <div className="decor-plate" aria-hidden="true">
    <Plate items={HERO_LEFT}/>
    <Plate items={HERO_RIGHT}/>
    <Plate items={ACCENTS} className="decor decor-accent"/>
  </div>;
}

/* Tool pages get a lighter plate: the same language, fewer objects, because
 * the task is a form rather than a front page. */
const TOOL_SETS: Record<string, Item[]> = {
  ask: [{C: Prism, top: 88, left: 2, size: 150}, {C: Wave, top: 406, left: 3, size: 140, o: .85},
        {C: Atom, top: 700, left: 2, size: 146, o: .8}],
  guided: [{C: Pendulum, top: 88, left: 2, size: 152}, {C: Axes, top: 420, left: 3, size: 138, o: .85},
           {C: Venn, top: 712, left: 2.5, size: 134, o: .8}],
  notes: [{C: Benzene, top: 94, left: 2.5, size: 140}, {C: Triangle, top: 420, left: 2.5, size: 142, o: .85},
          {C: Pythagoras, top: 700, left: 2, size: 23, o: 1.2}],
  'past-papers': [{C: Protractor, top: 90, left: 2.5, size: 146}, {C: SetSquare, top: 430, left: 2.5, size: 140, o: .85},
                  {C: Pencil, top: 716, left: 3, size: 128, o: .8}],
  practice: [{C: Cradle, top: 86, left: 1.8, size: 158}, {C: Calculator, top: 432, left: 3, size: 120, o: .85},
             {C: Cube, top: 712, left: 2.5, size: 134, o: .8}],
  'study-map': [{C: Atom, top: 86, left: 1.8, size: 158}, {C: Cell, top: 430, left: 2.5, size: 150, o: .85},
                {C: Cone, top: 716, left: 3, size: 130, o: .8}],
};

const SUBJECT_SETS: Record<string, Item[]> = {
  physics: [{C: Magnet, top: 140, right: 2.5, size: 150}, {C: Ecg, top: 470, right: 1, size: 180, o: .75},
            {C: Cylinder, top: 730, right: 3, size: 128, o: .8}],
  chemistry: [{C: Flask, top: 132, right: 2.5, size: 152}, {C: Benzene, top: 480, right: 3, size: 132, o: .85},
              {C: Naphthalene, top: 736, right: 2.5, size: 124, o: .8}],
  mathematics: [{C: Axes, top: 138, right: 2.5, size: 150}, {C: Pi, top: 492, right: 5, size: 56, o: 1.1},
                {C: CircleRadius, top: 700, right: 2.5, size: 134, o: .8}],
  biology: [{C: HeartArt, top: 124, right: 2.5, size: 152}, {C: Helix, top: 460, right: 2, size: 192, o: .85},
            {C: Leaf, top: 740, right: 2.5, size: 140, o: .8}],
};

const TOOL_ACCENTS: Item[] = [
  {C: Spark, top: 140, left: 11, size: 14}, {C: Plus, top: 330, left: 3, size: 11},
  {C: Dot, top: 560, left: 10.5, size: 7},
  {C: Spark, top: 120, right: 11, size: 14}, {C: Plus, top: 380, right: 3, size: 11},
  {C: Dot, top: 620, right: 10, size: 7},
];

export function ToolDecor({slug, subject}: {slug: string; subject: string}) {
  const Glyph = subjectMotif[subject as keyof typeof subjectMotif];
  return <div className="decor-plate" aria-hidden="true">
    <Plate items={TOOL_SETS[slug] || []}/>
    <Plate items={SUBJECT_SETS[subject] || []}/>
    <Plate items={TOOL_ACCENTS} className="decor decor-accent"/>
    {Glyph ? null : null}
  </div>;
}
