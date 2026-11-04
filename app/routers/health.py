from fastapi import APIRouter
from app.services.faiss_store import store
router = APIRouter(tags=['health'])

@router.get('/health')
async def health():
    return {'status': 'ok', 'indexed_chunks': store.index.ntotal,
            'index_ready': bool(store.index.ntotal)}
