"""Assemble a curriculum QA benchmark from the indexed question-paper corpus.

Questions are taken verbatim from real Karnataka board papers; nothing is
invented. Gold answers and mark-scheme value points are deliberately left empty
for a subject teacher to fill, because a benchmark whose gold answers were
written by the same model family it evaluates is worthless.

The out-of-syllabus split IS authored here on purpose: those items exist to test
abstention, and must be provably outside the indexed corpus.

    python evaluation/build_benchmark.py --per-cell 20
"""
import argparse
import json
import random
import re
from pathlib import Path

from app.services.pyq_analysis import question_records

SUBJECTS = ['physics', 'chemistry', 'mathematics', 'biology']
LEVELS = ['PUC1', 'PUC2']

# Degree-level topics with no place in a PUC syllabus. A grounded system must
# decline these rather than answer from parametric memory.
OUT_OF_SYLLABUS = {
    'physics': ['Explain the Higgs mechanism and electroweak symmetry breaking.',
                'Derive the Schwarzschild metric from the Einstein field equations.',
                'Explain renormalisation in quantum electrodynamics.'],
    'chemistry': ['Explain the mechanism of the Suzuki-Miyaura cross-coupling reaction.',
                  'Describe protein tertiary structure prediction by molecular dynamics.',
                  'Explain the Marcus theory of electron transfer rates.'],
    'mathematics': ['State and prove the Riemann-Roch theorem for algebraic curves.',
                    'Explain the classification of finite simple groups.',
                    'Derive the Ito formula for stochastic integrals.'],
    'biology': ['Explain CRISPR-Cas9 off-target scoring with deep learning models.',
                'Describe single-cell RNA-seq batch-effect correction methods.',
                'Explain the coalescent model in population genetics.'],
}

# Karnataka papers mark allocation as "(2)" or "(2 marks)" after the question.
MARKS = re.compile(r'\(\s*(\d+)\s*(?:marks?|m)?\s*\)|\b(\d+)\s*marks?\b', re.I)


def infer_marks(text):
    """Highest plausible mark value stated in the question."""
    values = []
    for match in MARKS.finditer(text):
        value = int(next(g for g in match.groups() if g))
        if 1 <= value <= 10:
            values.append(value)
    return max(values) if values else None


def usable(text):
    words = text.split()
    if not 6 <= len(words) <= 90:
        return False
    # Drop extraction debris: instruction lines and pure headers.
    if re.match(r'^(part|section|answer any|instructions?|note)\b', text.strip(), re.I):
        return False
    # Bilingual Kannada/English PDFs often extract as fragments. Require enough
    # real words to be a readable question rather than surviving punctuation.
    real = [w for w in words if len(re.sub(r'[^A-Za-z]', '', w)) >= 3]
    if len(real) < 5 or len(real) / len(words) < 0.5:
        return False
    letters = len(re.findall(r'[A-Za-z]', text))
    return letters / max(len(text), 1) >= 0.55


def build(per_cell, seed):
    rng = random.Random(seed)
    items, seen = [], set()

    for subject in SUBJECTS:
        for level in LEVELS:
            records, origin = question_records(subject, level, 'KA')
            pool = []
            for record in records:
                text = ' '.join(record['text'].split())
                key = text.lower()[:90]
                if key in seen or not usable(text):
                    continue
                seen.add(key)
                pool.append((text, record))
            rng.shuffle(pool)
            for text, record in pool[:per_cell]:
                items.append({
                    'id': f'{subject[:4]}-{level}-{len(items):04d}',
                    'question': text,
                    'subject': subject,
                    'level': level,
                    'board': 'KA',
                    'answerable': True,
                    'marks': infer_marks(text),
                    'source_file': record.get('source'),
                    'source_year': record.get('year'),
                    'extraction': origin,
                    # To be completed by a subject teacher:
                    'gold_answer': '',
                    'mark_scheme_points': [],
                    'topic': '',
                    'bloom': '',
                    'verified_by': '',
                })

    for subject, questions in OUT_OF_SYLLABUS.items():
        for level in LEVELS:
            for question in questions:
                items.append({
                    'id': f'{subject[:4]}-{level}-oos-{len(items):04d}',
                    'question': question,
                    'subject': subject,
                    'level': level,
                    'board': 'KA',
                    'answerable': False,
                    'marks': None,
                    'source_file': None,
                    'source_year': None,
                    'extraction': 'authored: out-of-syllabus probe',
                    'gold_answer': 'SYSTEM SHOULD DECLINE',
                    'mark_scheme_points': [],
                    'topic': 'out-of-syllabus',
                    'bloom': '',
                    'verified_by': 'design',
                })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--per-cell', type=int, default=20,
                        help='answerable questions per subject/level cell')
    parser.add_argument('--seed', type=int, default=20260911)
    parser.add_argument('--out', default='evaluation/benchmark.json')
    args = parser.parse_args()

    items = build(args.per_cell, args.seed)
    answerable = sum(1 for i in items if i['answerable'])
    payload = {
        'name': 'StudyMate Karnataka PUC curriculum QA benchmark',
        'version': '0.1',
        'seed': args.seed,
        'counts': {'total': len(items), 'answerable': answerable,
                   'out_of_syllabus': len(items) - answerable},
        'provenance': 'Questions extracted verbatim from Karnataka PUC board papers; '
                      'out-of-syllabus probes authored to test abstention.',
        'status': 'gold_answer, mark_scheme_points, topic and bloom require teacher annotation.',
        'items': items,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(items)} items ({answerable} answerable, {len(items)-answerable} out-of-syllabus) -> {path}')
    for subject in SUBJECTS:
        for level in LEVELS:
            n = sum(1 for i in items if i['subject'] == subject and i['level'] == level and i['answerable'])
            print(f'  {subject:12} {level}: {n}')


if __name__ == '__main__':
    main()
