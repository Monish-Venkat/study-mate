from fastapi import APIRouter
from app.models.schemas import SummaryRequest
from app.services.rag import run_summary
router = APIRouter(tags=['summary'])
@router.post('/summary/')
async def summary(req: SummaryRequest):
    persona = {}
    ans = await run_summary(req.chapter, req.subject, req.level, req.board, req.summary_type, req.persona_id, persona)
    return {'summary': ans, 'persona': persona}
