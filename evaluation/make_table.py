"""Render the ablation results as a paper-ready table (Markdown + LaTeX)."""
import json
from pathlib import Path

ORDER = [
    ('vanilla', 'Vanilla RAG'),
    ('filter_only', r'+ boilerplate filter'),
    ('crag_only', r'+ CRAG'),
    ('full', r'+ filter + CRAG (3B grader)'),
    ('full_strong_grader', r'+ filter + CRAG (strong grader)'),
]

COLUMNS = [
    ('avg_sources', 'Passages', '{:.2f}'),
    ('citation_rate', 'Cite rate', '{:.2f}'),
    ('abstention_precision', 'Abst. P', '{:.2f}'),
    ('abstention_recall', 'Abst. R', '{:.2f}'),
    ('false_abstentions', 'False abst.', '{:d}'),
    ('avg_secs', 'Latency (s)', '{:.1f}'),
]


def load(results_dir):
    rows = []
    for key, label in ORDER:
        path = Path(results_dir) / f'{key}.json'
        if path.exists():
            rows.append((label, json.loads(path.read_text(encoding='utf-8'))['summary']))
    return rows


def markdown(rows):
    head = '| Configuration | ' + ' | '.join(c[1] for c in COLUMNS) + ' |'
    rule = '|---' * (len(COLUMNS) + 1) + '|'
    lines = [head, rule]
    for label, s in rows:
        cells = [c[2].format(s.get(c[0], 0)) for c in COLUMNS]
        lines.append(f'| {label} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def latex(rows):
    spec = 'l' + 'r' * len(COLUMNS)
    lines = [r'\begin{table}[htbp]',
             r'\caption{Ablation of the corrective retrieval layer. Passages is the mean number'
             r' supplied to the generator; abstention precision and recall are measured against'
             r' the out-of-syllabus split.}',
             r'\label{tab:ablation}',
             f'\\begin{{tabular}}{{{spec}}}', r'\toprule',
             'Configuration & ' + ' & '.join(c[1].replace('+', r'\,+\,') for c in COLUMNS) + r' \\',
             r'\midrule']
    for label, s in rows:
        cells = [c[2].format(s.get(c[0], 0)) for c in COLUMNS]
        lines.append(f'{label} & ' + ' & '.join(cells) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}']
    return '\n'.join(lines)


def main():
    rows = load('evaluation/results')
    if not rows:
        print('No results in evaluation/results. Run evaluation/run_ablation.sh first.')
        return
    n = rows[0][1].get('items', '?')
    md = f'Benchmark items per configuration: {n}\n\n' + markdown(rows)
    out = Path('evaluation/results')
    (out / 'ablation.md').write_text(md + '\n', encoding='utf-8')
    (out / 'ablation.tex').write_text(latex(rows) + '\n', encoding='utf-8')
    print(md)
    print('\nwrote evaluation/results/ablation.md and ablation.tex')


if __name__ == '__main__':
    main()
