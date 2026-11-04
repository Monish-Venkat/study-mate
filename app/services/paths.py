from pathlib import Path
from app.core.config import settings

BASE = Path(settings.DATA_DIR)
DB = Path(settings.DB_DIR)
TEXTBOOKS = Path(settings.TEXTBOOKS_DIR)
SYLLABUS = Path(settings.SYLLABUS_DIR)
QUESTION_PAPERS = Path(settings.QUESTION_PAPERS_DIR)
FAISS_DIR = Path(settings.VECTOR_DIR)

def ensure_dirs():
    for p in [BASE, DB, TEXTBOOKS, SYLLABUS, QUESTION_PAPERS, FAISS_DIR]:
        p.mkdir(parents=True, exist_ok=True)
    for subject in ['physics', 'chemistry', 'mathematics', 'biology']:
        for level in ['1st', '2nd']:
            (TEXTBOOKS / subject / level).mkdir(parents=True, exist_ok=True)
    for board in ['cbse', 'ka']:
        (QUESTION_PAPERS / board).mkdir(parents=True, exist_ok=True)
