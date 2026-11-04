"""Telegram command dispatch. Network delivery only follows authenticated incoming updates."""
import asyncio
import json
import httpx
from app.core.config import settings
from app.models.schemas import AskRequest,MockRequest,PlannerRequest,ScoreRequest,PersonaRegisterRequest
from app.services.memory import memory
from app.services.tutoring import answer
from app.services.persona import register_video,process_video
from app.services.persona_store import persona_store
from app.services.mock_engine import generate_mock
from app.services.pyq_analysis import analyze
from app.services.planner import save_plan
from app.services.voice import transcribe_audio,synthesize

HELP='''StudyMate commands:
/course physics PUC2 KA (also chemistry, mathematics, biology; PUC1; CBSE)
/ask your question
/rev chapter topic
/pyq
/mock 70
/planner YYYY-MM-DD | daily minutes | topic one; topic two
/score topic | earned | possible
/persona list, /persona off, /persona EDUCATOR_ID
/persona register VIDEO_URL Educator name
/voice on or /voice off
/teacher
/forget
Voice notes are transcribed locally (first two minutes).'''

async def api(method,payload=None,files=None):
    async with httpx.AsyncClient(timeout=40) as client:
        response=await client.post(f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}',
                                  data=payload if files else None,json=None if files else payload,files=files)
        response.raise_for_status()
        data=response.json()
        if not data.get('ok'):raise RuntimeError('Telegram request failed')
        return data['result']

async def dispatch(text,student_id):
    profile=memory.profile(student_id,'telegram')
    course={k:profile.get(k,default) for k,default in [('subject','physics'),('level','PUC2'),('board','KA')]}
    base={'student_id':student_id,**course,'persona_id':profile.get('persona_id')}
    command,_,argument=text.strip().partition(' ')
    command=command.split('@')[0].lower()
    if command in ('/start','/help'):return HELP
    if command=='/course':
        values=argument.split()
        if len(values)!=3:return 'Use /course physics PUC2 KA'
        AskRequest(student_id=student_id,subject=values[0],level=values[1],board=values[2],question='validate')
        profile.update(subject=values[0],level=values[1],board=values[2],persona_id=None)
        memory.put(student_id,'profile',profile,'telegram',True)
        return 'Course updated.'
    if command=='/forget':memory.forget(student_id);return 'Your stored dialogue, preferences, scores and plans were deleted.'
    if command=='/teacher':return settings.PUBLIC_APP_URL.rstrip('/')+'/teacher'
    if command=='/voice':
        if argument not in ('on','off'):return 'Use /voice on or /voice off.'
        if argument=='on' and not settings.ENABLE_GTTS:return 'Voice output requires ENABLE_GTTS=true on the server. gTTS sends response text to Google.'
        profile['voice']=argument=='on';memory.put(student_id,'profile',profile,'telegram',True)
        return 'Voice preference saved.'
    if command=='/persona':
        if argument=='list':return '\n'.join(f"{e['id']}: {e['name']} ({e['subject']}; {'ready' if e['ready'] else 'not ready'})" for e in persona_store().listing()) or 'No educators registered.'
        if argument.startswith('register '):
            parts=argument.split(' ',2)
            if len(parts)<3:return 'Use /persona register VIDEO_URL Educator name'
            req=PersonaRegisterRequest(name=parts[2],subject=course['subject'],url=parts[1])
            key,eid,vid,process=register_video(req)
            if process:await process_video(key,eid,vid,'en',None)
            e=persona_store().get(eid)
            return f"Educator {eid}: "+ ('ready' if e['ready'] else 'not ready. Check import details in the web app.')
        if argument!='off':
            e=persona_store().get(argument)
            if not e or not e['ready'] or e['subject']!=course['subject']:return 'Choose a ready educator for your course using /persona list.'
        profile['persona_id']=None if argument=='off' else argument
        memory.put(student_id,'profile',profile,'telegram',True);return 'Teaching style updated.'
    if command=='/pyq':return (await asyncio.to_thread(analyze,**course))['analysis']
    if command=='/mock':return (await generate_mock(MockRequest(**base,total_marks=int(argument or 70))))['mock_paper']
    if command=='/planner':
        parts=[p.strip() for p in argument.split('|')]
        if len(parts)!=3:return 'Use /planner YYYY-MM-DD | daily minutes | topic one; topic two'
        return json.dumps(await save_plan(PlannerRequest(**base,exam_date=parts[0],daily_minutes=int(parts[1]),topics=[x.strip() for x in parts[2].split(';') if x.strip()])),ensure_ascii=False)
    if command=='/score':
        from app.routers.learning import score
        parts=[p.strip() for p in argument.split('|')]
        if len(parts)!=3:return 'Use /score topic | earned | possible'
        data=score(ScoreRequest(**base,topic=parts[0],earned=float(parts[1]),possible=float(parts[2])))
        return f"Self-reported score saved: {data['percentage']}%. Your saved plan has been recalculated."
    if command=='/rev':
        from app.services.rag import run_summary
        return await run_summary(argument,**course,summary_type='bullet_points',persona_id=profile.get('persona_id'))
    question=argument if command=='/ask' else text
    return (await answer(AskRequest(**base,question=question,language=profile.get('language','en'))))['answer']

async def handle_update(update):
    message=update.get('message') or {}
    chat=message.get('chat',{}).get('id');sender=message.get('from',{}).get('id')
    if chat is None or sender is None:return
    student_id=f'telegram:{chat}:{sender}'
    text=message.get('text','')
    try:
        if message.get('voice'):
            if message['voice'].get('file_size',0)>10*1024*1024:raise ValueError('Voice file exceeds 10 MB.')
            info=await api('getFile',{'file_id':message['voice']['file_id']})
            path=info.get('file_path','')
            if not path or '..' in path or path.startswith('/'):raise ValueError('Invalid voice file path.')
            content=bytearray()
            async with httpx.AsyncClient(timeout=40) as client:
                async with client.stream('GET',f'https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{path}') as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content)>10*1024*1024:raise ValueError('Voice file exceeds 10 MB.')
            transcript=await asyncio.to_thread(transcribe_audio,bytes(content))
            text=transcript['text']
            profile=memory.profile(student_id,'telegram')
            if transcript['language'] in ('en','hi','kn','ta','te','ml','mr','bn'):
                profile['language']=transcript['language'];memory.put(student_id,'profile',profile,'telegram',True)
        if not text:return
        result=await dispatch(text,student_id)
    except Exception as exc:
        from app.services.llm_client import GenerationUnavailable
        result=str(exc) if isinstance(exc,GenerationUnavailable) else 'This request could not be completed. Check the command format and service configuration. Use /help.'
    for start in range(0,len(result),3500):await api('sendMessage',{'chat_id':chat,'text':result[start:start+3500]})
    profile=memory.profile(student_id,'telegram')
    if profile.get('voice') and settings.ENABLE_GTTS:
        try:
            audio=await asyncio.to_thread(synthesize,result[:5000],profile.get('language','en'))
            await api('sendVoice',{'chat_id':str(chat)},files={'voice':('answer.mp3',audio,'audio/mpeg')})
        except Exception:await api('sendMessage',{'chat_id':chat,'text':'Audio output is unavailable; the text answer is above.'})
