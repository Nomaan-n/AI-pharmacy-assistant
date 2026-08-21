from app.safety import assess

def test_urgent_symptom_is_flagged():
    level, flags = assess('I have trouble breathing after taking a medicine')
    assert level == 'urgent'
    assert 'possible_urgent_symptoms' in flags

def test_treatment_change_is_flagged():
    level, flags = assess('Should I stop taking my prescription?')
    assert level == 'caution'
    assert 'treatment_change_request' in flags

def test_simple_question_is_informational():
    level, flags = assess('What is ibuprofen used for?')
    assert level == 'informational'
    assert flags == []
