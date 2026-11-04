"use client";
import {ShieldCheck, ShieldWarning, Info} from '@phosphor-icons/react';

export type Claim = {text: string; status: string; citations: number[];
                     cited_support: number; corpus_support: number; verified?: boolean};
export type Grounding = {
  claims?: Claim[];
  counts?: Record<string, number>;
  grounded_fraction?: number;
  cited_fraction?: number;
  dangling_citations?: number[];
  passages?: number;
  verified?: boolean;
};

const WORDING: Record<string, string> = {
  unsupported: 'Not found in the retrieved passages',
  miscited: 'Supported, but not by the passage it cites',
  uncited: 'No citation given',
};

/** Shows how much of an answer the retrieved passages actually support.
 *
 *  A citation is a claim about grounding, not proof of it. The backend reads
 *  the answer back against its own evidence; this surfaces that verdict next
 *  to the answer rather than leaving the student to check every line. */
export default function GroundingBadge({grounding}: {grounding?: Grounding}) {
  const claims = grounding?.claims ?? [];
  if (!grounding || claims.length === 0) return null;

  const counts = grounding.counts ?? {};
  const flagged = claims.filter(c => c.status !== 'supported');
  const fraction = grounding.grounded_fraction ?? 0;
  const traceable = claims.length - (counts.unsupported ?? 0);
  const tone = fraction >= 0.8 ? 'is-good' : fraction >= 0.5 ? 'is-fair' : 'is-poor';
  const percent = Math.round(fraction * 100);

  return <section className={`grounding ${tone}`} aria-label="Grounding check">
    <div className="grounding-head">
      {tone === 'is-good' ? <ShieldCheck size={20} weight="duotone"/> : <ShieldWarning size={20} weight="duotone"/>}
      <div className="grounding-headline">
        <strong>{percent}% of this answer traces to your course material</strong>
        <small>
          {traceable} of {claims.length} statement{claims.length === 1 ? '' : 's'}{' '}
          {traceable === 1 ? 'was' : 'were'} found in the {grounding.passages ?? 0} retrieved
          passage{grounding.passages === 1 ? '' : 's'}, and {counts.supported ?? 0}{' '}
          cite{(counts.supported ?? 0) === 1 ? 's' : ''} the passage that carries{' '}
          {(counts.supported ?? 0) === 1 ? 'it' : 'them'}
          {grounding.verified ? '. Flagged statements were checked a second time' : ''}.
        </small>
      </div>
      <span className="grounding-meter" aria-hidden="true">
        <span style={{transform: `scaleX(${fraction})`}}/>
      </span>
    </div>

    {flagged.length > 0 && <details className="grounding-detail">
      <summary>Show the {flagged.length} statement{flagged.length === 1 ? '' : 's'} to check yourself</summary>
      <ul>
        {flagged.map((claim, i) => <li key={i} className={`claim-${claim.status}`}>
          <span className="claim-tag">{WORDING[claim.status] ?? claim.status}</span>
          <p>{claim.text}</p>
        </li>)}
      </ul>
      {(grounding.dangling_citations?.length ?? 0) > 0 &&
        <p className="grounding-note">
          <Info size={15}/>
          Citation{grounding.dangling_citations!.length === 1 ? '' : 's'}{' '}
          {grounding.dangling_citations!.map(n => `[${n}]`).join(', ')} point to passages that were never
          retrieved, so there is nothing behind them.
        </p>}
    </details>}
  </section>;
}
