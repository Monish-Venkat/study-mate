import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import rag, llm_client, ingest
from app.services.faiss_store import FAISSStore

client = TestClient(app)
BASE = {'student_id':'anonymous-test','subject':'physics','level':'PUC2','board':'KA'}

def test_health_and_validation():
    assert client.get('/health').status_code == 200
    assert client.post('/ask/', json={**BASE,'question':'   '}).status_code == 422
    assert client.post('/mock-paper/', json={**BASE,'total_marks':0}).status_code == 422
    assert client.post('/ask/', json={**BASE,'subject':'invalid','question':'Why?'}).status_code == 422

@pytest.mark.parametrize('path,extra,key', [('ask',{'question':'Why?'},'answer'),('socratic',{'question':'Why?'},'answer'),('summary',{'chapter':'Waves'},'summary')])
def test_empty_retrieval_abstains_without_model(monkeypatch,path,extra,key):
    monkeypatch.setattr(rag,'retrieve',AsyncMock(return_value=[]))
    generator = AsyncMock()
    monkeypatch.setattr(rag,'generate_text',generator)
    response = client.post(f'/{path}/',json={**BASE,**extra})
    assert response.status_code == 200
    assert 'could not find supporting passages' in response.json()[key]
    generator.assert_not_called()

def test_filtering_before_top_k_and_reload(tmp_path):
    store = FAISSStore(str(tmp_path),dim=2)
    store.add([[1,0],[.9,.1],[.8,.2]],[{'subject':'chemistry'},{'subject':'physics'},{'subject':'physics'}])
    hits = FAISSStore(str(tmp_path),dim=2).search([1,0],1,{'subject':['physics']})
    assert len(hits)==1 and hits[0]['subject']=='physics'
    assert hits[0]['score']==pytest.approx(.9)

def test_metadata_and_chunk_validation():
    assert ingest.infer_subject_level(Path('data/question_papers/puc-1-mqp-physics-2024.pdf'))==('physics','1st','ka')
    assert ingest.infer_subject_level(Path('data/textbooks/mathematics/1st/kech201.pdf'))==('chemistry','1st','ka')
    with pytest.raises(ValueError): ingest.chunk_text('abc',3,3)
    assert ingest.chunk_text('abcdef',4,1)==['abcd','def']

def test_weak_evidence_and_citations(monkeypatch):
    hit={'score':.1,'text':'A wave transfers energy.','source':'Physics.pdf','page':3}
    monkeypatch.setattr(rag,'retrieve',AsyncMock(return_value=[hit]))
    generator=AsyncMock(return_value='A wave transfers energy [1].')
    monkeypatch.setattr(rag,'generate_text',generator)
    asyncio.run(rag.run_ask('Waves','physics','PUC2','KA'))
    generator.assert_not_called()
    hit['score']=.8
    answer=asyncio.run(rag.run_ask('Waves','physics','PUC2','KA'))
    assert '[1] Physics.pdf | page 3' in answer

def test_model_failure_is_503(monkeypatch):
    monkeypatch.setattr(rag,'retrieve',AsyncMock(return_value=[{'score':.8,'text':'Wave','source':'x','page':1}]))
    monkeypatch.setattr(rag,'generate_text',AsyncMock(side_effect=llm_client.GenerationUnavailable('Start Ollama')))
    response=client.post('/ask/',json={**BASE,'question':'Waves'})
    assert response.status_code==503
    assert response.json()['detail']=='Start Ollama'

def test_ollama_fallback_and_model_selection(monkeypatch):
    calls=[]
    def handler(request):
        import json
        calls.append((request.url.path,json.loads(request.content)))
        if request.url.path=='/api/chat': return httpx.Response(404)
        return httpx.Response(200,json={'choices':[{'message':{'content':'Grounded answer'}}]})
    original=httpx.AsyncClient
    monkeypatch.setattr(llm_client.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    assert asyncio.run(llm_client.generate_text('chosen-model','context'))=='Grounded answer'
    assert [c[0] for c in calls]==['/api/chat','/v1/chat/completions']
    assert all(c[1]['model']=='chosen-model' for c in calls)
