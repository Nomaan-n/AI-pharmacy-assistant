from fastapi.testclient import TestClient
from app.main import app
from app import main

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_empty_question_rejected():
    response = client.post('/api/chat', json={'question': ''})
    assert response.status_code == 422

def test_urgent_question(monkeypatch):
    async def fake_retrieve(_):
        return type('R', (), {'medication': {}, 'context': '', 'sources': [], 'grounded': False})()
    async def fake_answer(*args):
        return 'Seek urgent care.', 'test'
    monkeypatch.setattr(main.retriever, 'retrieve', fake_retrieve)
    monkeypatch.setattr(main, 'answer', fake_answer)
    response = client.post('/api/chat', json={'question': 'I have chest pain after taking ibuprofen'})
    assert response.status_code == 200
    assert response.json()['safety']['level'] == 'urgent'
    assert 'possible_urgent_symptoms' in response.json()['safety']['flags']

def test_chat_shape(monkeypatch):
    async def fake_retrieve(_):
        return type('R', (), {'medication': {'name':'ibuprofen','title':'Example label','label_set_id':'x'}, 'context':'label context', 'sources':[{'title':'DailyMed','url':'https://dailymed.nlm.nih.gov/','source_type':'DailyMed/NLM'}], 'grounded':True})()
    async def fake_answer(*args):
        return 'Grounded answer.', 'test'
    monkeypatch.setattr(main.retriever, 'retrieve', fake_retrieve)
    monkeypatch.setattr(main, 'answer', fake_answer)
    response = client.post('/api/chat', json={'question': 'What are side effects of ibuprofen?'})
    assert response.status_code == 200
    data = response.json()
    assert data['grounded'] is True
    assert data['medication']['name'] == 'ibuprofen'
    assert data['sources'][0]['source_type'] == 'DailyMed/NLM'
