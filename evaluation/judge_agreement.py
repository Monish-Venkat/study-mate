"""Do two judges from different model families agree on the same answers?

Reviewer 1 objected that an LLM judge may share the generator's blind spots.
The paper's mitigation was to separate judge from generator by model family;
that is a design claim until the two are compared on identical output. Both
judges here scored the same cached answers, so any disagreement is the judges'
and not the generator's.

Cohen's kappa is reported for the binary PSC labels because raw agreement
flatters a skewed label distribution: if a metric almost always says "no", two
judges agree often by accident.

    python evaluation/judge_agreement.py
"""
import json
import statistics
from pathlib import Path

RESULTS = Path('evaluation/results')
A = 'judged_eval_qwen2-5-7b.json'
B = 'judged_eval_openrouter-google-gemini-2-5-flash.json'


def load(name):
    path = RESULTS / name
    if not path.exists():
        raise SystemExit(f'missing {path}; run judged_eval.py for that judge first')
    return json.loads(path.read_text(encoding='utf-8'))


def pearson(xs, ys):
    if len(xs) < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return round(num / den, 3) if den else None


def kappa(a, b):
    """Cohen's kappa for two binary labellings."""
    n = len(a)
    if not n:
        return None
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected >= 1.0:
        return None
    return round((observed - expected) / (1 - expected), 3)


def main():
    da, db = load(A), load(B)

    # Faithfulness, paired by benchmark item.
    fa = {r['id']: r for r in da['faithfulness'] if r.get('judge')}
    fb = {r['id']: r for r in db['faithfulness'] if r.get('judge')}
    shared = sorted(set(fa) & set(fb))
    xs = [fa[i]['judge']['faithfulness'] for i in shared]
    ys = [fb[i]['judge']['faithfulness'] for i in shared]
    diffs = [abs(x - y) for x, y in zip(xs, ys)]

    # PSC, paired by question, over answers where the persona actually fired.
    pa = {r['question']: r for r in da['persona'] if r['psc_consistent'] is not None}
    pb = {r['question']: r for r in db['persona'] if r['psc_consistent'] is not None}
    pshared = sorted(set(pa) & set(pb))
    la = [int(bool(pa[q]['psc_consistent'])) for q in pshared]
    lb = [int(bool(pb[q]['psc_consistent'])) for q in pshared]

    report = {
        'judge_a': da['summary']['judge_model'],
        'judge_b': db['summary']['judge_model'],
        'faithfulness': {
            'paired_items': len(shared),
            'mean_a': round(statistics.mean(xs), 3) if xs else None,
            'mean_b': round(statistics.mean(ys), 3) if ys else None,
            'mean_absolute_difference': round(statistics.mean(diffs), 3) if diffs else None,
            'pearson_r': pearson(xs, ys),
            'within_0_25': (round(sum(1 for d in diffs if d <= 0.25) / len(diffs), 3)
                            if diffs else None),
        },
        'psc': {
            'paired_answers': len(pshared),
            'psc_a': round(sum(la) / len(la), 3) if la else None,
            'psc_b': round(sum(lb) / len(lb), 3) if lb else None,
            'raw_agreement': (round(sum(1 for x, y in zip(la, lb) if x == y) / len(la), 3)
                              if la else None),
            'cohens_kappa': kappa(la, lb),
        },
    }
    (RESULTS / 'judge_agreement.json').write_text(json.dumps(report, indent=1),
                                                  encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
