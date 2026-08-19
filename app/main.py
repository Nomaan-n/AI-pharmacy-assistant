from typing import Any
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AI Pharmacy Assistant", version="3.0.0", description="Accessible medication information assistant with live RxNorm lookup.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

DEMO = {
 "paracetamol":{"name":"Paracetamol","category":"Pain & fever","uses":["Fever","Mild to moderate pain"],"warning":"Do not exceed the product-label dose. Too much can seriously damage the liver.","tip":"Check combination cold or pain medicines for paracetamol."},
 "acetaminophen":{"name":"Acetaminophen","category":"Pain & fever","uses":["Fever","Mild to moderate pain"],"warning":"Do not exceed the product-label dose. Too much can seriously damage the liver.","tip":"Check combination products because this ingredient may appear under another name."},
 "ibuprofen":{"name":"Ibuprofen","category":"Pain & inflammation","uses":["Pain","Fever","Inflammation"],"warning":"NSAIDs can cause stomach, kidney and cardiovascular problems in some people.","tip":"Ask a pharmacist if you have ulcers, kidney disease, heart disease, take blood thinners, or are pregnant."},
 "cetirizine":{"name":"Cetirizine","category":"Allergy relief","uses":["Sneezing","Runny nose","Itching"],"warning":"Some people become sleepy or less alert.","tip":"See how it affects you before driving or doing anything requiring full alertness."},
 "loratadine":{"name":"Loratadine","category":"Allergy relief","uses":["Sneezing","Runny nose","Itching"],"warning":"Drowsiness can occur in some people.","tip":"Check the label and ask a pharmacist if you take other medicines."},
 "omeprazole":{"name":"Omeprazole","category":"Acid reflux","uses":["Heartburn","Acid reflux"],"warning":"Persistent or severe symptoms need professional assessment.","tip":"Use according to the product instructions or professional advice."},
 "amoxicillin":{"name":"Amoxicillin","category":"Antibiotic","uses":["Certain bacterial infections"],"warning":"It does not treat viral illnesses. Serious allergic reactions are possible.","tip":"Use antibiotics only when appropriately prescribed or supplied."},
 "metformin":{"name":"Metformin","category":"Diabetes medicine","uses":["Type 2 diabetes","Blood glucose control"],"warning":"Suitability and dosing depend on the individual.","tip":"Take exactly as prescribed and discuss kidney problems or severe illness with your clinician."},
 "atorvastatin":{"name":"Atorvastatin","category":"Cholesterol medicine","uses":["Lowering cholesterol","Reducing cardiovascular risk"],"warning":"Unexplained severe muscle pain or weakness should be assessed promptly.","tip":"Tell your clinician about other medicines and supplements."},
}

def rxnorm_search(term: str) -> list[dict[str, Any]]:
    try:
        r = requests.get("https://rxnav.nlm.nih.gov/REST/drugs.json", params={"name": term}, timeout=5)
        r.raise_for_status()
        groups = r.json().get("drugGroup", {}).get("conceptGroup", [])
        out = []
        seen = set()
        for group in groups:
            for c in group.get("conceptProperties", []):
                name = c.get("name")
                if name and name.lower() not in seen:
                    seen.add(name.lower()); out.append({"name": name, "rxcui": c.get("rxcui"), "tty": c.get("tty")})
        return out[:20]
    except (requests.RequestException, ValueError):
        return []

@app.get("/", include_in_schema=False)
def root(): return FileResponse("static/index.html")

@app.get("/health")
def health(): return {"status":"healthy","version":app.version}

@app.get("/api/medicines")
def medicines(): return {"count":len(DEMO),"medicines":list(DEMO.values()),"live_lookup":True}

@app.get("/api/medicine/{medicine_name}")
def medicine(medicine_name: str):
    key = medicine_name.strip().lower()
    if key in DEMO: return {**DEMO[key],"found":True,"source":"educational dataset"}
    matches = rxnorm_search(medicine_name.strip())
    if matches:
        m = matches[0]
        return {"found":True,"name":m["name"],"rxcui":m.get("rxcui"),"category":"Medication","uses":[],"warning":"This live result identifies a medication concept but does not provide individualized dosing or safety advice.","tip":"Use the medicine label and consult a pharmacist or clinician for indication, dose, interactions and suitability.","source":"NIH RxNorm"}
    return {"found":False,"name":medicine_name.strip(),"message":"No medication concept was found."}

@app.get("/api/search")
def search(q: str = Query(min_length=1,max_length=80)):
    term=q.strip().lower(); local=[]
    for item in DEMO.values():
        if term in " ".join([item["name"],item["category"],*item["uses"]]).lower(): local.append({**item,"source":"educational dataset"})
    live=rxnorm_search(q.strip()) if len(local)<5 else []
    return {"query":q,"count":len(local)+len(live),"results":local,"live_results":live}

app.mount("/static", StaticFiles(directory="static"), name="static")
