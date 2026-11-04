"""Persistent local educator profiles and isolated transcript vectors."""
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.core.config import settings
from app.services.security import seal,unseal

class PersonaStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS educators (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, subject TEXT NOT NULL,
                descriptor TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY, educator_id TEXT NOT NULL, video_id TEXT NOT NULL,
                title TEXT NOT NULL, url TEXT NOT NULL, language TEXT NOT NULL,
                status TEXT NOT NULL, error TEXT, origin TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(educator_id, video_id),
                FOREIGN KEY(educator_id) REFERENCES educators(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS passages (
                id INTEGER PRIMARY KEY, video_key TEXT NOT NULL,
                text TEXT NOT NULL, start REAL, end REAL, vector TEXT NOT NULL,
                FOREIGN KEY(video_key) REFERENCES videos(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS passage_video ON passages(video_key);
            ''')

    @contextmanager
    def connection(self):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            yield db

    def listing(self):
        with self.connection() as db:
            result = []
            for row in db.execute('SELECT * FROM educators ORDER BY name'):
                educator = dict(row)
                educator['descriptor'] = (unseal(row['descriptor'][7:], row['id']) if row['descriptor'].startswith('enc:v1:') else json.loads(row['descriptor'])) if row['descriptor'] else None
                educator['videos'] = [dict(v) for v in db.execute('''SELECT v.*, COUNT(p.id) AS passage_count
                    FROM videos v LEFT JOIN passages p ON p.video_key=v.id
                    WHERE educator_id=? GROUP BY v.id ORDER BY v.updated_at DESC''', (row['id'],))]
                educator['passage_count'] = sum(v['passage_count'] for v in educator['videos'] if v['status']=='ready')
                educator['ready'] = bool(educator['descriptor'] and educator['passage_count'] >= 5)
                result.append(educator)
            return result

    def get(self, educator_id):
        return next((e for e in self.listing() if e['id']==educator_id), None)

    def passages(self, educator_id):
        with self.connection() as db:
            rows = [dict(r) for r in db.execute('''SELECT p.*, v.url, v.title, v.origin FROM passages p
                JOIN videos v ON v.id=p.video_key WHERE v.educator_id=? AND v.status='ready'
                ORDER BY p.id''', (educator_id,))]
            for row in rows:
                if row['text'].startswith('enc:v1:'):
                    row['text'] = unseal(row['text'][7:], row['video_key'])
            return rows

    def recover(self):
        with self.connection() as db:
            # Migrate existing plaintext profiles/passages on startup.
            for row in db.execute('SELECT id,descriptor FROM educators WHERE descriptor IS NOT NULL').fetchall():
                if not row['descriptor'].startswith('enc:v1:'):
                    db.execute('UPDATE educators SET descriptor=? WHERE id=?',('enc:v1:'+seal(json.loads(row['descriptor']),row['id']),row['id']))
            for row in db.execute('SELECT id,video_key,text FROM passages').fetchall():
                if not row['text'].startswith('enc:v1:'):
                    db.execute('UPDATE passages SET text=? WHERE id=?',('enc:v1:'+seal(row['text'],row['video_key']),row['id']))
            db.execute("UPDATE videos SET status='failed',error='Import interrupted by server restart. Register this video again to retry.' WHERE status='processing'")

_store = None

def persona_store():
    global _store
    if _store is None:
        _store = PersonaStore(Path(settings.DB_DIR) / 'personas.sqlite3')
    return _store
