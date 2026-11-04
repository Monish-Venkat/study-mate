from pathlib import Path
import re
from pypdf import PdfReader
from app.core.config import settings
from app.services.embeddings import embed_text, embed_texts, get_model, model_lock
from app.services.faiss_store import store


def chunk_text(text: str, size: int = 700, overlap: int = 120):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Chunk size must be positive and overlap smaller than size')
    text = ' '.join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def detect_category(path: Path):
    parts = [x.lower() for x in path.parts]
    if 'question_papers' in parts:
        return 'question_paper'
    return 'syllabus' if 'syllabus' in parts else 'textbook'


def infer_subject_level(path: Path):
    parts = [x.lower() for x in path.parts]
    name = path.name.lower()
    # NCERT chemistry files were accidentally placed inside mathematics/1st.
    if name.startswith('kech'):
        subject = 'chemistry'
    else:
        subject = next((s for s in settings.subjects_list() if s in parts or s in name), 'general')
    level = '2nd' if '2nd' in parts else ('1st' if '1st' in parts else 'general')
    if detect_category(path) == 'question_paper':
        level = '1st' if 'puc-1' in name else '2nd'
    board = 'cbse' if 'cbse' in parts else 'ka'
    return subject, level, board


def token_chunks(text, tokenizer, size=500, overlap=50):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Invalid token window')
    # Preserve paragraph endings where possible, split long paragraphs only as needed.
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n',text) if p.strip()]
    pending=[]
    for paragraph in paragraphs:
        tokens=tokenizer.encode(paragraph,add_special_tokens=False)
        if pending and len(pending)+len(tokens)>size:
            yield tokenizer.decode(pending,skip_special_tokens=True)
            pending=pending[-overlap:] if overlap else []
        for token in tokens:
            pending.append(token)
            if len(pending)==size:
                yield tokenizer.decode(pending,skip_special_tokens=True)
                pending=pending[-overlap:] if overlap else []
    if pending:
        yield tokenizer.decode(pending,skip_special_tokens=True)


def ingest_pdf(path: str):
    p = Path(path)
    subject, level, board = infer_subject_level(p)
    doc_type = detect_category(p)
    source_path = p.resolve().as_posix()
    if any(record.get('source_path') == source_path for record in store.meta):
        return {'file': p.name, 'chunks': 0, 'skipped': True}
    years = re.findall(r'20\d{2}', p.name)
    vectors, records = [], []
    tokenizer = get_model().tokenizer
    # Uploads are indexed on a worker thread; the shared tokenizer is not
    # thread-safe, so chunking must not overlap a query embedding.
    with model_lock:
        for page_number, page in enumerate(PdfReader(path).pages, 1):
            for chunk in token_chunks(page.extract_text() or '', tokenizer, settings.DOCUMENT_TOKENS, settings.DOCUMENT_OVERLAP):
                records.append({'text': chunk, 'subject': subject, 'level': level, 'board': board,
                                'doc_type': doc_type, 'source': p.name, 'source_path': source_path,
                                'page': page_number, 'year': int(years[0]) if years else None,
                                'chunk_id': len(records)})
    if records:
        vectors = embed_texts([record["text"] for record in records])
        store.add(vectors, records)
    return {'file': p.name, 'chunks': len(records), 'subject': subject, 'level': level}
