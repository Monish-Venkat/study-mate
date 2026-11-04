"""Render the judged evaluation and the judge-disagreement result as a table."""
import json
from pathlib import Path

RESULTS = Path('evaluation/results')
FILES = [('Qwen2.5-7B', 'judged_eval_qwen2-5-7b.json'),
         ('Gemini 2.5', 'judged_eval_openrouter-google-gemini-2-5-flash.json')]


def load(name):
    path = RESULTS / name
    return json.loads(path.read_text(encoding='utf-8'))['summary'] if path.exists() else None


def main():
    cols = [(label, load(name)) for label, name in FILES]
    cols = [(label, s) for label, s in cols if s]
    agree = json.loads((RESULTS / 'judge_agreement.json').read_text(encoding='utf-8'))

    rows = [
        ('Faithfulness (RAGAS definition)', 'mean_faithfulness', '{:.3f}'),
        ('Statements extracted per answer', 'mean_statements_per_answer', '{:.1f}'),
        ('Answer relevancy (judge-rated)', 'mean_relevancy', '{:.3f}'),
        ('PSC (submitted target $0.78$)', 'psc', '{:.3f}'),
    ]
    lines = [r'\begin{table}[htbp]',
             r'\caption{Judged evaluation of the same $22$ answers and $9$ persona answers by '
             r'two judges: Qwen2.5-7B, from the generator\textquotesingle{}s own family, and '
             r'Gemini 2.5 Flash from another. The generator is Qwen2.5-3B throughout, so the '
             r'columns differ only in who is scoring. Faithfulness follows the RAGAS definition; relevancy is a '
             r'direct judge rating, not RAGAS\textquotesingle{}s question-regeneration procedure.}',
             r'\label{tab:judged}', r'\centering',
             r'\begin{tabular}{lrr}', r'\toprule',
             r'\textbf{Measure} & ' + ' & '.join(f'\\textbf{{{c[0]}}}' for c in cols) + r' \\',
             r'\midrule']
    for label, key, fmt in rows:
        cells = []
        for _, summary in cols:
            value = summary.get(key)
            cells.append(fmt.format(value) if value is not None else '--')
        lines.append(f'{label} & ' + ' & '.join(cells) + r' \\')
    f, p = agree['faithfulness'], agree['psc']
    lines += [r'\midrule',
              r'\multicolumn{3}{l}{\emph{Agreement between the two judges}} \\',
              f"Faithfulness correlation ($r$) & \\multicolumn{{2}}{{r}}{{{f['pearson_r']}}} \\\\",
              f"Mean absolute difference & \\multicolumn{{2}}{{r}}{{{f['mean_absolute_difference']}}} \\\\",
              f"PSC agreement ($\\kappa$) & \\multicolumn{{2}}{{r}}{{{p['cohens_kappa']}}} \\\\",
              r'\bottomrule', r'\end{tabular}', r'\end{table}']
    table = '\n'.join(lines)
    (RESULTS / 'judged.tex').write_text(table + '\n', encoding='utf-8')
    print(table)


if __name__ == '__main__':
    main()
