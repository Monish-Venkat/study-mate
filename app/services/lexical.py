"""Lexical retrieval, fused with the dense index.

A 384-dimensional embedding is a lossy summary. It generalises well, which is
what makes semantic search work, but the same compression blurs the rare tokens
that carry most of the meaning in a science syllabus. "Snell", "Le Chatelier",
"Avogadro" and "sigma bond" all sit near their topical neighbourhood in vector
space, so a query naming one of them can rank a passage that merely discusses
the surrounding topic above the passage that actually defines it.

BM25 has the opposite bias: it cannot see that "lens formula" and "thin lens
equation" are the same thing, but it will never miss the passage containing the
exact term the student typed. Fusing the two rankings keeps each one's strength
without having to tune a weight between incomparable score scales -- reciprocal
rank fusion combines positions, not scores, so a cosine of 0.42 never has to be
made commensurate with a BM25 score of 11.3.
"""
import math
import re
from collections import defaultdict
from threading import RLock

from app.core.config import settings

K1 = 1.5
B = 0.75

# Function words carry no retrieval signal but appear in nearly every chunk, so
# they cost time and flatten idf. Deliberately short: anything with subject
# meaning, including "work", "force" and "state", must stay.
_STOP = frozenset('''a an and are as at be been by for from had has have he her his how i if in
into is it its of on or s so such t than that the their then there these they this to was were
what when where which who will with would you your'''.split())

_TOKEN = re.compile(r'[a-z0-9]+(?:[.\-][a-z0-9]+)*')


def tokenize(text):
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


class BM25Index:
    """An inverted index over the vector store's chunk metadata.

    Built lazily and rebuilt when the store grows, so ingestion does not have
    to know this module exists.
    """

    def __init__(self):
        self.lock = RLock()
        self.size = -1
        self.postings = {}
        self.lengths = []
        self.avg_length = 0.0
        self.idf = {}

    def _build(self, meta):
        postings = defaultdict(list)
        lengths = []
        for position, record in enumerate(meta):
            tokens = tokenize(record.get('text', ''))
            lengths.append(len(tokens))
            counts = defaultdict(int)
            for token in tokens:
                counts[token] += 1
            for token, count in counts.items():
                postings[token].append((position, count))
        total = len(meta)
        self.postings = dict(postings)
        self.lengths = lengths
        self.avg_length = (sum(lengths) / total) if total else 0.0
        self.idf = {token: math.log(1 + (total - len(plist) + 0.5) / (len(plist) + 0.5))
                    for token, plist in self.postings.items()}
        self.size = total

    def ensure(self, meta):
        if self.size != len(meta):
            with self.lock:
                if self.size != len(meta):
                    self._build(meta)

    def search(self, query, meta, limit, keep):
        """Return [(position, score)] best first, over positions `keep` accepts."""
        self.ensure(meta)
        if not self.avg_length:
            return []
        scores = defaultdict(float)
        for token in set(tokenize(query)):
            plist = self.postings.get(token)
            if not plist:
                continue
            idf = self.idf[token]
            for position, count in plist:
                if not keep(position):
                    continue
                length = self.lengths[position] or 1
                norm = count + K1 * (1 - B + B * length / self.avg_length)
                scores[position] += idf * count * (K1 + 1) / norm
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:limit]


bm25 = BM25Index()


def _key(record):
    return (record.get('source'), record.get('page'), record.get('text', '')[:120])


def fuse(dense_hits, lexical_hits, limit, k=None):
    """Reciprocal rank fusion of two ranked lists of chunk records."""
    k = settings.RRF_K if k is None else k
    scores = defaultdict(float)
    best = {}
    for ranking in (dense_hits, lexical_hits):
        for rank, hit in enumerate(ranking):
            key = _key(hit)
            scores[key] += 1.0 / (k + rank + 1)
            # Keep whichever copy carries a dense similarity, so downstream
            # thresholds and telemetry still see a comparable number.
            if key not in best or (hit.get('score', 0) > best[key].get('score', 0)):
                best[key] = hit
    order = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    out = []
    for key, score in order[:limit]:
        hit = dict(best[key])
        hit['rrf_score'] = round(score, 5)
        out.append(hit)
    return out


def lexical_hits(query, vector, store, filters, limit):
    """BM25 results shaped like dense results, honouring the same filters.

    A lexical hit still needs a cosine. Downstream stages apply a similarity
    floor to every passage, and a hit that arrives without a comparable score
    would either be discarded unread or smuggled past the floor. The index is
    flat inner-product over normalised vectors, so the true cosine can simply
    be reconstructed for the handful of candidates this arm returns.
    """
    import numpy as np

    meta = store.meta

    def keep(position):
        record = meta[position]
        return not filters or all(
            record.get(field) in values for field, values in filters.items())

    query_vector = np.asarray(vector, dtype='float32').reshape(-1)
    results = []
    for position, score in bm25.search(query, meta, limit, keep):
        record = dict(meta[position])
        record['lexical_score'] = round(score, 4)
        try:
            stored = store.index.reconstruct(int(position))
            record['score'] = float(np.dot(np.asarray(stored, dtype='float32').reshape(-1),
                                           query_vector))
        except (RuntimeError, AttributeError, ValueError):
            # Reconstruction is unavailable on some index types. The passage
            # did match the query lexically, so it is admitted at exactly the
            # floor rather than being dropped or flattered.
            record['score'] = settings.MIN_SIMILARITY
        results.append(record)
    return results
