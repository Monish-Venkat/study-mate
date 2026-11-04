"""Reliability of diagram generation, measured rather than asserted.

The claim being tested is narrow and falsifiable: that a diagram shown to a
student always parses, because the renderer re-emits the structure it recovered
instead of forwarding what the model wrote. So the quantities here are render
reliability, abstention rate and how often recovery had to repair something --
not whether a diagram teaches well, which needs learners and is not measured.

Topics are taken from the system's own topic miner, which draws them from the
syllabus and from recurring past-paper topics, so the inputs are not a list
chosen to flatter the feature.

Emitted Mermaid is written to results/diagram_sources.json so that it can be
put through a real Mermaid parser in a browser; structural self-checks here
cannot prove that Mermaid accepts the output.

    python evaluation/diagram_study.py --per-cell 3
"""
import argparse
import asyncio
import json
import re
import time
from pathlib import Path

from app.core.prompts import DIAGRAM_KINDS
from app.services.diagram import MIN_NODES, build_diagram
from app.services.mock_engine import exam_topics

CELLS = [(s, l) for s in ('physics', 'chemistry', 'mathematics', 'biology')
         for l in ('PUC1', 'PUC2')]
KINDS = list(DIAGRAM_KINDS)


def structural_problems(code, kind):
    """Cheap invariants the emitter is supposed to guarantee by construction."""
    problems = []
    grammar = DIAGRAM_KINDS[kind][0]
    lines = code.splitlines()
    if grammar == 'mindmap':
        if not lines or lines[0].strip() != 'mindmap':
            problems.append('missing mindmap header')
        if len(lines) < 2 or not re.match(r'^\s*root\(\(.*\)\)$', lines[1]):
            problems.append('missing or malformed root')
        for line in lines[2:]:
            if re.search(r'[\[\](){}"]', line):
                problems.append(f'unsafe mindmap label: {line.strip()[:40]}')
        indents = [len(l) - len(l.lstrip(' ')) for l in lines[2:] if l.strip()]
        previous = 1
        for indent in indents:
            if indent // 2 > previous + 1:
                problems.append('indentation jumps more than one level')
                break
            previous = indent // 2
    else:
        if not lines or not lines[0].startswith('flowchart '):
            problems.append('missing flowchart header')
        defined = set(re.findall(r'^\s{4}([A-Za-z]\w*)[\[({]', code, re.M))
        for src, dst in re.findall(r'^\s{4}(\w+)\s*-->(?:\|[^|]*\|)?\s*(\w+)$', code, re.M):
            if src not in defined or dst not in defined:
                problems.append(f'edge to undefined node: {src}->{dst}')
        for line in lines[1:]:
            if '-->' not in line and '"' not in line:
                problems.append(f'node line without quoted label: {line.strip()[:40]}')
    if re.search(r'\\[a-zA-Z]+|\$|`', code):
        problems.append('LaTeX or backtick survived into the diagram')
    if re.search(r'^\s*(?:click|style|classDef|linkStyle)\b', code, re.M):
        problems.append('directive survived into the diagram')
    return problems


async def run(per_cell):
    rows = []
    kind_cycle = 0
    for subject, level in CELLS:
        try:
            topics = [t for t in exam_topics(subject, level, 'KA') if len(t) > 3][:per_cell]
        except Exception as exc:                                   # noqa: BLE001
            print(f'  {subject}/{level}: topic mining failed ({exc})')
            continue
        for topic in topics:
            kind = KINDS[kind_cycle % len(KINDS)]
            kind_cycle += 1
            telemetry = {}
            start = time.time()
            try:
                result = await build_diagram(topic, subject, level, 'KA', kind,
                                             retrieval_result=telemetry)
                error = None
            except Exception as exc:                               # noqa: BLE001
                result, error = {}, f'{type(exc).__name__}: {exc}'
            secs = round(time.time() - start, 1)
            code = result.get('mermaid', '')
            row = {
                'subject': subject, 'level': level, 'topic': topic, 'kind': kind,
                'secs': secs, 'error': error,
                'abstained': bool(result.get('abstained', True)),
                'nodes': result.get('nodes', 0),
                'repaired': bool(result.get('repaired')),
                'has_notes': bool((result.get('notes') or '').strip()),
                'sources': len(result.get('sources') or []),
                'structural_problems': structural_problems(code, kind) if code else [],
                'mermaid': code,
            }
            rows.append(row)
            flag = 'ABSTAIN' if row['abstained'] else f"{row['nodes']} nodes"
            print(f"  {subject[:4]}/{level} {kind:<15} {secs:>5.1f}s  {flag}"
                  f"{'  REPAIRED' if row['repaired'] else ''}"
                  f"{'  PROBLEMS' if row['structural_problems'] else ''}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--per-cell', type=int, default=3)
    parser.add_argument('--out-dir', default='evaluation/results')
    args = parser.parse_args()

    rows = asyncio.run(run(args.per_cell))
    drawn = [r for r in rows if not r['abstained']]
    by_kind = {}
    for kind in KINDS:
        subset = [r for r in rows if r['kind'] == kind]
        if subset:
            by_kind[kind] = {
                'attempts': len(subset),
                'drawn': sum(1 for r in subset if not r['abstained']),
                'mean_nodes': round(sum(r['nodes'] for r in subset if not r['abstained'])
                                    / max(1, sum(1 for r in subset if not r['abstained'])), 1),
            }
    summary = {
        'attempts': len(rows),
        'drawn': len(drawn),
        'abstained': sum(1 for r in rows if r['abstained']),
        'errors': sum(1 for r in rows if r['error']),
        'repaired': sum(1 for r in rows if r['repaired']),
        'with_notes': sum(1 for r in drawn if r['has_notes']),
        'structurally_clean': sum(1 for r in drawn if not r['structural_problems']),
        'all_problems': [p for r in drawn for p in r['structural_problems']],
        'mean_nodes': round(sum(r['nodes'] for r in drawn) / max(1, len(drawn)), 1),
        'min_nodes_floor': MIN_NODES,
        'mean_secs': round(sum(r['secs'] for r in rows) / max(1, len(rows)), 1),
        'by_kind': by_kind,
    }
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'diagram_study.json').write_text(
        json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1),
        encoding='utf-8')
    # Just the sources, for parsing in a browser against the real Mermaid.
    (out / 'diagram_sources.json').write_text(
        json.dumps([{'id': f"{r['subject']}-{r['level']}-{r['kind']}", 'kind': r['kind'],
                     'mermaid': r['mermaid']} for r in drawn], ensure_ascii=False, indent=1),
        encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
