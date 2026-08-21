from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_returns_structured_grounding():
    response = client.post("/api/chat", json={"question": "What is cetirizine used for?"})
    assert response.status_code == 200
    data = response.json()
    assert data["medication"]["generic_name"] == "Cetirizine"
    assert data["source"]["name"]
    assert "answer" in data


def test_empty_question_rejected():
    response = client.post("/api/chat", json={"question": " "})
    assert response.status_code == 422


def test_urgent_question_gets_safety_flag():
    response = client.post("/api/chat", json={"question": "I took too much medicine and have chest pain"})
    assert response.status_code == 200
    assert response.json()["safety"]["urgent"] is True
