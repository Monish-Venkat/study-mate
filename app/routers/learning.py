import asyncio
from fastapi import APIRouter,HTTPException
from app.models.schemas import CourseRequest,PlannerRequest,ScoreRequest
from app.services.memory import memory,course_scope
from app.services.planner import save_plan,current_plan
from app.services.syllabus import syllabus_topics
router=APIRouter(tags=['learning'])

@router.post('/planner/')
async def planner(req:PlannerRequest):
    if any(len(t)>200 or not t.strip() for t in req.topics):raise HTTPException(422,'Each topic must be 1–200 characters.')
    try:return await save_plan(req)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/profile/')
def profile(req:CourseRequest):
    scope=course_scope(req.subject,req.level,req.board)
    return {'profile':memory.profile(req.student_id,scope),'history':memory.recent(req.student_id,10,scope),
            'plan':current_plan(req.student_id,scope),'syllabus_topics':syllabus_topics(req.subject,req.level,req.board)}

@router.post('/scores/')
def score(req:ScoreRequest):
    if req.earned>req.possible:raise HTTPException(422,'Earned marks cannot exceed possible marks.')
    scope=course_scope(req.subject,req.level,req.board)
    profile=memory.profile(req.student_id,scope)
    percentage=round(req.earned/req.possible*100,2)
    profile.setdefault('scores',{})[req.topic]=percentage
    memory.put(req.student_id,'profile',profile,scope,True)
    memory.put(req.student_id,'score',{'subject':req.subject,'level':req.level,'board':req.board,'topic':req.topic,'percentage':percentage,'source':'self_reported'},scope)
    return {'percentage':percentage,'plan':current_plan(req.student_id,scope),'source':'self_reported'}

@router.post('/memory/clear')
def clear(req:CourseRequest):
    memory.forget(req.student_id)
    return {'deleted':True}
