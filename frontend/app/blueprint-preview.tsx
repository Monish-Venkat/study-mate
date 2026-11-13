'use client';
import {useEffect, useState} from 'react';

/* What a mark total will actually produce, shown before generating.
 *
 * Generating a paper takes a while on a local model, and until now the only
 * way to discover that 70 marks means thirteen 5-mark questions was to wait
 * for one. The shape is deterministic, so it can be shown immediately.
 *
 * The figures come from the server's own blueprint function rather than being
 * recomputed here: a preview that disagreed with the generator would be worse
 * than no preview.
 */
type Blueprint = {
  total_marks: number;
  questions: number;
  internal_choice: number;
  by_marks: {marks: number; count: number}[];
  bloom: {level: string; count: number}[];
};

export default function BlueprintPreview({totalMarks}: {totalMarks: number}) {
  const [plan, setPlan] = useState<Blueprint | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(totalMarks) || totalMarks < 10 || totalMarks > 200) {
      setPlan(null);
      return;
    }
    let live = true;
    // Debounced: the field is a number input, so typing "70" passes through 7.
    const timer = setTimeout(() => {
      fetch(`/api/modules/mock-paper/blueprint?total_marks=${totalMarks}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (live) { setPlan(d); setFailed(!d); } })
        .catch(() => { if (live) { setPlan(null); setFailed(true); } });
    }, 350);
    return () => { live = false; clearTimeout(timer); };
  }, [totalMarks]);

  if (failed && !plan) return null;
  if (!plan) return null;

  return <div className="blueprint" aria-live="polite">
    <p className="blueprint-head">
      <b>{plan.questions}</b> questions · <b>{plan.total_marks}</b> marks
      {plan.internal_choice > 0 &&
        <> · <b>{plan.internal_choice}</b> with internal choice</>}
    </p>
    <ul className="blueprint-rows">
      {plan.by_marks.map(row => <li key={row.marks}>
        <span className="count">{row.count}×</span>
        <span>{row.marks}-mark question{row.count === 1 ? '' : 's'}</span>
        <span className="bar" style={{flexBasis: `${(row.count * row.marks / plan.total_marks) * 100}%`}}/>
        <span className="share">{Math.round((row.count * row.marks / plan.total_marks) * 100)}%</span>
      </li>)}
    </ul>
    <p className="blueprint-bloom">
      {plan.bloom.map(b => `${b.count} ${b.level}`).join(' · ')}
    </p>
  </div>;
}
