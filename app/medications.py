from typing import Any

MEDICATIONS: dict[str, dict[str, Any]] = {
    "paracetamol": {
        "generic_name": "Paracetamol (acetaminophen)",
        "class": "Analgesic / antipyretic",
        "uses": ["Relief of mild to moderate pain", "Reduction of fever"],
        "common_side_effects": ["Nausea", "Skin rash"],
        "warnings": ["Do not exceed the labeled dose.", "Excessive use can cause serious liver injury."],
        "source": "U.S. FDA Drug Safety Communication and approved labeling resources",
        "source_url": "https://www.fda.gov/drugs/postmarket-drug-safety-information-patients-and-providers",
    },
    "ibuprofen": {
        "generic_name": "Ibuprofen",
        "class": "Nonsteroidal anti-inflammatory drug (NSAID)",
        "uses": ["Relief of pain", "Reduction of fever", "Reduction of inflammation"],
        "common_side_effects": ["Stomach upset", "Heartburn", "Nausea"],
        "warnings": ["NSAIDs can cause serious gastrointestinal bleeding and cardiovascular risks.", "Use requires extra caution in some kidney, heart, pregnancy, and ulcer-related situations."],
        "source": "U.S. FDA NSAID safety information",
        "source_url": "https://www.fda.gov/drugs/postmarket-drug-safety-information-patients-and-providers/fda-strengthens-warning-heart-attack-and-stroke-risk-non-steroidal-anti-inflammatory-drugs",
    },
    "cetirizine": {
        "generic_name": "Cetirizine",
        "class": "Second-generation antihistamine",
        "uses": ["Relief of allergy symptoms", "Relief of hives"],
        "common_side_effects": ["Drowsiness", "Fatigue", "Dry mouth"],
        "warnings": ["May cause drowsiness in some people.", "Follow the product label and ask a clinician or pharmacist when other medicines or health conditions are involved."],
        "source": "DailyMed labeling resources",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/",
    },
}


def normalize_query(value: str) -> str:
    return " ".join(value.lower().strip().split())


def find_medication(query: str) -> dict[str, Any] | None:
    normalized = normalize_query(query)
    for key, medication in MEDICATIONS.items():
        if key in normalized or medication["generic_name"].lower() in normalized:
            return {"key": key, **medication}
    return None
