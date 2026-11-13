import asyncio
import json
import re
from datetime import date,timedelta
from app.core.config import settings
from app.core.prompts import study_plan_prompt
from app.services.memory import memory,course_scope


def allocate_plan(exam_date,topics,scores,daily_minutes,today=None):
    today=today or date.today()
    exam=date.fromisoformat(exam_date) if isinstance(exam_date,str) else exam_date
    days=(exam-today).days-1
    if days<1:raise ValueError('Choose an exam at least two days away; the day before the exam is kept free.')
    if days>365:raise ValueError('Choose an exam within the next year.')
    topics=list({t.strip().casefold():t.strip() for t in topics if t.strip()}.values())
    lookup={k.casefold():v for k,v in scores.items()}
    scores={topic:lookup[topic.casefold()] for topic in topics if topic.casefold() in lookup}
    if not topics:raise ValueError('Provide topics or add a syllabus first.')
    slots=max(1,daily_minutes//30)
    weights={t:1+(100-float(scores.get(t,50)))/25 for t in topics}
    allocations={t:0 for t in topics}
    schedule=[]
    # Cover every topic once, weakest first, then weighted fair allocation.
    initial=sorted(topics,key=lambda t:float(scores.get(t,50)))
    for day in range(days):
        sessions=[]
        for slot in range(slots):
            topic=initial.pop(0) if initial else max(topics,key=lambda t:weights[t]/(allocations[t]+1))
            allocations[topic]+=1
            sessions.append({'topic':topic,'minutes':daily_minutes//slots+(1 if slot<daily_minutes%slots else 0),
                             'pass_number':allocations[topic],
                             'activity':'Learn and practice' if allocations[topic]==1 else 'Recall, practice and review mistakes',
                             'score':scores.get(topic)})
        schedule.append({'date':(today+timedelta(days=day)).isoformat(),'sessions':sessions})
    return {'exam_date':exam.isoformat(),'free_day':(exam-timedelta(days=1)).isoformat(),'schedule':schedule,
            'uncovered_topics':initial,'allocations':allocations,'daily_minutes':daily_minutes,
            'warning':'Not enough time to cover every topic. Increase daily minutes or narrow the syllabus.' if initial else None}


def _page_runs(pages):
    """Collapse [36,37,38,41] into [(36,38),(41,41)] for readable references."""
    runs=[]
    for page in sorted(set(pages)):
        if runs and page==runs[-1][1]+1:
            runs[-1][1]=page
        else:
            runs.append([page,page])
    return [(a,b) for a,b in runs]


def describe_reading(refs):
    """Render [(source,page)] as 'kebo102.pdf pp. 6-8; kebo103.pdf p. 12'."""
    by_source={}
    for source,page in refs:
        by_source.setdefault(source or 'course material',[]).append(page)
    parts=[]
    for source,pages in by_source.items():
        runs=_page_runs(pages)
        spans=', '.join(str(a) if a==b else f'{a}-{b}' for a,b in runs)
        label='p.' if len(runs)==1 and runs[0][0]==runs[0][1] else 'pp.'
        parts.append(f'{source} {label} {spans}')
    return '; '.join(parts)


def reading_passes(hits,passes):
    """Split the pages covering a topic into one reading target per pass.

    This is the part of a session that has to work whether or not a language
    model is available: a student can be told which pages to read from
    retrieval alone. Pages are ordered so that successive passes move through
    the material rather than re-reading the same opening pages.
    """
    refs=[]
    seen=set()
    for hit in hits:
        page=hit.get('page')
        if page is None:continue
        key=(hit.get('source'),page)
        if key in seen:continue
        seen.add(key)
        refs.append(key)
    if not refs:return []
    refs.sort(key=lambda r:(r[0] or '',r[1]))
    size=max(1,-(-len(refs)//max(1,passes)))
    return [refs[i:i+size] for i in range(0,len(refs),size)]


async def topic_breakdown(topic,subject,level,board,minutes):
    """Name what to actually study inside a topic, grounded in the course material.

    Retrieval and generation are separated deliberately. Retrieval gives the
    pages that cover the topic and never needs a model; generation only names
    the subtopics. Previously a single try block wrapped both, so when the
    local model was unavailable the whole breakdown was discarded and every
    session degraded to "Learn and practice" against a bare chapter name.
    """
    from app.services.rag import retrieve,build_context
    from app.services.llm_client import generate_text,GenerationUnavailable

    try:
        hits=await retrieve(topic,subject,level,board,['textbook','syllabus'])
        hits=[h for h in hits if h['score']>=settings.MIN_SIMILARITY]
    except Exception:
        hits=[]
    if not hits:
        return {'subtopics':[],'sources':[],'reading':[],
                'reason':'No course material matched this topic. Check the subject and year, or index the chapter.'}

    detail={'subtopics':[],'sources':[{'source':h['source'],'page':h.get('page')} for h in hits[:4]],
            'reading':reading_passes(hits,4)}
    try:
        raw=await generate_text(settings.LLM_SMALL_MODEL,
                                study_plan_prompt(build_context(hits),topic,board,level,subject,minutes),
                                token_budget=700)
        clean=re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip())
        match=re.search(r'\{.*\}',clean,re.S)
        data=json.loads(match.group(0) if match else clean)
        subtopics=[str(s).strip() for s in data.get('subtopics',[]) if str(s).strip()]
        detail.update(subtopics=subtopics[:4],focus=data.get('focus',''),
                      practice=data.get('practice',''),checkpoint=data.get('checkpoint',''))
    except (GenerationUnavailable,ValueError,TypeError,KeyError,AttributeError,json.JSONDecodeError):
        # Named subtopics are an enhancement. The page references below are
        # what make the session specific, and they survive without a model.
        detail['reason']='Subtopic names need the local model; the reading targets below come from your textbook index.'
    return detail


def apply_detail(session,info):
    """Turn one scheduled slot into specific work: what to read, then what to do.

    Applied identically to a freshly generated plan and to one rebuilt from
    storage, so revisiting a plan shows the same sessions it was saved with.
    """
    if not info:return
    pass_number=session.get('pass_number',1)
    subtopics=info.get('subtopics') or []
    reading=info.get('reading') or []
    if subtopics:
        # Each pass over a topic advances through its subtopics.
        start=((pass_number-1)*2)%len(subtopics)
        session['subtopics']=subtopics[start:start+2] or subtopics[:2]
    if reading:
        # Successive passes move through the chapter instead of re-reading
        # the same opening pages.
        refs=[tuple(r) for r in reading[(pass_number-1)%len(reading)]]
        session['reading']=[{'source':s,'page':p} for s,p in refs]
        session['reference']=describe_reading(refs)
    # The activity says what to do; the reference says where. They are kept
    # apart so the client can lay them out rather than parse one sentence.
    if session.get('subtopics'):
        focus='; '.join(session['subtopics'])
        session['activity']=f'Study: {focus}' if pass_number==1 else f'Revise and self-test: {focus}'
    elif session.get('reference'):
        session['activity']=('Read the pages below, then write the key results out from memory'
                             if pass_number==1 else
                             'Re-read the pages below and answer on them without notes')
    if pass_number==1 and info.get('practice'):
        session['practice']=info['practice']
    if pass_number>1 and info.get('checkpoint'):
        session['checkpoint']=info['checkpoint']
    if info.get('reason') and not session.get('reference'):
        session['detail_note']=info['reason']


async def enrich_plan(plan,subject,level,board):
    """Attach real study detail per topic and spread it across that topic's sessions."""
    topics=list(plan['allocations'].keys())
    if not topics:return plan
    minutes=plan.get('daily_minutes',60)
    breakdowns=await asyncio.gather(*[topic_breakdown(t,subject,level,board,minutes) for t in topics])
    detail=dict(zip(topics,breakdowns))
    for day in plan['schedule']:
        for session in day['sessions']:
            apply_detail(session,detail.get(session['topic'],{}))
    plan['topic_detail']=detail
    return plan


async def save_plan(req):
    scope=course_scope(req.subject,req.level,req.board)
    profile=memory.profile(req.student_id,scope)
    topics=req.topics
    if not topics:
        from app.services.syllabus import syllabus_topics
        topics=syllabus_topics(req.subject,req.level,req.board)
    result=allocate_plan(req.exam_date,topics,profile['scores'],req.daily_minutes)
    result=await enrich_plan(result,req.subject,req.level,req.board)
    profile['exam_date']=str(req.exam_date)
    memory.put(req.student_id,'profile',profile,scope,True)
    memory.put(req.student_id,'plan_spec',{'exam_date':str(req.exam_date),'topics':topics,'daily_minutes':req.daily_minutes},scope,True)
    memory.put(req.student_id,'plan_detail',result.get('topic_detail',{}),scope,True)
    return result


def current_plan(student_id,scope):
    specs=memory.read(student_id,'plan_spec',scope)
    if not specs:return None
    try:
        plan=allocate_plan(**specs[-1],scores=memory.profile(student_id,scope)['scores'])
    except ValueError as exc:
        return {'expired':True,'message':str(exc)}
    # Reuse the stored breakdown so revisiting a plan costs no generation.
    saved=memory.read(student_id,'plan_detail',scope)
    detail=saved[-1] if saved else {}
    for day in plan['schedule']:
        for session in day['sessions']:
            apply_detail(session,detail.get(session['topic']) or {})
    plan['topic_detail']=detail
    return plan
