from app.schemas import ChatRequest, ChatResponse


def test_chat_request_trims_whitespace():
    request = ChatRequest(message="  What is aspirin?  ")
    assert request.message == "What is aspirin?"


def test_chat_response_has_structured_fields():
    response = ChatResponse(answer="Use medicine information carefully.", safety_flags=[], sources=[])
    assert response.answer
    assert response.safety_flags == []
