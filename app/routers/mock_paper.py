from collections import Counter

from fastapi import APIRouter, Query
from app.models.schemas import MockRequest
from app.services.mock_engine import generate_mock, blueprint
router=APIRouter(tags=['mock-paper'])
@router.post('/mock-paper/')
async def mock_paper(req:MockRequest):
    return await generate_mock(req)


@router.get('/mock-paper/blueprint')
def paper_blueprint(total_marks:int=Query(70,ge=10,le=200)):
    """The question structure a given mark total produces.

    Served rather than recomputed in the client so there is one definition of
    the blueprint. A preview that drifted from what the generator actually
    builds would be worse than showing nothing, since the whole point is to
    tell a student what they are about to get before they wait for it.
    """
    slots=blueprint(total_marks)
    counts=Counter(slot['marks'] for slot in slots)
    return {
        'total_marks':sum(slot['marks'] for slot in slots),
        'questions':len(slots),
        'internal_choice':sum(1 for slot in slots if slot['internal_choice']),
        'by_marks':[{'marks':marks,'count':count} for marks,count in sorted(counts.items())],
        'bloom':[{'level':level,'count':count} for level,count in
                 Counter(slot['bloom'] for slot in slots).most_common()],
    }

from pydantic import BaseModel,Field
from fastapi import HTTPException
from app.models.schemas import CourseRequest
from app.services.memory import memory,course_scope
from app.services.planner import current_plan

class QuestionScore(BaseModel):
    id:int=Field(ge=1)
    earned:float=Field(ge=0,le=200)
class MockScoreRequest(CourseRequest):
    paper_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    scores:list[QuestionScore]=Field(min_length=1,max_length=200)

@router.post('/mock-paper/score')
def score_paper(req:MockScoreRequest):
    scope=course_scope(req.subject,req.level,req.board)
    stored=memory.read(req.student_id,'mock',scope+':'+req.paper_id)
    if not stored:raise HTTPException(404,'This paper has expired or belongs to a different guest/course.')
    paper=stored[-1]
    answers={s.id:s.earned for s in req.scores}
    if len(answers)!=len(req.scores) or set(answers)!={q['id'] for q in paper['questions']}:raise HTTPException(422,'Provide exactly one score for every question.')
    topics={}
    for q in paper['questions']:
        if answers[q['id']]>q['marks']:raise HTTPException(422,f"Question {q['id']} exceeds its available marks.")
        entry=topics.setdefault(q['topic'],[0,0]);entry[0]+=answers[q['id']];entry[1]+=q['marks']
    profile=memory.profile(req.student_id,scope)
    for topic,(earned,possible) in topics.items():
        percentage=round(earned/possible*100,2)
        profile['scores'][topic]=percentage
        memory.put(req.student_id,'score',{'subject':req.subject,'level':req.level,'board':req.board,'topic':topic,'percentage':percentage,'source':'self_reported_mock'},scope+':'+req.paper_id+':'+topic,True)
    memory.put(req.student_id,'profile',profile,scope,True)
    return {'earned':sum(answers.values()),'possible':paper['total_marks'],'topic_scores':profile['scores'],'plan':current_plan(req.student_id,scope),'source':'self_reported_mock'}
