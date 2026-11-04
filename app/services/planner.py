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


async def topic_breakdown(topic,subject,level,board,minutes):
    """Name what to actually study inside a topic, grounded in the course material."""
    from app.services.rag import retrieve,build_context
    from app.services.llm_client import generate_text,GenerationUnavailable
    try:
        hits=await retrieve(topic,subject,level,board,['textbook','syllabus'])
        hits=[h for h in hits if h['score']>=settings.MIN_SIMILARITY]
        if not hits:
            return {'subtopics':[],'reason':'No course material matched this topic.'}
        raw=await generate_text(settings.LLM_SMALL_MODEL,
                                study_plan_prompt(build_context(hits),topic,board,level,subject,minutes),
                                token_budget=700)
        clean=re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip())
        match=re.search(r'\{.*\}',clean,re.S)
        data=json.loads(match.group(0) if match else clean)
        subtopics=[str(s).strip() for s in data.get('subtopics',[]) if str(s).strip()]
        return {'subtopics':subtopics[:4],'focus':data.get('focus',''),'practice':data.get('practice',''),
                'checkpoint':data.get('checkpoint',''),
                'sources':[{'source':h['source'],'page':h.get('page')} for h in hits[:3]]}
    except (GenerationUnavailable,ValueError,TypeError,KeyError,AttributeError,json.JSONDecodeError):
        # The schedule is still useful without enrichment, so never fail the plan.
        return {'subtopics':[],'reason':'Study detail is unavailable; the schedule below still applies.'}


async def enrich_plan(plan,subject,level,board):
    """Attach real study detail per topic and spread subtopics across its sessions."""
    topics=list(plan['allocations'].keys())
    if not topics:return plan
    minutes=plan.get('daily_minutes',60)
    breakdowns=await asyncio.gather(*[topic_breakdown(t,subject,level,board,minutes) for t in topics])
    detail=dict(zip(topics,breakdowns))
    for day in plan['schedule']:
        for session in day['sessions']:
            info=detail.get(session['topic'],{})
            subtopics=info.get('subtopics') or []
            if subtopics:
                # Each pass over a topic advances through its subtopics.
                start=((session['pass_number']-1)*2)%len(subtopics)
                session['subtopics']=subtopics[start:start+2] or subtopics[:2]
                session['activity']=('Study: '+'; '.join(session['subtopics']) if session['pass_number']==1
                                     else 'Revise and self-test: '+'; '.join(session['subtopics']))
            elif info.get('reason'):
                session['detail_note']=info['reason']
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
            subtopics=(detail.get(session['topic']) or {}).get('subtopics') or []
            if subtopics:
                start=((session['pass_number']-1)*2)%len(subtopics)
                session['subtopics']=subtopics[start:start+2] or subtopics[:2]
                session['activity']=('Study: '+'; '.join(session['subtopics']) if session['pass_number']==1
                                     else 'Revise and self-test: '+'; '.join(session['subtopics']))
    plan['topic_detail']=detail
    return plan
