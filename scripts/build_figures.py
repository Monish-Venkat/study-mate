"""Extract captioned figures from the textbook PDFs and index their captions.

Figures are written to data/figures/<subject>/<level>/<id>.png and their
captions are added to the same FAISS index as the text, under doc_type
'figure', so retrieval filters by subject and year exactly as it already does.

Reruns skip any PDF whose figures are already indexed. Extraction is slow
(embedded images are decoded page by page), so --subject and --limit exist to
let it run a book or a subject at a time.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.figures import extract, figures_dir
from app.services.ingest import infer_subject_level


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subject', help='Only this subject (physics, chemistry, mathematics, biology)')
    parser.add_argument('--limit', type=int, help='Only the first N PDFs')
    parser.add_argument('--dry-run', action='store_true', help='Extract and report without embedding')
    args = parser.parse_args()

    files = sorted(p for p in Path(settings.TEXTBOOKS_DIR).rglob('*')
                   if p.is_file() and p.suffix.lower() == '.pdf')
    if args.subject:
        files = [p for p in files if infer_subject_level(p)[0] == args.subject.lower()]
    if args.limit is not None:
        if args.limit < 1:
            parser.error('--limit must be positive')
        files = files[:args.limit]
    if not files:
        print('No matching textbook PDFs found.')
        return

    from app.services.faiss_store import store
    done = {r.get('source_path') for r in store.meta if r.get('doc_type') == 'figure'}

    out_dir = figures_dir()
    total = 0
    for index, pdf in enumerate(files, 1):
        subject, level, board = infer_subject_level(pdf)
        if pdf.resolve().as_posix() in done:
            print(f'[{index}/{len(files)}] {pdf.name}: already indexed, skipping')
            continue
        records = extract(pdf, subject, level, board, out_dir)
        total += len(records)
        print(f'[{index}/{len(files)}] {pdf.name} ({subject}/{level}): {len(records)} figures')
        if records and not args.dry_run:
            from app.services.embeddings import embed_texts
            vectors = embed_texts([r['text'] for r in records])
            # The image bytes are on disk; only the caption and its provenance
            # belong in the index.
            store.add(vectors, records)

    print(f'\n{total} figures extracted from {len(files)} PDFs'
          + (' (dry run, nothing indexed)' if args.dry_run else f' into {out_dir}'))


if __name__ == '__main__':
    main()
