import asyncio
from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import Response
from app.models.schemas import SpeechRequest
from app.services.voice import transcribe_audio,synthesize
router=APIRouter(prefix='/voice',tags=['voice'])

@router.post('/transcribe')
async def transcribe(request:Request):
    content=bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content)>10*1024*1024:raise HTTPException(413,'Audio must be 10 MB or smaller.')
    try:return await asyncio.to_thread(transcribe_audio,bytes(content))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/speak')
async def speak(req:SpeechRequest):
    return Response(await asyncio.to_thread(synthesize,req.text,req.language),media_type='audio/mpeg',headers={'Cache-Control':'no-store'})
