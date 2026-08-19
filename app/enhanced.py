from typing import Any
from urllib.parse import quote_plus
import requests
from fastapi import Query

RXNORM = "https://rxnav.nlm.nih.gov/REST"
OPENFDA = "https://api.fda.gov/drug/label.json"

def _get(url: str, params: dict[str, Any], timeout: float = 7.0) -> dict[str, Any]:
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        return {}

def rxnorm_candidates(term: str) -> list[dict[str, Any]]:
    data = _get(f"{RXNORM}/approximateTerm.json", {"term": term, "maxEntries": 8})
    out = []
    for item in data.get("approximateGroup", {}).get("candidate", []) or []:
        if item.get("rxcui"):
            out.append({"rxcui": item["rxcui"], "name": item.get("name"), "score": item.get("score")})
    return out

def rxnorm_products(term: str) -> list[dict[str, Any]]:
    data = _get(f"{RXNORM}/Prescribe/drugs.json", {"name": term, "expand": "psn,tty"})
    out = []
    for group in data.get("drugGroup", {}).get("conceptGroup", []) or []:
        for c in group.get("conceptProperties", []) or []:
            if c.get("rxcui") and c.get("name"):
                out.append({"rxcui": c["rxcui"], "name": c["name"], "tty": c.get("tty")})
    return out[:25]

def fda_label(term: str) -> dict[str, Any]:
    q = quote_plus(term.strip())
    data = _get(OPENFDA, {"search": f"openfda.generic_name:{q} OR openfda.brand_name:{q}", "limit": 3})
    results = data.get("results") or []
    if not results:
        data = _get(OPENFDA, {"search": f"openfda.substance_name:{q}", "limit": 3})
        results = data.get("results") or []
    if not results:
        return {}
    r = results[0]
    of = r.get("openfda", {})
    return {
        "brand_names": (of.get("brand_name") or [])[:8],
        "generic_names": (of.get("generic_name") or [])[:8],
        "manufacturer": (of.get("manufacturer_name") or [])[:8],
        "route": (of.get("route") or [])[:8],
        "dosage_form": (of.get("dosage_form") or [])[:8],
        "indications": (r.get("indications_and_usage") or [])[:2],
        "warnings": (r.get("warnings") or [])[:2],
        "contraindications": (r.get("contraindications") or [])[:2],
        "adverse_reactions": (r.get("adverse_reactions") or [])[:2],
        "drug_interactions": (r.get("drug_interactions") or [])[:2],
        "source": "openFDA drug labeling",
    }

def register(app):
    @app.get("/api/identify")
    def identify(text: str = Query(min_length=2, max_length=300)):
        candidates = rxnorm_candidates(text)
        products = rxnorm_products(text)
        return {"query": text, "candidates": candidates, "products": products, "confidence_note": "Approximate matches are candidates for manual verification, especially for OCR or handwritten prescriptions.", "source": "NIH/NLM RxNorm"}

    @app.get("/api/drug-profile/{medicine_name}")
    def drug_profile(medicine_name: str):
        candidates = rxnorm_candidates(medicine_name)
        fda = fda_label(medicine_name)
        return {"query": medicine_name, "match": candidates[0] if candidates else None, "alternatives": candidates[1:5], "label": fda, "sources": ["NIH/NLM RxNorm", "U.S. FDA openFDA"] if fda else ["NIH/NLM RxNorm"], "last_checked": "live"}

    @app.get("/api/safety-check")
    def safety_check(medicines: str = Query(min_length=2, max_length=500)):
        names = [x.strip() for x in medicines.split(",") if x.strip()][:12]
        profiles = []
        for name in names:
            candidates = rxnorm_candidates(name)
            profiles.append({"query": name, "best_match": candidates[0] if candidates else None})
        return {"medicines": profiles, "status": "identification_only", "message": "This endpoint verifies medication concepts. It does not make individualized interaction, dosing, or treatment decisions.", "next_step": "Use a validated clinical interaction service before presenting an interaction result to a patient.", "source": "NIH/NLM RxNorm"}
