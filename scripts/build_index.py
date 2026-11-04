"""Build the local index. Reruns skip existing source paths; use a new VECTOR_DIR to rebuild."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='List source PDFs without embedding')
    parser.add_argument('--limit', type=int, help='Index only the first N PDFs for a smoke test')
    args = parser.parse_args()
    files = sorted({p for root in (settings.QUESTION_PAPERS_DIR, settings.SYLLABUS_DIR, settings.TEXTBOOKS_DIR)
                    for p in Path(root).rglob('*') if p.is_file() and p.suffix.lower() == '.pdf'})
    if args.limit is not None:
        if args.limit < 1:
            parser.error('--limit must be positive')
        files = files[:args.limit]
    if args.dry_run:
        for p in files:
            print(p)
        print(f'{len(files)} PDFs found')
        return
    from app.services.ingest import ingest_pdf
    failures = 0
    for p in files:
        try:
            print(json.dumps(ingest_pdf(str(p))), flush=True)
        except Exception as exc:
            failures += 1
            print(f'FAILED {p}: {exc}', file=sys.stderr, flush=True)
    if failures:
        raise SystemExit(1)
    print(f'Finished scanning {len(files)} PDFs. Restart the API to load the updated index.')

if __name__ == '__main__':
    main()
