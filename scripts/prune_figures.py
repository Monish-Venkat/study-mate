"""Remove figure records from the index so they can be rebuilt.

FAISSStore only appends, so a figure indexed under an old caption rule stays
indexed. Rebuilding the whole store would mean re-embedding every text chunk,
which is minutes of work to correct a handful of rows — so the figure vectors
are removed in place instead.

IndexFlat.remove_ids compacts the index while preserving the relative order of
the vectors it keeps, so filtering `meta` by the same positions keeps the two
aligned. Run with the backend stopped: it holds the store in memory and would
write its stale copy back on the next add.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import faiss
import numpy as np

from app.services.faiss_store import store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--doc-type', default='figure', help="Record doc_type to remove (default: figure)")
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    positions = [i for i, record in enumerate(store.meta) if record.get('doc_type') == args.doc_type]
    print(f'index vectors: {store.index.ntotal}, meta rows: {len(store.meta)}')
    if store.index.ntotal != len(store.meta):
        print('REFUSING: index and meta are already out of step; rebuild from scratch instead.')
        return 1
    if not positions:
        print(f'nothing to remove for doc_type={args.doc_type!r}')
        return 0
    print(f'removing {len(positions)} {args.doc_type} records at positions {positions[:12]}'
          + ('...' if len(positions) > 12 else ''))
    if args.dry_run:
        print('(dry run, nothing written)')
        return 0

    with store.lock:
        removed = store.index.remove_ids(faiss.IDSelectorBatch(np.array(positions, dtype='int64')))
        drop = set(positions)
        store.meta = [record for i, record in enumerate(store.meta) if i not in drop]
        store.save()
    print(f'removed {removed} vectors')
    print(f'now: index {store.index.ntotal}, meta {len(store.meta)}')
    assert store.index.ntotal == len(store.meta), 'index and meta diverged'
    print('index and meta aligned')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
