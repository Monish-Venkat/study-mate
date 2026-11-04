"""Durable encrypted guest memory, scores, plans and analytics events."""
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from app.core.config import settings
from app.services.security import identity,seal,unseal,key

class MemoryStore:
    @contextmanager
    def db(self):
        key()  # Initialize key before creating the database; never silently replace a lost key.
        path=Path(settings.DB_DIR)/'learning.sqlite3'
        path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(path,timeout=30) as db:
            db.row_factory=sqlite3.Row
            db.execute('CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, scope TEXT NOT NULL, value TEXT NOT NULL, ts REAL NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS record_lookup ON records(owner,kind,scope,ts)')
            db.execute('DELETE FROM records WHERE ts < ?', (time.time()-settings.RETENTION_DAYS*86400,))
            yield db

    def put(self,student_id,kind,value,scope='',replace=False):
        owner=identity(student_id)
        with self.db() as db:
            if replace:db.execute('DELETE FROM records WHERE owner=? AND kind=? AND scope=?',(owner,kind,scope))
            db.execute('INSERT INTO records(owner,kind,scope,value,ts) VALUES(?,?,?,?,?)',(owner,kind,scope,seal(value,owner+kind+scope),time.time()))
            if kind=='turn':
                db.execute('DELETE FROM records WHERE owner=? AND kind=? AND scope=? AND id NOT IN (SELECT id FROM records WHERE owner=? AND kind=? AND scope=? ORDER BY id DESC LIMIT 10)',(owner,kind,scope,owner,kind,scope))

    def read(self,student_id,kind,scope=''):
        owner=identity(student_id)
        with self.db() as db:
            rows=db.execute('SELECT * FROM records WHERE owner=? AND kind=? AND scope=? ORDER BY id',(owner,kind,scope)).fetchall()
        return [unseal(r['value'],owner+kind+scope) for r in rows]

    def save(self,student_id,role,message,scope=''):
        self.put(student_id,'turn',{'role':role,'message':message,'timestamp':time.time()},scope)

    def recent(self,student_id,n=10,scope=''):
        return self.read(student_id,'turn',scope)[-n:]

    def profile(self,student_id,scope=''):
        data=self.read(student_id,'profile',scope)
        return data[-1] if data else {'language':'en','depth':'auto','scores':{}}

    def forget(self,student_id):
        with self.db() as db:db.execute('DELETE FROM records WHERE owner=?',(identity(student_id),))

    def aggregate(self):
        with self.db() as db:rows=db.execute("SELECT * FROM records WHERE kind IN ('event','score')").fetchall()
        return [(r['kind'],unseal(r['value'],r['owner']+r['kind']+r['scope'])) for r in rows]

memory=MemoryStore()

def course_scope(subject,level,board):
    return f'{subject}:{level}:{board}'
