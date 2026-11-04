import asyncio
import hmac
import json
import uuid
from collections import Counter,defaultdict
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,Header,HTTPException,Depends,Request,BackgroundTasks
from pydantic import BaseModel,Field,ConfigDict
from app.core.config import settings
from app.services.memory import memory
from app.services.syllabus import save_syllabus,syllabus_topics


def require_teacher(x_teacher_key:str=Header(default='')):
    if not settings.TEACHER_API_KEY:raise HTTPException(503,'Teacher tools require TEACHER_API_KEY in the backend environment.')
    if not hmac.compare_digest(x_teacher_key,settings.TEACHER_API_KEY):raise HTTPException(403,'Teacher access key is incorrect.')

router=APIRouter(prefix='/teacher',tags=['teacher'],dependencies=[Depends(require_teacher)])

class SyllabusRequest(BaseModel):
    subject:Literal['physics','chemistry','mathematics','biology']
    level:Literal['PUC1','PUC2']
    board:Literal['KA','CBSE']
    topics:list[str]=Field(min_length=1,max_length=100)

class QuestionRecord(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    subject:Literal['physics','chemistry','mathematics','biology']
    level:Literal['PUC1','PUC2']
    board:Literal['KA','CBSE']
    year:int=Field(ge=1990,le=2100)
    text:str=Field(min_length=15,max_length=4000)
    topic:str=Field(min_length=1,max_length=200)
    source:str=Field(min_length=1,max_length=200)
    marks:int=Field(ge=1,le=30)
    page:int|None=Field(default=None,ge=1)
    verified:bool=True

@router.get('/analytics')
def analytics():
    events=memory.aggregate()
    queries=Counter();confusion=Counter();personas=Counter();scores=defaultdict(list)
    for kind,event in events:
        key=f"{event['subject']} / {event['level']} / {event['board']} / {event['topic']}"
        if kind=='event':
            queries[key]+=1
            if event.get('clarification'):confusion[key]+=1
            if event.get('persona'):personas[event['persona']]+=1
        else:scores[key].append(event['percentage'])
    return {'queries':dict(queries),'confusion':dict(confusion),'persona_usage':dict(personas),
            'scores':{k:{'count':len(v),'mean':round(sum(v)/len(v),1),'below_50':sum(x<50 for x in v)} for k,v in scores.items()},
            'retention_days':settings.RETENTION_DAYS,'score_source':'self_reported',
            'syllabus_coverage':{f'{s}/{l}/{b}':{'topics':len(syllabus_topics(s,l,b)),
                'queried':sum(any(key==f'{s} / {l} / {b} / {topic}' for key in queries) for topic in syllabus_topics(s,l,b))}
                for s in settings.subjects_list() for l in ('PUC1','PUC2') for b in ('KA','CBSE') if syllabus_topics(s,l,b)}}

@router.post('/syllabus')
def syllabus(req:SyllabusRequest):
    if any(not t.strip() or len(t)>200 for t in req.topics):raise HTTPException(422,'Topic names must be 1–200 characters.')
    save_syllabus(req.subject,req.level,req.board,[t.strip() for t in req.topics])
    return {'saved':len(set(req.topics))}

@router.post('/questions')
def questions(records:list[QuestionRecord]):
    if not 1<=len(records)<=5000:raise HTTPException(422,'Import between 1 and 5000 reviewed questions.')
    path=Path(settings.DATA_DIR)/'pyq_questions.json'
    previous=json.loads(path.read_text()) if path.exists() else []
    combined={(r['source'],r['year'],r['text']):r for r in previous+[r.model_dump() for r in records]}
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(list(combined.values()),ensure_ascii=False),encoding='utf-8');temp.replace(path)
    return {'records':len(combined)}

_jobs={}
async def index_upload(key,path):
    try:
        from app.services.ingest import ingest_pdf
        result=await asyncio.to_thread(ingest_pdf,str(path))
        _jobs[key]={'status':'ready','result':result}
    except Exception:
        _jobs[key]={'status':'failed','error':'Indexing failed. Check the PDF text and embedding model, then upload again.'}

@router.post('/upload')
async def upload(request:Request,background:BackgroundTasks):
    form=await request.form()
    subject=str(form.get('subject',''));level=str(form.get('level',''));board=str(form.get('board',''))
    kind=str(form.get('kind','textbook'))
    if subject not in settings.subjects_list() or level not in ('PUC1','PUC2') or board not in ('KA','CBSE') or kind not in ('textbook','syllabus'):raise HTTPException(422,'Select a valid course and source type.')
    uploaded=form.get('file')
    if not hasattr(uploaded,'read'):raise HTTPException(422,'Choose a PDF.')
    content=await uploaded.read(20*1024*1024+1)
    if len(content)>20*1024*1024:raise HTTPException(413,'PDF must be under 20 MB.')
    if not content.startswith(b'%PDF-'):raise HTTPException(422,'File must be a PDF.')
    key=uuid.uuid4().hex
    root=Path(settings.SYLLABUS_DIR if kind=='syllabus' else settings.TEXTBOOKS_DIR)
    path=root/subject/('1st' if level=='PUC1' else '2nd')/board.lower()/f'{key}.pdf'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    _jobs[key]={'status':'processing'}
    background.add_task(index_upload,key,path)
    return {'job_id':key,'status':'processing'}

@router.get('/uploads/{job_id}')
def upload_status(job_id:str):
    if job_id not in _jobs:raise HTTPException(404,'Unknown upload job; the server may have restarted.')
    return _jobs[job_id]
