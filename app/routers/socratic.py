from fastapi import APIRouter
from app.models.schemas import SocraticRequest
from app.services.tutoring import answer
router=APIRouter(tags=['socratic'])
@router.post('/socratic/')
async def socratic(req:SocraticRequest):
    return {**await answer(req,guided=True),'mode':'socratic'}
