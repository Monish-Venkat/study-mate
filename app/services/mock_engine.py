"""Structured mock generation with deterministic blueprint and validated totals."""
import json
import re
import uuid
from app.services.rag import retrieve,build_context
from app.services.llm_client import generate_text,GenerationUnavailable
from app.core.config import settings
from app.services.memory import memory,course_scope

def blueprint(total):
    if not 10 <= total <= 200:
        raise ValueError('Total marks must be between 10 and 200')
    slots=[{'marks':2,'bloom':'understand','internal_choice':False},
           {'marks':3,'bloom':'apply','internal_choice':False},
           {'marks':5,'bloom':'evaluate','internal_choice':True}]
    remaining=total-10
    while remaining:
        marks=min(5,remaining)
        slots.append({'marks':marks,'bloom':'analyze' if marks>=3 else 'remember','internal_choice':False})
        remaining-=marks
    slots.sort(key=lambda x:x['marks'])
    return [{'id':i+1,**slot} for i,slot in enumerate(slots)]


def validate_paper(raw,slots):
    data=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()))
    questions=data.get('questions')
    if not isinstance(questions,list) or len(questions)!=len(slots):raise ValueError('Wrong question count')
    seen=set()
    for q,slot in zip(questions,slots):
        if any(q.get(key)!=slot[key] for key in ('id','marks','bloom')):raise ValueError('Blueprint mismatch')
        for key in ('text','answer','topic'):
            if not isinstance(q.get(key),str) or not 1<=len(q[key].strip())<=5000:raise ValueError('Missing question fields')
        normalized=' '.join(q['text'].lower().split())
        if normalized in seen:raise ValueError('Duplicate question')
        seen.add(normalized)
        alternative=q.get('alternative')
        if slot['internal_choice']:
            if not isinstance(alternative,dict) or not all(isinstance(alternative.get(k),str) and 1<=len(alternative[k].strip())<=5000 for k in ('text','answer')):raise ValueError('Missing internal choice')
        elif alternative:raise ValueError('Unexpected alternative')
    return questions

# Extraction artefacts and generic words that match title pages and prefaces
# rather than course content.
_SEED_NOISE=set('indd mention point expression part parts chapter chapters page pages book books textbook edition preface contents'.split())

def exam_topics(subject,level,board):
    """Real topics to retrieve against; the bare subject name only matches front matter."""
    from app.services.syllabus import syllabus_topics
    topics=list(syllabus_topics(subject,level,board))
    # A short teacher syllabus alone retrieves too narrow a context to support a
    # full paper, so top it up with the recurring exam topics.
    if len(topics)<8:
        from app.services.pyq_analysis import question_records,trend_report
        records,_=question_records(subject,level,board)
        known={t.lower() for t in topics}
        for entry in trend_report(records)['topics']:
            topic=entry['topic']
            # Drop the subject name itself: it is what makes title pages rank first.
            if len(topic)<4 or topic in _SEED_NOISE or topic.lower()==subject.lower():
                continue
            if topic.lower() not in known:
                topics.append(topic)
                known.add(topic.lower())
    return topics[:12]

async def generate_mock(req):
    topics=exam_topics(req.subject,req.level,req.board)
    # A 15-question paper needs broader coverage than the default top-k.
    hits=await retrieve(', '.join(topics) or req.subject,req.subject,req.level,req.board,
                        ['textbook','syllabus'],top_k=max(settings.TOP_K,12))
    hits=[h for h in hits if h['score']>=settings.MIN_SIMILARITY]
    if not hits:return {'mock_paper':'No supporting course material found. Build the index first.','total_marks':req.total_marks,'validated':False}
    slots=blueprint(req.total_marks)
    prompt=('Use only COURSE CONTEXT. Return ONLY JSON {"questions":[...]}. Each question requires id, marks, bloom, text, answer, topic. '
            'Copy the blueprint id/marks/bloom exactly. For internal_choice=true add alternative:{text,answer}, at the same marks and Bloom level. '
            'Do not repeat questions. Use distinct topics supported by context. This is a practice blueprint, not a verified official board format.\n'
            +'BLUEPRINT:\n'+json.dumps(slots)+'\nCOURSE CONTEXT:\n'+build_context(hits))
    for attempt in range(2):
        raw=await generate_text(settings.LLM_MOCK_MODEL,prompt,token_budget=8192)
        try:
            questions=validate_paper(raw,slots)
            break
        except (ValueError,TypeError,KeyError):
            if attempt:raise GenerationUnavailable('The model could not produce a valid paper after two attempts. Try fewer marks or a different topic.')
            prompt+='\nYour previous response was invalid. Return the exact blueprint as valid JSON with every required field.'
    paper_id=uuid.uuid4().hex
    paper={'id':paper_id,'questions':questions,'total_marks':sum(q['marks'] for q in questions),'validated':True,
           'blueprint':'StudyMate practice format','sources':[{'source':h['source'],'page':h.get('page')} for h in hits]}
    scope=course_scope(req.subject,req.level,req.board)
    memory.put(req.student_id,'mock',paper,scope+':'+paper_id,True)
    lines=[f'## Practice paper ({paper["total_marks"]} marks)','Totals, question structure and internal choices were checked. Academic quality still needs review.']
    for q in questions:
        lines.append(f"### {q['id']}. {q['topic']} ({q['marks']} marks; {q['bloom']})\n{q['text']}")
        if q.get('alternative'):lines.append('**OR**\n'+q['alternative']['text'])
    lines.append('## Answer guide')
    for q in questions:
        lines.append(f"**{q['id']}.** {q['answer']}"+ ('\nAlternative: '+q['alternative']['answer'] if q.get('alternative') else ''))
    return {'mock_paper':'\n\n'.join(lines),'paper':paper,'total_marks':paper['total_marks'],'validated':True}
