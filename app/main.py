from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AI Pharmacy Assistant", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

MEDICINES = {
    "paracetamol": {"name":"Paracetamol","category":"Pain & fever","uses":["Fever","Mild to moderate pain"],"warning":"Do not exceed the dose on the product label. Too much can seriously damage the liver.","tip":"Check combination cold or pain medicines for paracetamol to avoid accidental double-dosing."},
    "ibuprofen": {"name":"Ibuprofen","category":"Pain & inflammation","uses":["Pain","Fever","Inflammation"],"warning":"It can irritate the stomach and may be unsuitable for some people with kidney, heart, stomach or other conditions.","tip":"If you have a long-term condition or take regular medicines, ask a pharmacist whether it is suitable."},
    "cetirizine": {"name":"Cetirizine","category":"Allergy relief","uses":["Sneezing","Runny nose","Itching"],"warning":"Some people become sleepy or less alert after taking it.","tip":"See how it affects you before driving or doing anything requiring full alertness."},
    "omeprazole": {"name":"Omeprazole","category":"Acid reflux","uses":["Heartburn","Acid reflux","Stomach acid-related conditions"],"warning":"Persistent or severe symptoms need professional assessment rather than repeated self-treatment.","tip":"Use it according to the product instructions or advice from a healthcare professional."},
    "amoxicillin": {"name":"Amoxicillin","category":"Antibiotic","uses":["Certain bacterial infections"],"warning":"It does not treat viral illnesses such as most colds and flu. Allergic reactions can be serious.","tip":"Use antibiotics only when prescribed or supplied appropriately by a qualified healthcare professional."},
}

@app.get("/", include_in_schema=False)
def root(): return FileResponse("static/index.html")
@app.get("/health")
def health(): return {"status":"healthy","version":app.version}
@app.get("/api/medicines")
def medicines(): return {"count":len(MEDICINES),"medicines":list(MEDICINES.values())}
@app.get("/api/medicine/{medicine_name}")
def medicine(medicine_name:str):
    item=MEDICINES.get(medicine_name.strip().lower())
    return {**item,"found":True} if item else {"found":False,"name":medicine_name.strip(),"message":"No entry found in this educational demo database."}
@app.get("/api/search")
def search(q:str=Query(min_length=1,max_length=80)):
    term=q.strip().lower(); results=[]
    for item in MEDICINES.values():
        hay=" ".join([item["name"],item["category"],*item["uses"]]).lower()
        if term in hay: results.append(item)
    return {"query":q,"count":len(results),"results":results}
app.mount("/static", StaticFiles(directory="static"), name="static")
