from typing import Any
import requests
from urllib.parse import quote_plus
RXNORM="https://rxnav.nlm.nih.gov/REST"; OPENFDA="https://api.fda.gov/drug/label.json"
def get_json(url,params=None,timeout=8):
    try:
        r=requests.get(url,params=params,timeout=timeout); r.raise_for_status(); return r.json()
    except (requests.RequestException,ValueError): return None
def rxnorm_search(term):
    data=get_json(f"{RXNORM}/drugs.json",{"name":term}); out=[]; seen=set()
    for group in (data or {}).get("drugGroup",{}).get("conceptGroup",[]):
        for p in group.get("conceptProperties",[]) or []:
            n=p.get("name")
            if n and n.lower() not in seen: seen.add(n.lower()); out.append({"name":n,"rxcui":p.get("rxcui"),"tty":p.get("tty"),"source":"NIH RxNorm"})
    return out[:20]
def rxnorm_properties(rxcui): return (get_json(f"{RXNORM}/rxcui/{rxcui}/properties.json") or {}).get("properties",{})
def interactions(rxcuis):
    ids=[x for x in rxcuis if x]
    if len(ids)<2:return {"status":"not_checked","interactions":[],"reason":"At least two verified medication concepts are required."}
    data=get_json(f"{RXNORM}/interaction/list.json",{"rxcuis":"+".join(ids)})
    if data is None:return {"status":"unavailable","interactions":[],"reason":"Authoritative interaction service unavailable; no safety conclusion made."}
    found=[]
    for group in data.get("fullInteractionTypeGroup",[]) or []:
        for typ in group.get("fullInteractionType",[]) or []:
            for pair in typ.get("fullInteractionPair",[]) or []: found.append({"description":pair.get("description"),"severity":pair.get("severity"),"source":typ.get("comment") or group.get("sourceName")})
    return {"status":"checked","count":len(found),"interactions":found[:100],"source":"NIH RxNav"}
def fda_label(term):
    data=get_json(OPENFDA,{"search":f'openfda.generic_name:"{term}"',"limit":1},timeout=10)
    if not data or not data.get("results"): return None
    x=data["results"][0]
    def first(k):
        v=x.get(k); return v[0] if isinstance(v,list) and v else v
    return {"indications":first("indications_and_usage"),"warnings":first("warnings"),"contraindications":first("contraindications"),"source":"U.S. FDA openFDA","label_version":first("version")}
def india_links(term):
    q=quote_plus(term)
    return [{"name":"CDSCO","region":"India","url":"https://www.cdsco.gov.in/opencms/opencms/en/"},{"name":"CDSCO Data Bank","region":"India","url":"https://www.cdsco.gov.in/opencms/opencms/en/Data-Bank/Data-Bank-Sub-cat/"},{"name":"National List of Essential Medicines","region":"India","url":"https://cdsco.gov.in/opencms/opencms/en/consumer/Essential-Medicines/"},{"name":"Tata 1mg","region":"India","url":f"https://www.1mg.com/search/all?name={q}"},{"name":"PharmEasy","region":"India","url":f"https://pharmeasy.in/search/all?name={q}"},{"name":"Apollo Pharmacy","region":"India","url":f"https://www.apollopharmacy.in/search-medicines?query={q}"},{"name":"Netmeds","region":"India","url":f"https://www.netmeds.com/products?search={q}&verticalspecification=Medicine"}]
