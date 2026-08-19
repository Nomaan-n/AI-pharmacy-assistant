from app.safety import classify
def test_emergency_classification(): assert classify('I have trouble breathing')=='emergency'
def test_prescribing_classification(): assert classify('Can I increase my dose?')=='prescribing'
def test_information_classification(): assert classify('What is paracetamol?')=='information'
