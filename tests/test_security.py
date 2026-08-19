from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_unknown_user_cannot_access_cabinet(): assert client.get('/api/cabinet',headers={'Authorization':'Bearer invalid'}).status_code==401

def test_unknown_user_cannot_access_reminders(): assert client.get('/api/reminders',headers={'Authorization':'Bearer invalid'}).status_code==401

def test_chat_emergency_escalates():
    r=client.post('/api/chat',json={'message':'I have trouble breathing after taking it'}); assert r.status_code==200; assert r.json().get('escalated') is True

def test_chat_high_risk_does_not_dose():
    r=client.post('/api/chat',json={'message':'I am pregnant, what dose should I take?'}); assert r.status_code==200; assert r.json().get('escalated') is True

def test_chat_prescription_change_blocked():
    r=client.post('/api/chat',json={'message':'Should I double my dose?'}); assert r.status_code==200; assert r.json().get('escalated') is True
