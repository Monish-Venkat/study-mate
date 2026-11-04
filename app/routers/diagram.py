from fastapi import APIRouter, HTTPException
from app.models.schemas import DiagramRequest
from app.services.diagram import build_diagram

router = APIRouter(tags=['diagram'])


@router.post('/diagram/')
async def diagram(req: DiagramRequest):
    retrieval = {}
    try:
        result = await build_diagram(req.topic, req.subject, req.level, req.board,
                                     req.kind, chapter=req.chapter,
                                     retrieval_result=retrieval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {**result, 'retrieval': retrieval}
