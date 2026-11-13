"""Choose ABSTAIN_GROUNDED_FRACTION from a benchmark run, instead of guessing.

The abstention gate in rag.py withholds an answer whose claims mostly cannot
be traced back to the retrieved passages. Where to put that threshold is an
empirical question with an asymmetric cost, and it was first set from three
observations -- which put it at 0.35, above the worst legitimately answerable
question in the data (0.33), so a Fungi question whose chapter IS indexed got
refused. This script exists so the next person does not repeat that.

Run it on the JSON that run_benchmark.py writes:

    python evaluation/abstain_threshold.py evaluation/results/full.json

It reports the grounded_fraction distribution for answerable and unanswerable
questions separately, then sweeps candidate thresholds showing what each one
would cost. Nothing is applied automatically: the operating point is a
judgement about which error is worse, and that belongs to a person.

Reading the output
------------------
"false refusals" are answerable questions the threshold would withhold -- a
student who should have been taught gets nothing. "caught" are unanswerable
questions it would withhold -- a student is spared a confident invention.
A threshold is only trustworthy where BOTH columns have enough items behind
them; a clean-looking separation over two unanswerable rows is not evidence.

A limit of this benchmark, worth knowing before trusting the "caught" column:
an out-of-syllabus question is usually refused upstream, by the no-hits path,
and so never reaches the audit at all. On floor_ground.json only 2 of 8 did.
The case this gate actually exists for is a different one the benchmark does
not label: a question that IS in the syllabus but whose chapter is NOT in the
index, where retrieval finds neighbouring passages, the model fills the gap
from memory, and the answer comes back fluent and wrong. Measuring the gate
properly needs items of that kind. Indexing the full corpus shrinks the
category, which is the better fix, but it does not empty it.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

# Corrective-retrieval outcomes rag.py treats as weak. Kept in step with
# WEAK_RETRIEVAL there.
WEAK = {'incorrect', 'incorrect_recovered'}


def load(paths: list[str]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        for row in data.get('rows') or []:
            grounding = row.get('grounding')
            if not isinstance(grounding, dict) or 'grounded_fraction' not in grounding:
                continue
            rows.append({
                'id': row.get('id'),
                'answerable': bool(row.get('answerable')),
                'fraction': float(grounding['grounded_fraction']),
                'weak': (row.get('retrieval') or {}).get('action') in WEAK,
                'source': Path(path).name,
            })
    return rows


def describe(label: str, values: list[float]) -> None:
    if not values:
        print(f'  {label:30} no items')
        return
    values = sorted(values)
    print(f'  {label:30} n={len(values):3}  min={values[0]:.2f}  '
          f'p10={values[max(0, len(values) // 10)]:.2f}  '
          f'median={statistics.median(values):.2f}  max={values[-1]:.2f}')


def sweep(rows: list[dict], weak: bool | None) -> None:
    """Print what each candidate threshold would cost on this data."""
    group = [r for r in rows if weak is None or r['weak'] == weak]
    good = [r['fraction'] for r in group if r['answerable']]
    bad = [r['fraction'] for r in group if not r['answerable']]
    if not good and not bad:
        print('  no items in this group')
        return
    print(f'  {"threshold":>9}  {"false refusals":>16}  {"caught":>14}')
    for step in range(0, 21):
        threshold = step / 20
        refused = sum(1 for f in good if f < threshold)
        caught = sum(1 for f in bad if f < threshold)
        flag = ''
        if good and refused == 0 and caught == len(bad) and bad:
            flag = '  <- separates cleanly'
        print(f'  {threshold:>9.2f}  {refused:>6}/{len(good):<9}  {caught:>6}/{len(bad):<7}{flag}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('results', nargs='+', help='JSON file(s) written by run_benchmark.py')
    parser.add_argument('--split-weak', action='store_true',
                        help='report strong and weak retrieval separately, as rag.py gates them')
    args = parser.parse_args()

    rows = load(args.results)
    if not rows:
        print('No rows carried a grounded_fraction. Was the run made with ENABLE_GROUNDING on?')
        return 1

    good = [r for r in rows if r['answerable']]
    bad = [r for r in rows if not r['answerable']]
    print(f'{len(rows)} audited items from {", ".join(sorted({r["source"] for r in rows}))}')
    print(f'  answerable {len(good)}, not answerable {len(bad)}')
    if len(bad) < 10:
        print(f'  WARNING: only {len(bad)} unanswerable items reached the audit. The threshold')
        print('  is what stops an invented answer, and that side is what this measures;')
        print('  treat any separation below as provisional until more of them get through.')
    print()

    print('grounded_fraction')
    describe('answerable, strong retrieval', [r['fraction'] for r in good if not r['weak']])
    describe('answerable, weak retrieval', [r['fraction'] for r in good if r['weak']])
    describe('not answerable, strong', [r['fraction'] for r in bad if not r['weak']])
    describe('not answerable, weak', [r['fraction'] for r in bad if r['weak']])
    print()

    if args.split_weak:
        for weak, name in ((False, 'STRONG retrieval -> ABSTAIN_GROUNDED_FRACTION'),
                           (True, 'WEAK retrieval -> ABSTAIN_GROUNDED_FRACTION_WEAK')):
            print(name)
            sweep(rows, weak)
            print()
    else:
        print('all items')
        sweep(rows, None)
        print()

    floor = min((r['fraction'] for r in good), default=None)
    if floor is not None:
        print(f'Lowest answerable observation: {floor:.2f}. A threshold at or above it refuses')
        print('a question the index can answer, which is the failure that is hard to notice:')
        print('the student simply does not get taught, and nothing looks broken.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
