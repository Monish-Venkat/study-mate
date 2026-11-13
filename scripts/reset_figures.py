"""Drop every figure record from the index, keeping the text chunks.

FAISSStore only appends, so re-extracting figures after a change to the
extractor would otherwise mean rebuilding the whole index and re-embedding
thousands of text chunks. The stored vectors can be read back out of the flat
index instead, so the text survives untouched and only the figures go.

The extracted PNG files are left on disk: they are addressed by content hash,
so a re-run writes the same names and any genuinely orphaned file is simply
unreferenced.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--yes', action='store_true', help='Skip the confirmation prompt')
    args = parser.parse_args()

    import faiss
    import numpy as np
    from app.services.faiss_store import store

    total = len(store.meta)
    figures = [i for i, m in enumerate(store.meta) if m.get('doc_type') == 'figure']
    keep = [i for i, m in enumerate(store.meta) if m.get('doc_type') != 'figure']
    print(f'index holds {total} records: {len(figures)} figures, {len(keep)} other')
    if not figures:
        print('nothing to remove')
        return
    if store.index.ntotal != total:
        print(f'refusing: index has {store.index.ntotal} vectors but {total} records')
        return
    if not args.yes:
        print('re-run with --yes to remove the figure records')
        return

    vectors = store.index.reconstruct_n(0, store.index.ntotal)
    kept = np.asarray(vectors, dtype='float32')[keep]
    rebuilt = faiss.IndexFlatIP(store.dim)
    if len(kept):
        rebuilt.add(kept)
    store.index = rebuilt
    store.meta = [store.meta[i] for i in keep]
    store.save()
    print(f'removed {len(figures)} figure records; {store.index.ntotal} vectors remain')


if __name__ == '__main__':
    main()
