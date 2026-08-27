from app.schemas import ChatRequest, ChatResponse, MedicationContext, Safety


def test_chat_request_trims_whitespace():
    request = ChatRequest(question="  What is aspirin?  ")
    assert request.question == "What is aspirin?"


def test_chat_response_has_structured_fields():
    response = ChatResponse(
        answer="Use medicine information carefully.",
        medication=MedicationContext(name="aspirin"),
        safety=Safety(level="normal", flags=[], disclaimer="Informational only."),
        sources=[],
        grounded=False,
        provider="test",
    )
    assert response.answer
    assert response.medication.name == "aspirin"
    assert response.safety.flags == []
    assert response.grounded is False
