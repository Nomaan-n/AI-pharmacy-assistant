import re

URGENT_PATTERNS = [
    r"chest pain", r"difficulty breathing", r"can't breathe", r"cannot breathe",
    r"severe allergic", r"anaphylaxis", r"overdose", r"took too much",
    r"poison", r"suicid", r"unconscious", r"seizure", r"stroke",
]

HIGH_RISK_PATTERNS = [
    r"pregnan", r"child", r"infant", r"baby", r"kidney", r"liver",
    r"blood thinner", r"warfarin", r"bleeding", r"drug interaction",
    r"stop taking", r"start taking", r"dose", r"dosage",
]


def safety_flags(text: str) -> dict[str, bool]:
    lowered = text.lower()
    urgent = any(re.search(pattern, lowered) for pattern in URGENT_PATTERNS)
    high_risk = any(re.search(pattern, lowered) for pattern in HIGH_RISK_PATTERNS)
    return {"urgent": urgent, "high_risk": high_risk}


def safety_message(flags: dict[str, bool]) -> str | None:
    if flags["urgent"]:
        return "This may describe an urgent medical situation. Seek immediate medical care or contact your local emergency service rather than relying on this assistant."
    if flags["high_risk"]:
        return "This question involves a situation where individualized advice may matter. A pharmacist or clinician should review the specific medicine, dose, medical history, and other medicines before you act on the information."
    return None
