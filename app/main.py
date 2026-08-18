from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Pharmacy Assistant",
    version="1.0.0",
    description="Educational medication information API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDICINES = {
    "paracetamol": {
        "name": "Paracetamol",
        "uses": "Commonly used for pain and fever.",
        "warning": "Do not exceed the recommended dose. Too much can seriously damage the liver."
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "uses": "Commonly used for pain, inflammation and fever.",
        "warning": "Can cause stomach irritation and may not be suitable for people with certain stomach, kidney or heart problems."
    },
    "cetirizine": {
        "name": "Cetirizine",
        "uses": "An antihistamine commonly used for allergy symptoms.",
        "warning": "May cause drowsiness in some people."
    }
}

@app.get("/")
def root():
    return {
        "name": "AI Pharmacy Assistant",
        "status": "running",
        "version": app.version
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/medicine/{medicine_name}")
def medicine_info(medicine_name: str):
    medicine = medicine_name.strip().lower()

    if medicine in MEDICINES:
        return MEDICINES[medicine]

    return {
        "name": medicine_name,
        "message": "Medicine not found in the demo database.",
        "note": "This assistant provides educational information and is not a substitute for a doctor or pharmacist."
    }
