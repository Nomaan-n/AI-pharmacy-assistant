from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get("/health"); assert r.status_code==200; assert r.json()["status"]=="healthy"

def test_auth_requires_delivery_not_exposed():
    r=client.post("/api/auth/request-otp",json={"identifier":"test@example.com"}); assert r.status_code==200; assert "development_code" not in r.json()

def test_cabinet_requires_auth():
    r=client.get("/api/cabinet"); assert r.status_code==401

def test_reminder_requires_auth():
    r=client.get("/api/reminders"); assert r.status_code==401

def test_verify_unknown_is_safe():
    r=client.post("/api/verify",params={"name":"definitely-not-a-real-medication-name-xyz"}); assert r.status_code==200; assert r.json()["status"] in {"not_verified","candidate_verified"}

def test_medicine_catalog_compatibility():
    r=client.get("/api/medicines"); assert r.status_code==200; assert r.json()["count"]>=1

def test_photo_endpoint_rejects_invalid_image():
    r=client.post("/api/identify/photo",files={"file":("x.txt",b"not-an-image","text/plain")}); assert r.status_code==400

def test_chat_safety_guardrail():
    r=client.post("/api/chat",json={"message":"Should I increase my dose?"}); assert r.status_code==200; assert r.json()["escalated"] is True
