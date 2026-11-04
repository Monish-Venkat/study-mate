import asyncio
import json
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import PersonaRegisterRequest
from app.services import persona, persona_store as stores, rag
from app.services.persona_store import PersonaStore

PROFILE={key:'Short, clear explanations' for key in ['sentence_length','analogy_use','transitions','vocabulary','teaching_approach']}

@pytest.fixture
def store(tmp_path,monkeypatch):
    value=PersonaStore(tmp_path/'personas.db')
    monkeypatch.setattr(stores,'_store',value)
    monkeypatch.setattr(persona,'_import_lock',asyncio.Lock())
    return value

def request(**kwargs):
    return PersonaRegisterRequest(name='Test lecturer',subject='physics',url='https://youtu.be/abcdefghijk',**kwargs)

@pytest.mark.parametrize('url',['https://youtu.be/abcdefghijk?t=10','https://www.youtube.com/watch?v=abcdefghijk','https://youtube.com/shorts/abcdefghijk'])
def test_video_urls(url):
    assert persona.video_id_from_url(url)=='abcdefghijk'

@pytest.mark.parametrize('url',['https://evil.com/watch?v=abcdefghijk','https://youtube.com.evil.com/watch?v=abcdefghijk','file:///etc/passwd','https://youtube.com/playlist?list=abcdef','https://youtube.com/@teacher'])
def test_reject_non_video_urls(url):
    with pytest.raises(persona.PersonaError):persona.video_id_from_url(url)

class Tokens:
    def encode(self,text,**kwargs):return list(range(len(text.split())))
    def decode(self,ids,**kwargs):return ' '.join(str(i) for i in ids)

def test_token_windows_timestamps_and_sampling():
    chunks=persona.transcript_passages([{'text':'wave '*1400,'start':10,'end':180}],Tokens())
    assert len(chunks)==6
    assert len(chunks[0]['text'].split())==300
    assert chunks[0]['text'].split()[-50:]==chunks[1]['text'].split()[:50]
    assert chunks[0]['start']==10 and chunks[-1]['end']==180
    assert len(persona.sample_passages(list(range(100))))==30
    assert persona.sample_passages(list(range(100)))[-1]==99

async def imported(store,monkeypatch,count=6):
    monkeypatch.setattr(persona,'encode_passages',lambda segments:([{'text':f'example {i}','start':i*10,'end':i*10+10} for i in range(count)],[[1.,0.]]*count))
    monkeypatch.setattr(persona,'fingerprint',AsyncMock(return_value=PROFILE))
    req=request(transcript='lecture '*200)
    key,eid,vid,process=persona.register_video(req)
    assert process
    await persona.process_video(key,eid,vid,'en',req.transcript)
    return key,eid

def test_atomic_import_persistence_duplicates_and_style_gate(store,monkeypatch):
    key,eid=asyncio.run(imported(store,monkeypatch))
    assert PersonaStore(store.path).get(eid)['ready']
    assert len(store.passages(eid))==6
    assert persona.register_video(request())[3] is False
    monkeypatch.setattr(persona,'embed_text',lambda query:[1.,0.])
    prefix,result=asyncio.run(persona.style_context(eid,'physics','waves'))
    assert result['applied'] and len(result['sources'])==3
    assert 'Never add facts from these transcripts' in prefix
    assert result['sources'][1]['url'].endswith('&t=10')
    assert not asyncio.run(persona.style_context(eid,'biology','cells'))[1]['applied']
    monkeypatch.setattr(persona,'embed_text',lambda query:[0.,1.])
    assert not asyncio.run(persona.style_context(eid,'physics','unrelated'))[1]['applied']

def test_fewer_than_five_is_not_ready(store,monkeypatch):
    _,eid=asyncio.run(imported(store,monkeypatch,4))
    assert not store.get(eid)['ready']
    assert not asyncio.run(persona.style_context(eid,'physics','waves'))[1]['applied']

def test_failed_import_retry_and_restart_recovery(store,monkeypatch):
    monkeypatch.setattr(persona,'fetch_captions',lambda *args:(_ for _ in ()).throw(persona.PersonaError('No accessible captions')))
    key,eid,vid,_=persona.register_video(request())
    asyncio.run(persona.process_video(key,eid,vid,'en',None))
    assert store.get(eid)['videos'][0]['status']=='failed'
    assert not store.passages(eid)
    assert persona.register_video(request())[3] is True
    store.recover()
    assert 'restart' in store.get(eid)['videos'][0]['error']

def test_fingerprint_validates_and_caches_fields(monkeypatch):
    model=AsyncMock(return_value='```json\n'+json.dumps(PROFILE)+'\n```')
    monkeypatch.setattr(persona,'generate_text',model)
    assert asyncio.run(persona.fingerprint([{'text':'lecture'}]))==PROFILE
    model.return_value='not JSON'
    with pytest.raises(persona.PersonaError):asyncio.run(persona.fingerprint([{'text':'lecture'}]))

def test_api_registration_and_selected_persona_reaches_rag(store,monkeypatch):
    monkeypatch.setattr(persona,'encode_passages',lambda segments:([{'text':'lecture','start':None,'end':None}]*6,[[1.,0.]]*6))
    monkeypatch.setattr(persona,'fingerprint',AsyncMock(return_value=PROFILE))
    client=TestClient(app)
    response=client.post('/personas/',json=request(transcript='words '*200).model_dump())
    assert response.status_code==202
    eid=response.json()['educator_id']
    assert client.get('/personas/').json()['educators'][0]['ready']
    monkeypatch.setattr(persona,'embed_text',lambda query:[1.,0.])
    monkeypatch.setattr(rag,'retrieve',AsyncMock(return_value=[{'text':'Course facts','source':'Book','page':1,'score':.9}]))
    generator=AsyncMock(return_value='Course explanation [1].')
    monkeypatch.setattr(rag,'generate_text',generator)
    response=client.post('/ask/',json={'student_id':'guest','subject':'physics','question':'waves','persona_id':eid})
    assert response.status_code==200 and response.json()['persona']['applied']
    assert 'STYLE-ONLY' in generator.call_args.args[1]
    assert 'Course facts' in generator.call_args.args[1]
    monkeypatch.setattr(rag,'retrieve',AsyncMock(return_value=[]))
    response=client.post('/ask/',json={'student_id':'guest','subject':'physics','question':'waves','persona_id':eid})
    assert not response.json()['persona']['applied']
