from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.schemas import PersonaRegisterRequest
from app.services.persona import register_video, process_video, PersonaError
from app.services.persona_store import persona_store

router = APIRouter(prefix='/personas', tags=['personas'])

@router.get('/')
def list_personas():
    return {'educators': persona_store().listing()}

@router.post('/', status_code=202)
async def register(req: PersonaRegisterRequest, background_tasks: BackgroundTasks):
    try:
        key, educator_id, video_id, process = register_video(req)
    except PersonaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if process:
        background_tasks.add_task(process_video, key, educator_id, video_id, req.language, req.transcript)
    return {'educator_id':educator_id, 'video_key':key, 'queued':process}
