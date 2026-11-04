import asyncio
import json
from datetime import date,timedelta
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.memory import memory,course_scope
from app.services.security import seal,unseal,identity
from app.services.planner import allocate_plan
from app.services.pyq_analysis import trend_report
from app.services.mock_engine import blueprint,validate_paper
from app.services import tutoring,rag

BASE={'student_id':'guest-one','subject':'physics','level':'PUC2','board':'KA'}

def test_encrypted_persistent_memory_isolation_and_retention():
    for i in range(14):memory.save('guest-one','user',f'private question {i}','course')
    assert len(memory.recent('guest-one',scope='course'))==10
    assert memory.recent('guest-two',scope='course')==[]
    assert memory.recent('guest-one',scope='another')==[]
    with memory.db() as db:
        raw=db.execute('SELECT value,owner FROM records LIMIT 1').fetchone()
        assert 'private question' not in raw['value'] and 'guest-one' not in raw['owner']
        db.execute('UPDATE records SET ts=0')
    assert memory.recent('guest-one',scope='course')==[]

def test_authenticated_encryption_tampering():
    ciphertext=seal({'private':'data'},'owner')
    assert unseal(ciphertext,'owner')=={'private':'data'}
    with pytest.raises(Exception):unseal(ciphertext,'other-owner')
    assert identity('one')!=identity('two')

def test_planner_weak_topic_weighting_and_free_day():
    today=date(2026,1,1)
    result=allocate_plan('2026-01-12',['weak','strong'],{'weak':0,'strong':100},60,today)
    assert result['allocations']['weak']>result['allocations']['strong']
    assert result['free_day']=='2026-01-11'
    assert all(day['date']<'2026-01-11' for day in result['schedule'])
    assert all(sum(s['minutes'] for s in day['sessions'])==60 for day in result['schedule'])
    with pytest.raises(ValueError):allocate_plan('2026-01-02',['topic'],{},60,today)

def test_planner_reports_impossible_coverage():
    result=allocate_plan('2026-01-03',['a','b','c'],{},30,date(2026,1,1))
    assert result['warning'] and len(result['uncovered_topics'])==2

def test_statistics_count_real_years_and_deduplicate():
    a={'source':'Paper A','year':2025,'text':'Calculate electric field strength','topic':'Electric field','marks':3,'verified':True}
    b={**a,'source':'Paper B','year':2026,'marks':5}
    report=trend_report([a,a,b],2026)
    assert report['question_count']==2
    assert report['missing_years']==[2022,2023,2024]
    assert report['topics'][0]['question_count']==2
    assert report['topics'][0]['known_marks']==8

@pytest.mark.parametrize('total',[10,11,70,100,200])
def test_blueprint_and_structure(total):
    slots=blueprint(total)
    assert sum(s['marks'] for s in slots)==total
    questions=[{**s,'text':f'Question {s["id"]}','answer':'Answer','topic':'Topic',**({'alternative':{'text':'Alternative','answer':'Answer'}} if s['internal_choice'] else {})} for s in slots]
    assert validate_paper(json.dumps({'questions':questions}),slots)==questions
    questions[-1]['marks']+=1
    with pytest.raises(ValueError):validate_paper(json.dumps({'questions':questions}),slots)

def test_score_recalculates_saved_plan():
    client=TestClient(app)
    plan=client.post('/planner/',json={**BASE,'exam_date':str(date.today()+timedelta(days=10)),'topics':['Waves','Light'],'daily_minutes':60})
    assert plan.status_code==200
    response=client.post('/scores/',json={**BASE,'topic':'Waves','earned':0,'possible':10})
    assert response.status_code==200
    assert response.json()['plan']['allocations']['Waves']>response.json()['plan']['allocations']['Light']
    assert client.post('/scores/',json={**BASE,'topic':'Waves','earned':11,'possible':10}).status_code==422
    assert client.post('/memory/clear',json=BASE).json()['deleted']
    assert client.post('/profile/',json=BASE).json()['plan'] is None

def test_adaptive_history_reaches_prompt(monkeypatch):
    scope=course_scope('physics','PUC2','KA')
    memory.save('guest-one','user','I am confused about waves.',scope)
    memory.put('guest-one','profile',{'language':'en','depth':'auto','scores':{'Waves':20}},scope,True)
    monkeypatch.setattr(rag,'retrieve',AsyncMock(return_value=[{'text':'A wave transfers energy','source':'Book','score':.9,'page':1}]))
    model=AsyncMock(return_value='Explanation [1].');monkeypatch.setattr(rag,'generate_text',model)
    result=TestClient(app).post('/ask/',json={**BASE,'question':'Explain again','chapter':'Waves'})
    assert result.json()['strategy']=='step_by_step'
    assert 'I am confused about waves.' in model.call_args.args[1]

def test_teacher_and_webhook_secrets(monkeypatch):
    monkeypatch.setattr(settings,'TEACHER_API_KEY','teacher-secret')
    client=TestClient(app)
    assert client.get('/teacher/analytics').status_code==403
    assert client.get('/teacher/analytics',headers={'X-Teacher-Key':'teacher-secret'}).status_code==200
    monkeypatch.setattr(settings,'TELEGRAM_BOT_TOKEN','token')
    monkeypatch.setattr(settings,'TELEGRAM_WEBHOOK_SECRET','webhook-secret')
    assert client.post('/webhook',json={'update_id':1}).status_code==403
    assert client.post('/webhook',json={'update_id':1},headers={'X-Telegram-Bot-Api-Secret-Token':'webhook-secret'}).status_code==200
    assert client.post('/webhook',json={'update_id':1},headers={'X-Telegram-Bot-Api-Secret-Token':'webhook-secret'}).status_code==200
    assert len(memory.read('telegram-worker','telegram_update','1'))==1

def test_speech_disabled_is_explicit(monkeypatch):
    monkeypatch.setattr(settings,'ENABLE_GTTS',False)
    response=TestClient(app).post('/voice/speak',json={'text':'Hello','language':'en'})
    assert response.status_code==503 and 'disabled' in response.json()['detail']

def test_mock_score_uses_saved_marks():
    scope=course_scope('physics','PUC2','KA');pid='a'*32
    memory.put('guest-one','mock',{'total_marks':5,'questions':[{'id':1,'marks':5,'topic':'Waves'}]},scope+':'+pid,True)
    client=TestClient(app)
    assert client.post('/mock-paper/score',json={**BASE,'paper_id':pid,'scores':[{'id':1,'earned':6}]}).status_code==422
    result=client.post('/mock-paper/score',json={**BASE,'paper_id':pid,'scores':[{'id':1,'earned':3}]})
    assert result.json()['topic_scores']['Waves']==60
