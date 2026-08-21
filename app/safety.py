import re

URGENT_PATTERNS = [
    r"chest pain", r"trouble breathing", r"difficulty breathing", r"severe allergic",
    r"swelling of (the )?(face|tongue|throat)", r"passed out", r"unconscious",
    r"seizure", r"overdose", r"poisoned", r"suicid", r"severe bleeding"
]

HIGH_RISK_PATTERNS = [
    r"pregnan", r"breastfeed", r"child", r"infant", r"kidney", r"liver",
    r"blood thinner", r"warfarin", r"allergy", r"interactions?", r"drug interaction",
    r"stop taking", r"double (the )?dose", r"missed dose", r"dose for"
]

PRESCRIPTION_ACTION_PATTERNS = [
    r"should i start", r"should i stop", r"can i stop", r"change my dose",
    r"increase my dose", r"decrease my dose", r"what dose should i take"
]

def assess(question: str) -> tuple[str, list[str]]:
    q = question.lower()
    flags: list[str] = []
    if any(re.search(pattern, q) for pattern in URGENT_PATTERNS):
        flags.append("possible_urgent_symptoms")
        return "urgent", flags
    if any(re.search(pattern, q) for pattern in HIGH_RISK_PATTERNS):
        flags.append("higher_risk_context")
    if any(re.search(pattern, q) for pattern in PRESCRIPTION_ACTION_PATTERNS):
        flags.append("treatment_change_request")
    return ("caution" if flags else "informational"), flags

DISCLAIMER = (
    "This tool provides general medication information, not diagnosis or individualized treatment. "
    "Do not start, stop, or change prescription treatment based only on this response."
)

URGENT_DISCLAIMER = (
    "The question may involve a potentially urgent situation. Do not rely on this app for emergency care; "
    "seek urgent medical attention or contact local emergency services when appropriate."
)
