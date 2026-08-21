from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Pharmacy Assistant",
    version="1.1.0",
    description="Educational medication information API. Not a substitute for professional medical advice.",
)

# Demo API: keep CORS intentionally open for portfolio testing. A production deployment
# should restrict allow_origins to the application's known frontend domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

SAFETY_NOTE = (
    "This API provides general educational information only. It does not diagnose, "
    "prescribe, or replace advice from a qualified doctor or pharmacist."
)

MEDICINES = {
    "paracetamol": {
        "name": "Paracetamol",
        "generic_name": "Paracetamol (acetaminophen)",
        "drug_class": "Analgesic and antipyretic",
        "uses": ["Relief of mild to moderate pain", "Reduction of fever"],
        "common_side_effects": ["Usually well tolerated at recommended doses"],
        "warning": "Excessive dosing can cause serious liver injury. Check combination products to avoid accidentally taking more than the recommended amount.",
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "generic_name": "Ibuprofen",
        "drug_class": "Non-steroidal anti-inflammatory drug (NSAID)",
        "uses": ["Relief of pain", "Reduction of fever", "Reduction of inflammation"],
        "common_side_effects": ["Indigestion", "Stomach discomfort", "Nausea"],
        "warning": "NSAIDs may not be suitable for everyone, including some people with stomach ulcers, kidney disease, heart problems, or certain asthma histories.",
    },
    "cetirizine": {
        "name": "Cetirizine",
        "generic_name": "Cetirizine",
        "drug_class": "Second-generation antihistamine",
        "uses": ["Relief of allergy symptoms", "Relief of urticaria (hives) symptoms"],
        "common_side_effects": ["Drowsiness", "Headache", "Dry mouth"],
        "warning": "Drowsiness can occur in some people. Take care with driving or other activities requiring alertness until you know how it affects you.",
    },
}


def _normalize_medicine_name(medicine_name: str) -> str:
    return " ".join(medicine_name.strip().lower().split())


@app.get("/")
def root():
    return {
        "name": app.title,
        "status": "running",
        "version": app.version,
        "safety_note": SAFETY_NOTE,
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/medicine/{medicine_name}")
def medicine_info(medicine_name: str):
    medicine = _normalize_medicine_name(medicine_name)

    if not medicine:
        raise HTTPException(status_code=400, detail="Medicine name cannot be empty.")

    if len(medicine) > 100:
        raise HTTPException(status_code=400, detail="Medicine name is too long.")

    result = MEDICINES.get(medicine)
    if result is None:
        return {
            "name": medicine_name.strip(),
            "found": False,
            "message": "Medicine not found in the demo knowledge base.",
            "safety_note": SAFETY_NOTE,
        }

    return {
        **result,
        "found": True,
        "safety_note": SAFETY_NOTE,
    }
