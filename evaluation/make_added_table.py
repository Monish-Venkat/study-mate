"""Render the evidence-floor comparison and the grounding audit as paper tables.

Kept separate from make_table.py because these rows are not interchangeable
with the published ablation: they were measured in a later session, so the
baseline is re-run alongside them rather than reused. Mixing a new row into a
table whose other rows came from a different run would overstate comparability.

    python evaluation/make_added_table.py
"""
import json
from pathlib import Path

FLOOR_ROWS = [
    ('full_rerun', r'filter\,+\,CRAG ($3$B)'),
    ('floor', r'\quad +\,evidence floor'),
]

FLOOR_COLUMNS = [
    ('avg_sources', 'Src.', '{:.2f}'),
    ('abstention_precision', r'Abst.\,P', '{:.2f}'),
    ('abstention_recall', r'Abst.\,R', '{:.2f}'),
    ('false_abstentions', 'False', '{:d}'),
    ('avg_restored', 'Rest.', '{:.2f}'),
    ('avg_secs', r'Lat.\,(s)', '{:.1f}'),
]


def load(name, results_dir='evaluation/results'):
    path = Path(results_dir) / f'{name}.json'
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))['summary']


def floor_table(rows):
    lines = [r'\begin{table}[htbp]',
             r'\caption{Effect of the evidence floor, $48$ items per configuration from the',
             r'physics split. Both rows were measured in the same session; the baseline is',
             r'a re-run of the shipped configuration of Table~\ref{tab:ablation} rather than',
             r'its published numbers, because generation is sampled and the two differ',
             r'slightly. \emph{Rest.} is the mean number of passages restored past the',
             r'grader per request.}',
             r'\label{tab:floor}', r'\centering',
             r'\begin{tabular}{l' + 'r' * len(FLOOR_COLUMNS) + '}', r'\toprule',
             r'\textbf{Configuration} & ' +
             ' & '.join(f'\\textbf{{{c[1]}}}' for c in FLOOR_COLUMNS) + r' \\',
             r'\midrule']
    for key, label in rows:
        summary = load(key)
        if not summary:
            continue
        cells = [c[2].format(summary.get(c[0], 0)) for c in FLOOR_COLUMNS]
        lines.append(f'{label} & ' + ' & '.join(cells) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def grounding_report(summary):
    if not summary or 'grounding_items' not in summary:
        return '(no grounding statistics in floor_ground.json)'
    answered = summary['grounding_items']
    return '\n'.join([
        f"answers audited              {answered}",
        f"mean claims per answer       {summary['avg_claims']}",
        f"mean grounded fraction       {summary['avg_grounded_fraction']}",
        f"mean cited fraction          {summary['avg_cited_fraction']}",
        f"answers with >=1 unsupported {summary['answers_with_unsupported']}"
        f"  ({100 * summary['answers_with_unsupported'] / answered:.0f}%)",
        f"answers with dangling cite   {summary['answers_with_dangling']}"
        f"  ({100 * summary['answers_with_dangling'] / answered:.0f}%)",
        f"latency with audit (s)       {summary['avg_secs']}",
    ])


def main():
    out = Path('evaluation/results')
    missing = [k for k, _ in FLOOR_ROWS if not load(k)]
    if missing:
        print(f'missing results: {", ".join(missing)} -- run evaluation/run_added.sh first')
    table = floor_table(FLOOR_ROWS)
    (out / 'floor.tex').write_text(table + '\n', encoding='utf-8')
    print(table)
    print()
    print('--- grounding audit (floor_ground) ---')
    print(grounding_report(load('floor_ground')))
    print()
    print(f"-> {out / 'floor.tex'}")


if __name__ == '__main__':
    main()
