from fastapi import APIRouter
from app.models.schemas import AskRequest
from app.services.tutoring import answer
router=APIRouter(tags=['ask'])
@router.post('/ask/')
async def ask(req:AskRequest):
    return {**await answer(req),'student_id':req.student_id,'subject':req.subject,'board':req.board,'level':req.level}
