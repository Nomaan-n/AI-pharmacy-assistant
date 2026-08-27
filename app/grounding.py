from dataclasses import dataclass
import re
import httpx
from .config import get_settings
from .india_drugs import IndiaDrugRegistry
from .universal_drugs import UniversalDrugResolver

@dataclass
class GroundingResult:
    medication: dict
    context: str
    sources: list[dict]
    grounded: bool


class DailyMedRetriever:
    """Resolve medicines dynamically, then ground clinical facts in trusted labels."""

    VERIFIED_BRANDS = {
        "suhagra": {"brand_name": "Suhagra", "generic_name": "Sildenafil", "manufacturer": "Cipla Ltd", "strength": "Multiple strengths; strength not specified in query", "form": "oral tablet", "source_url": "https://www.cipla.com/", "source_title": "Cipla - Suhagra product family", "source_type": "Indian manufacturer reference", "use_summary": "Suhagra contains sildenafil and is primarily used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation."},
        "suhagra50": {"brand_name": "Suhagra 50", "generic_name": "Sildenafil 50 mg", "manufacturer": "Cipla Ltd", "strength": "50 mg", "form": "oral tablet", "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet", "source_title": "Suhagra-50 Tablet - Apollo Pharmacy", "source_type": "Indian product reference", "use_summary": "Suhagra 50 contains sildenafil and is used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation."},
        "suhagra100": {"brand_name": "Suhagra 100", "generic_name": "Sildenafil 100 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg", "form": "oral tablet", "source_url": "https://www.cipla.com/", "source_title": "Cipla - Suhagra product family", "source_type": "Indian manufacturer reference", "use_summary": "Suhagra 100 contains sildenafil and is used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation."},
        "zerodolsp": {"brand_name": "Zerodol-SP", "generic_name": "Aceclofenac 100 mg + Paracetamol 325 mg + Serratiopeptidase 15 mg", "manufacturer": "Ipca Laboratories Ltd", "strength": "100 mg + 325 mg + 15 mg", "form": "oral tablet", "source_url": "https://www.ipca.com/", "source_title": "Ipca Laboratories - Zerodol product family", "source_type": "Indian manufacturer reference", "use_summary": "Zerodol-SP is a pain-relief combination used for short-term relief of pain and inflammation."},
        "zerodolspas": {"brand_name": "Zerodol-Spas", "generic_name": "Aceclofenac 100 mg + Drotaverine Hydrochloride 80 mg", "manufacturer": "Ipca Laboratories Ltd", "strength": "100 mg + 80 mg", "form": "oral tablet", "source_url": "https://www.ipca.com/", "source_title": "Ipca Laboratories - Zerodol product family", "source_type": "Indian manufacturer reference", "use_summary": "Zerodol-Spas is a combination used for relief of pain associated with muscle or abdominal spasms."},
    }
    KNOWN = {"acetaminophen", "paracetamol", "ibuprofen", "amoxicillin", "metformin", "amlodipine", "losartan", "atorvastatin", "omeprazole", "cetirizine", "azithromycin", "diclofenac", "pantoprazole", "levothyroxine", "aspirin", "warfarin", "insulin", "prednisone", "salbutamol", "albuterol"}
    STOPWORDS = {"my", "the", "a", "an", "this", "that", "medicine", "medication", "drug", "tablet", "capsule", "prescribed", "dose", "dosage", "pill", "blood", "thinner", "pain", "question"}

    def __init__(self) -> None:
        self.settings = get_settings()
        self.india = IndiaDrugRegistry()
        self.universal = UniversalDrugResolver()

    async def retrieve(self, question: str) -> GroundingResult:
        query = self._extract_medication_candidate(question)
        if not query:
            return GroundingResult({}, "No specific medication was identified. Do not infer a drug from a medication category or symptom.", [], False)
        verified = self.VERIFIED_BRANDS.get(self._brand_key(query))
        product = dict(verified) if verified else None
        if not product: product = await self.india.exact_brand(query)
        if not product: product = await self.universal.resolve(query)
        india_context = self._india_context(product) if product else {}
        medication_name = (product.get("generic_name") if product else None) or query
        product_source = self._product_source(product)
        label_result = await self._dailymed(medication_name, question)
        if label_result:
            medication, context, source = label_result
            merged = {"name": query, **india_context, **medication}
            return GroundingResult(merged, context, ([product_source] if product_source else []) + [source], True)
        fda_result = await self._openfda(medication_name, question)
        if fda_result:
            medication, context, source = fda_result
            merged = {"name": query, **india_context, **medication}
            return GroundingResult(merged, context, ([product_source] if product_source else []) + [source], True)
        if product:
            context = self._product_context(product)
            return GroundingResult({"name": query, **india_context}, context, [product_source] if product_source else [], bool(context))
        return GroundingResult({"name": query}, f"No verified medication product or label was found for '{query}'. Do not guess its composition or use.", [], False)

    async def _dailymed(self, medication: str, question: str) -> tuple[dict, str, dict] | None:
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(f"{self.settings.daily_med_base_url}/spls.json", params={"drug_name": medication, "name_type": "both", "pagesize": 3, "page": 1})
                response.raise_for_status()
                rows = response.json().get("data", [])
                if not rows: return None
                for row in rows:
                    set_id = row.get("setid") or row.get("setId")
                    if not set_id: continue
                    detail = await client.get(f"{self.settings.daily_med_base_url}/spls/{set_id}.json")
                    detail.raise_for_status()
                    payload = detail.json()
                    xml = payload.get("xml", "") or payload.get("data", "") or ""
                    text = self._label_text(xml)
                    if not text: continue
                    context = self._select_relevant_context(text, question)
                    if context:
                        return {"name": medication, "label_source": "DailyMed", "set_id": str(set_id)}, context, {"title": f"DailyMed label: {medication}", "url": f"{self.settings.daily_med_base_url}/spls/{set_id}.json", "source_type": "DailyMed", "published_or_updated": None}
        except (httpx.HTTPError, ValueError, KeyError, TypeError): return None
        return None

    async def _openfda(self, medication: str, question: str) -> tuple[dict, str, dict] | None:
        escaped = medication.replace('"', '\\"')
        searches = [("brand_name", f'openfda.brand_name:"{escaped}"'), ("generic_name", f'openfda.generic_name:"{escaped}"'), ("substance_name", f'openfda.substance_name:"{escaped}"')]
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                for field, search in searches:
                    response = await client.get("https://api.fda.gov/drug/label.json", params={"search": search, "limit": 5})
                    if response.status_code == 404: continue
                    response.raise_for_status()
                    results = response.json().get("results", []) or []
                    for row in results:
                        openfda = row.get("openfda", {}) or {}
                        brand = (openfda.get("brand_name") or [None])[0]
                        generic = (openfda.get("generic_name") or openfda.get("substance_name") or [None])[0]
                        forms = openfda.get("dosage_form") or []
                        manufacturers = openfda.get("manufacturer_name") or []
                        values = openfda.get("brand_name") or [] if field == "brand_name" else openfda.get("generic_name") or openfda.get("substance_name") or []
                        if self._normalize(medication) not in {self._normalize(v) for v in values}: continue
                        indication = row.get("indications_and_usage") or []
                        warnings = row.get("warnings") or []
                        precautions = row.get("precautions") or []
                        interactions = row.get("drug_interactions") or []
                        adverse = row.get("adverse_reactions") or []
                        q = question.lower()
                        chunks = interactions + warnings + precautions if "interaction" in q else adverse + warnings + precautions if "side effect" in q or "adverse" in q else indication + warnings + precautions
                        context = " ".join(str(x) for x in chunks if x)[:6000]
                        if context:
                            return {"name": medication, "brand_name": brand, "generic_name": generic, "form": forms[0] if forms else None, "manufacturer": manufacturers[0] if manufacturers else None, "label_source": "openFDA"}, context, {"title": f"openFDA drug label: {brand or generic or medication}", "url": "https://open.fda.gov/apis/drug/label/", "source_type": "openFDA", "published_or_updated": None}
        except (httpx.HTTPError, ValueError, KeyError, TypeError): return None
        return None

    @staticmethod
    def _product_source(row: dict | None) -> dict | None:
        if not row: return None
        url = row.get("source_url")
        if not url: return None
        return {"title": str(row.get("source_title") or row.get("brand_name") or "Medicine product reference"), "url": str(url), "source_type": str(row.get("source_type") or "Medicine product reference"), "published_or_updated": None}

    @staticmethod
    def _product_context(row: dict) -> str:
        brand, generic, manufacturer = row.get("brand_name"), row.get("generic_name"), row.get("manufacturer")
        strength, form, use_summary = row.get("strength"), row.get("form"), row.get("use_summary")
        parts = []
        if brand: parts.append(f"Product: {brand}.")
        if generic: parts.append(f"Active ingredient/composition: {generic}.")
        if manufacturer: parts.append(f"Manufacturer: {manufacturer}.")
        if strength or form: parts.append(f"Strength/form: {(strength or '').strip()} {(form or '').strip()}.".strip())
        if use_summary: parts.append(f"Verified product information: {use_summary}")
        return " ".join(parts)

    @classmethod
    def _india_context(cls, row: dict | None) -> dict:
        if not row: return {}
        return {"india_brand_name": row.get("brand_name"), "india_generic_name": row.get("generic_name"), "india_manufacturer": row.get("manufacturer"), "india_strength": row.get("strength"), "india_form": row.get("form")}

    @classmethod
    def _brand_key(cls, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @classmethod
    def _extract_medication_candidate(cls, question: str) -> str | None:
        q = question.lower().strip()
        generic_patterns = [
            r"^what\s+is\s+([A-Za-z][A-Za-z0-9 .+/-]{2,80}?)(?:\s+used\s+for)?[?!.]*$",
            r"^what\s+are\s+the\s+uses\s+of\s+([A-Za-z][A-Za-z0-9 .+/-]{2,80})[?!.]*$",
            r"^tell\s+me\s+about\s+([A-Za-z][A-Za-z0-9 .+/-]{2,80})[?!.]*$",
            r"^information\s+(?:on|about)\s+([A-Za-z][A-Za-z0-9 .+/-]{2,80})[?!.]*$",
            r"^uses?\s+of\s+([A-Za-z][A-Za-z0-9 .+/-]{2,80})[?!.]*$",
        ]
        for pattern in generic_patterns:
            match = re.match(pattern, q, re.I)
            if match:
                candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
                if candidate and candidate not in cls.STOPWORDS: return candidate
        if len(q) <= 80 and not re.search(r"[?]", q):
            plain = re.sub(r"^(?:medicine|medication|drug)\s*[:=-]\s*", "", q).strip()
            if plain and len(plain.split()) <= 5 and plain not in cls.STOPWORDS and not any(token in plain.split() for token in {"why", "when", "where", "should", "can", "could"}): return plain
        for name in cls.KNOWN:
            if re.search(rf"\b{re.escape(name)}\b", q): return name
        brand_patterns = [
            r"what\s+does\s+([A-Za-z0-9][A-Za-z0-9 .&+/-]{2,50}?)\s+(?:do|treat|contain|mean)\b",
            r"what\s+is\s+([A-Za-z0-9][A-Za-z0-9 .&+/-]{2,50}?)\s+(?:used|for)\b",
            r"(?:about|for|taking|take|using|use)\s+([A-Za-z0-9][A-Za-z0-9 .&+/-]{2,50})\b",
        ]
        for pattern in brand_patterns:
            match = re.search(pattern, question, re.I)
            if match:
                candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
                if candidate and candidate.lower() not in cls.STOPWORDS: return candidate.lower()
        return None

    @staticmethod
    def _label_text(xml: str) -> str:
        text = re.sub(r"<[^>]+>", " ", xml)
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _select_relevant_context(text: str, question: str) -> str:
        keywords = ["boxed warning", "warnings", "precautions", "contraindications", "adverse reactions", "drug interactions", "indications and usage"]
        q = question.lower()
        if "interaction" in q: preferred = ["drug interactions", "warnings", "precautions", "contraindications"]
        elif "side effect" in q or "adverse" in q: preferred = ["adverse reactions", "warnings", "precautions"]
        elif "use" in q or "used" in q or "treat" in q or "what does" in q: preferred = ["indications and usage", "warnings", "precautions"]
        else: preferred = keywords
        chunks, lower = [], text.lower()
        for keyword in preferred:
            idx = lower.find(keyword)
            if idx >= 0: chunks.append(text[max(0, idx - 100): idx + 1400])
            if len(" ".join(chunks)) > 5000: break
        return " ".join(chunks)[:6000]

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())
