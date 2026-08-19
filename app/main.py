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

def rxnorm_search(term: str):
    try:
        r = requests.get("https://rxnav.nlm.nih.gov/REST/drugs.json", params={"name":term}, timeout=5)
        r.raise_for_status(); data=r.json(); out=[]
        for group in data.get("drugGroup",{}).get("conceptGroup",[]):
            for p in group.get("conceptProperties",[]): out.append({"name":p.get("name"),"rxcui":p.get("rxcui"),"source":"NIH RxNorm"})
        return out[:20]
    except Exception:
        return []

@app.get("/", include_in_schema=False)
def root(): return FileResponse("static/index.html")
@app.get("/health")
def health(): return {"status":"healthy","version":app.version}
@app.get("/api/medicines")
def medicines(): return {"count":len(DEMO),"medicines":list(DEMO.values())}
@app.get("/api/medicine/{medicine_name}")
def medicine(medicine_name:str):
    key=medicine_name.strip().lower(); item=DEMO.get(key)
    if item: return {**item,"found":True}
    live=rxnorm_search(medicine_name)
    return {"found":False,"name":medicine_name,"matches":live,"message":"No curated safety entry was found. Matches are medication concepts only; verify with a pharmacist or clinician."}
@app.get("/api/search")
def search(q:str=Query(min_length=1,max_length=80)):
    term=q.strip().lower(); local=[]
    for item in DEMO.values():
        if term in " ".join([item["name"],item["category"],*item["uses"]]).lower(): local.append({**item,"source":"educational dataset"})
    live=rxnorm_search(q.strip()) if len(local)<5 else []
    return {"query":q,"count":len(local)+len(live),"results":local,"live_results":live}

@app.get("/api/buy-links/{medicine_name}")
def buy_links(medicine_name: str):
    from urllib.parse import quote_plus
    q = quote_plus(medicine_name.strip())
    return {"medicine": medicine_name.strip(), "links": [
        {"region":"India","store":"Tata 1mg","url":f"https://www.1mg.com/search/all?name={q}"},
        {"region":"India","store":"PharmEasy","url":f"https://pharmeasy.in/search/all?name={q}"},
        {"region":"India","store":"Apollo Pharmacy","url":f"https://www.apollopharmacy.in/search-medicines?query={q}"},
        {"region":"India","store":"Netmeds","url":f"https://www.netmeds.com/products?search={q}&verticalspecification=Medicine"},
        {"region":"United States","store":"GoodRx","url":f"https://www.goodrx.com/search?query={q}"},
        {"region":"Worldwide","store":"Google Shopping","url":f"https://www.google.com/search?tbm=shop&q={q}+medicine"},
    ], "notice":"Availability, price, delivery area and prescription requirements vary by country and product. These are external search links, not purchase guarantees."}

app.mount("/static", StaticFiles(directory="static"), name="static")
