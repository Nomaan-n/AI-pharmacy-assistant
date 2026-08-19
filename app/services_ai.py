from .services_medication import rxnorm_search, fda_label

SAFETY="Medication information is educational. The assistant does not diagnose, prescribe, change doses, or confirm that a medicine is appropriate for a specific patient."

def grounded_chat(message, medication=None):
    msg=message.strip()
    if not msg: return {"answer":"Please provide a medication or question.","sources":[],"safety":SAFETY}
    emergency_terms=["trouble breathing","difficulty breathing","swelling of face","severe allergic","unconscious","seizure","overdose","poisoning"]
    if any(x in msg.lower() for x in emergency_terms):
        return {"answer":"This may be an emergency. Do not use an AI assistant to decide what to do. Seek urgent medical care or contact your local emergency service/poison service now.","sources":[],"safety":SAFETY,"escalated":True}
    if any(x in msg.lower() for x in ["increase my dose","decrease my dose","stop taking","start taking","change my prescription"]):
        return {"answer":"I cannot prescribe, stop, start, or change a medication or dose. A prescriber or pharmacist must make that decision using your clinical details.","sources":[],"safety":SAFETY,"escalated":True}
    terms=[x for x in (medication or "").split(",") if x.strip()]
    sources=[]; evidence=[]
    for term in terms[:3]:
        matches=rxnorm_search(term.strip())
        if matches:
            evidence.append(matches[0]); sources.append("NIH RxNorm")
            label=fda_label(matches[0]["name"])
            if label: evidence.append(label); sources.append("U.S. FDA openFDA")
    if evidence:
        answer=("I can explain verified medication evidence, but I won't invent clinical facts. The medication concepts I found are: "+", ".join(x.get("name",x.get("source","evidence")) for x in evidence[:4])+". Use the cited authoritative data for medication facts and ask a pharmacist/clinician for patient-specific advice.")
    else:
        answer=("I could not verify a medication concept from the connected authoritative sources. I won't guess from memory. Check the original package or prescription and consult a pharmacist.")
    return {"answer":answer,"evidence":evidence[:6],"sources":sorted(set(sources)),"safety":SAFETY}
