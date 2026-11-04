import json
from pathlib import Path
from app.core.config import settings


def syllabus_topics(subject,level,board):
    path=Path(settings.SYLLABUS_DIR)/f'{subject}-{level}-{board}.json'
    if not path.exists():return []
    return json.loads(path.read_text(encoding='utf-8'))['topics']


def save_syllabus(subject,level,board,topics):
    path=Path(settings.SYLLABUS_DIR)/f'{subject}-{level}-{board}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'topics':list(dict.fromkeys(topics))},ensure_ascii=False),encoding='utf-8')
