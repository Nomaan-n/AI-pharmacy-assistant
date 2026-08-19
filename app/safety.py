EMERGENCY_TERMS=("trouble breathing","difficulty breathing","face swelling","tongue swelling","seizure","unconscious","overdose","poisoning","chest pain")
HIGH_RISK_TERMS=("pregnant","pregnancy","breastfeeding","infant","newborn","child","pediatric","suicide","self harm")
PRESCRIPTION_ACTIONS=("increase my dose","decrease my dose","change my dose","stop taking","start taking","replace my medicine","double my dose")

def classify(text):
    t=text.lower()
    if any(x in t for x in EMERGENCY_TERMS): return "emergency"
    if any(x in t for x in HIGH_RISK_TERMS): return "high_risk"
    if any(x in t for x in PRESCRIPTION_ACTIONS): return "prescription_change"
    return "information"

def response_for_classification(kind):
    if kind=="emergency": return "This may require urgent medical attention. Do not use this assistant to decide emergency treatment. Seek urgent medical care or your local emergency/poison service now."
    if kind=="high_risk": return "This question needs individualized professional assessment. I can provide source-backed medication information, but I will not provide patient-specific dosing or treatment instructions."
    if kind=="prescription_change": return "I cannot prescribe, start, stop, or change a medication or dose. A prescriber or pharmacist must make that decision using the patient's clinical information."
    return None
