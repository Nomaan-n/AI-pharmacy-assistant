EMERGENCY_TERMS=('trouble breathing','difficulty breathing','swelling of face','swelling of tongue','seizure','unconscious','overdose','poisoning','chest pain','stroke symptoms')
PRESCRIBING_TERMS=('increase my dose','decrease my dose','double my dose','stop taking','start taking','change my prescription','replace my medicine')
def classify(message:str):
 text=message.lower()
 if any(x in text for x in EMERGENCY_TERMS): return 'emergency'
 if any(x in text for x in PRESCRIBING_TERMS): return 'prescribing'
 return 'information'
