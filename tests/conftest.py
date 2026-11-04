import pytest
from app.core.config import settings
from app.services.security import key
from app.main import _hits

@pytest.fixture(autouse=True)
def isolated_learning(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'DB_DIR',str(tmp_path/'db'))
    monkeypatch.setattr(settings,'STORAGE_KEY','')
    key.cache_clear()
    _hits.clear()
    yield
    key.cache_clear()
