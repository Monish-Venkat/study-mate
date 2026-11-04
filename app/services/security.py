"""AES-256-GCM encryption for local application records."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from functools import lru_cache
from app.core.config import settings

@lru_cache(maxsize=1)
def key():
    if settings.STORAGE_KEY:
        raw = base64.b64decode(settings.STORAGE_KEY, validate=True)
    else:
        if settings.APP_ENV == 'production':
            raise RuntimeError('Set a protected STORAGE_KEY before starting production.')
        path = Path(settings.DB_DIR) / '.storage-key'
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            persona_db=path.parent/'personas.sqlite3'
            encrypted_personas=False
            if persona_db.exists():
                import sqlite3
                with sqlite3.connect(persona_db) as db:
                    encrypted_personas=bool(db.execute("SELECT COUNT(*) FROM educators WHERE descriptor LIKE 'enc:v1:%'").fetchone()[0])
            if (path.parent / 'learning.sqlite3').exists() or encrypted_personas:
                raise RuntimeError('Storage key missing. Restore the original key; encrypted records cannot be recovered with a new key.')
            try:
                fd=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
                with os.fdopen(fd,'wb') as f:f.write(os.urandom(32))
            except FileExistsError:pass
        raw=path.read_bytes()
    if len(raw)!=32:raise RuntimeError('STORAGE_KEY must contain exactly 32 base64-encoded bytes.')
    return raw

def identity(student_id):
    return hmac.new(key(), student_id.encode(), hashlib.sha256).hexdigest()

def seal(value, aad):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce=os.urandom(12)
    payload=json.dumps(value,ensure_ascii=False).encode()
    return base64.b64encode(nonce+AESGCM(key()).encrypt(nonce,payload,aad.encode())).decode()

def unseal(value,aad):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    payload=base64.b64decode(value)
    return json.loads(AESGCM(key()).decrypt(payload[:12],payload[12:],aad.encode()))
