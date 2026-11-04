"""Two retrieval measurements that need no generation, over the full benchmark.

A. Separability of in-syllabus from out-of-syllabus questions by dense
   similarity alone. The evidence floor restores passages the grader rejected,
   so it must only fire when the index plainly considers the question on topic.
   This measures where that threshold can sit, rather than asserting one.

B. Whether fusing a lexical arm with the dense index changes what is retrieved.
   Relevance is not annotated in this benchmark, so the proxy is explicit and
   deliberately narrow: whether the passage containing the question's rarest
   content word is retrieved, and at what rank. It measures exact-term recall,
   which is the specific weakness a lexical arm is supposed to repair -- not
   relevance, and it is not reported as such.

    python evaluation/retrieval_study.py [--limit N]
"""
import argparse
import asyncio
import json
import statistics
from pathlib import Path

from app.services.embeddings import embed_text
from app.services.faiss_store import store
from app.services.lexical import bm25, fuse, lexical_hits, tokenize

LEVEL = {'PUC1': '1st', 'PUC2': '2nd'}
CANDIDATES = 40
TOP_K = 5


def filters_for(item):
    return {'subject': [item['subject'].lower()],
            'level': [LEVEL.get(item['level'], item['level'].lower())],
            'board': [item['board'].lower()],
            'doc_type': ['textbook', 'syllabus']}


def rarest_term(question):
    """The question's lowest-document-frequency content word.

    Rare words are the ones a dense encoder is most likely to blur and a
    lexical index most likely to catch, so they are where the two arms should
    disagree if they ever do.
    """
    best, best_df = None, None
    for token in set(tokenize(question)):
        if len(token) < 4:
            continue
        df = len(bm25.postings.get(token, ()))
        if df == 0:
            continue
        if best_df is None or df < best_df:
            best, best_df = token, df
    return best


def rank_of(hits, term):
    for position, hit in enumerate(hits, 1):
        if term in hit.get('text', '').lower():
            return position
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark', default='evaluation/benchmark.json')
    parser.add_argument('--out', default='evaluation/results/retrieval_study.json')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    items = json.loads(Path(args.benchmark).read_text(encoding='utf-8'))['items']
    if args.limit:
        items = items[:args.limit]
    bm25.ensure(store.meta)
    print(f'index={store.index.ntotal} passages, vocabulary={len(bm25.postings)} terms')

    answerable_top, unanswerable_top = [], []
    dense_ranks, hybrid_ranks, probes = [], [], 0

    for index, item in enumerate(items, 1):
        vector = embed_text(item['question'])
        filters = filters_for(item)
        dense = store.search(vector, CANDIDATES, filters)
        if not dense:
            continue
        top = dense[0]['score']
        (answerable_top if item['answerable'] else unanswerable_top).append(top)

        if item['answerable']:
            term = rarest_term(item['question'])
            if term:
                lexical = lexical_hits(item['question'], vector, store, filters, CANDIDATES)
                hybrid = fuse(dense, lexical, TOP_K) if lexical else dense[:TOP_K]
                dense_ranks.append(rank_of(dense[:TOP_K], term))
                hybrid_ranks.append(rank_of(hybrid, term))
                probes += 1
        if index % 25 == 0:
            print(f'  {index}/{len(items)}')

    def spread(values):
        values = sorted(values)
        return {'n': len(values), 'min': round(values[0], 3), 'max': round(values[-1], 3),
                'mean': round(statistics.mean(values), 3),
                'median': round(statistics.median(values), 3),
                'p05': round(values[max(0, int(0.05 * len(values)) - 1)], 3),
                'p95': round(values[min(len(values) - 1, int(0.95 * len(values)))], 3)}

    # Where can the floor sit? Sweep it and count both kinds of mistake.
    sweep = []
    for threshold in [t / 100 for t in range(30, 71, 5)]:
        sweep.append({
            'threshold': threshold,
            # In-syllabus questions whose evidence the floor could NOT restore.
            'answerable_below': sum(1 for s in answerable_top if s < threshold),
            # Out-of-syllabus questions the floor would wrongly let through.
            'unanswerable_above': sum(1 for s in unanswerable_top if s >= threshold),
        })

    def mrr(ranks):
        return round(statistics.mean(1 / r if r else 0.0 for r in ranks), 3)

    report = {
        'passages': store.index.ntotal,
        'vocabulary': len(bm25.postings),
        'top1_similarity': {'answerable': spread(answerable_top),
                            'unanswerable': spread(unanswerable_top)},
        'threshold_sweep': sweep,
        'exact_term_probe': {
            'questions': probes,
            'dense_mrr': mrr(dense_ranks),
            'hybrid_mrr': mrr(hybrid_ranks),
            'dense_hits_at_5': sum(1 for r in dense_ranks if r),
            'hybrid_hits_at_5': sum(1 for r in hybrid_ranks if r),
            'hybrid_better': sum(1 for d, h in zip(dense_ranks, hybrid_ranks)
                                 if h and (not d or h < d)),
            'dense_better': sum(1 for d, h in zip(dense_ranks, hybrid_ranks)
                                if d and (not h or d < h)),
            'tied': sum(1 for d, h in zip(dense_ranks, hybrid_ranks) if d == h),
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(json.dumps(report, indent=1))
    print(f'-> {out}')


if __name__ == '__main__':
    main()
