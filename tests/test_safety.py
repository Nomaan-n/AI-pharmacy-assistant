from app.safety import assess


def test_urgent_question_is_blocked():
    level, flags = assess("I have severe chest pain and difficulty breathing. What medicine should I take?")
    assert level == "urgent"
    assert "possible_urgent_symptoms" in flags


def test_treatment_change_is_flagged():
    level, flags = assess("Should I stop taking my prescribed blood thinner?")
    assert level == "caution"
    assert "treatment_change_request" in flags


def test_information_question_is_informational():
    level, flags = assess("What is amoxicillin used for?")
    assert level == "informational"
    assert flags == []
