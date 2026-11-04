from pathlib import Path
import json
import numpy as np
import faiss
from threading import RLock
from app.core.config import settings

class FAISSStore:
    def __init__(self, index_dir: str, dim: int = 384):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / 'index.faiss'
        self.meta_path = self.index_dir / 'meta.jsonl'
        self.dim = dim
        self.lock = RLock()
        self.load()

    def load(self):
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.meta = [json.loads(x) for x in self.meta_path.read_text(encoding='utf-8').splitlines() if x.strip()]
        else:
            self.index = faiss.IndexFlatIP(self.dim)
            self.meta = []

    def save(self):
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in self.meta), encoding='utf-8')

    def add(self, vectors, records):
        with self.lock:
            return self._add(vectors, records)

    def _add(self, vectors, records):
        arr = np.array(vectors, dtype='float32')
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.shape[0] != len(records) or arr.shape[1] != self.dim:
            raise ValueError('Vector/record dimensions do not match')
        self.index.add(arr)
        self.meta.extend(records)
        self.save()

    def search(self, vector, k=5, filters=None):
        with self.lock:
            return self._search(vector,k,filters)

    def _search(self, vector, k=5, filters=None):
        if self.index.ntotal == 0:
            return []
        q = np.array(vector, dtype='float32').reshape(1, -1)
        scores, idxs = self.index.search(q, self.index.ntotal)
        out = []
        for s, i in zip(scores[0], idxs[0]):
            if i == -1 or i >= len(self.meta):
                continue
            item = dict(self.meta[i])
            if filters and any(item.get(key) not in values for key, values in filters.items()):
                continue
            item['score'] = float(s)
            out.append(item)
            if len(out) >= k:
                break
        return out

store = FAISSStore(settings.VECTOR_DIR)
