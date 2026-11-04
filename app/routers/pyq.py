import asyncio
from fastapi import APIRouter
from app.models.schemas import PYQRequest
from app.services.pyq_analysis import analyze
router=APIRouter(tags=['pyq'])
@router.post('/pyq/')
async def pyq(req:PYQRequest):
    return await asyncio.to_thread(analyze,req.subject,req.level,req.board)
