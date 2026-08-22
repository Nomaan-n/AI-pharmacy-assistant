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
        "suhagra50": {
            "brand_name": "Suhagra 50",
            "generic_name": "Sildenafil 50 mg",
            "manufacturer": "Cipla Ltd",
            "strength": "50 mg",
            "form": "oral tablet",
            "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet",
            "source_title": "Suhagra-50 Tablet - Apollo Pharmacy",
            "source_type": "Indian product reference",
        },
    }

    # Kept only as a fast path for common generic names. Coverage no longer
    # depends on this list because UniversalDrugResolver queries live sources.
    KNOWN = {
        "acetaminophen", "paracetamol", "ibuprofen", "amoxicillin", "metformin",
        "amlodipine", "losartan", "atorvastatin", "omeprazole", "cetirizine",
        "azithromycin", "diclofenac", "pantoprazole", "levothyroxine", "aspirin",
        "warfarin", "insulin", "prednisone", "salbutamol", "albuterol"
    }
    STOPWORDS = {
        "my", "the", "a", "an", "this", "that", "medicine", "medication",
        "drug", "tablet", "capsule", "prescribed", "dose", "dosage", "pill",
        "blood", "thinner", "pain", "question"
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.india = IndiaDrugRegistry()
        self.universal = UniversalDrugResolver()

    async def retrieve(self, question: str) -> GroundingResult:
        query = self._extract_medication_candidate(question)
        if not query:
            return GroundingResult(
                {},
                "No specific medication was identified. Do not infer a drug from a medication category or symptom.",
                [],
                False,
            )

        # Exact verified product first. This is deliberately before any fuzzy
        # resolver so a brand cannot silently become a similarly named product.
        verified = self.VERIFIED_BRANDS.get(self._brand_key(query))
        product = dict(verified) if verified else None
        if not product:
            product = await self.india.exact_brand(query)
        if not product:
            product = await self.universal.resolve(query)

        india_context = self._india_context(product) if product else {}
        medication_name = (
            product.get("generic_name") if product else None
        ) or query

        product_source = self._product_source(product)

        # Once a product/ingredient is identified, retrieve the most relevant
        # DailyMed label as the clinical grounding layer. Product identity and
        # label facts are kept separate so an Indian brand is not confused with
        # a different brand carrying a similar name.
        label_result = await self._dailymed(medication_name, question)
        if label_result:
            medication, context, source = label_result
            merged = {"name": query, **india_context, **medication}
            sources = ([product_source] if product_source else []) + [source]
            return GroundingResult(merged, context, sources, True)

        if product:
            context = self._product_context(product)
            return GroundingResult(
                {"name": query, **india_context},
                context,
                [product_source] if product_source else [],
                bool(context),
            )

        return GroundingResult(
            {"name": query},
            f"No verified medication product or label was found for '{query}'. Do not guess its composition or use.",
            [],
            False,
        )

    async def _dailymed(self, medication: str, question: str) -> tuple[dict, str, dict] | None:
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(
                    f"{self.settings.daily_med_base_url}/spls.json",
                    params={"drug_name": medication, "name_type": "both", "pagesize": 3, "page": 1},
                )
                response.raise_for_status()
                rows = response.json().get("data", [])
                if not rows:
                    return None
                row = rows[0]
                set_id = row.get("setid") or row.get("SETID")
                title = row.get("title") or row.get("TITLE") or "DailyMed label"
                if not set_id:
                    return None
                label_response = await client.get(f"{self.settings.daily_med_base_url}/spls/{set_id}.xml")
                label_response.raise_for_status()
                text = self._label_text(label_response.text)
                context = self._select_relevant_context(text, question)
                if not context:
                    return None
                source = {
                    "title": str(title),
                    "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}",
                    "source_type": "DailyMed/NLM",
                    "published_or_updated": None,
                }
                return ({"title": str(title), "label_set_id": str(set_id)}, context, source)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _product_source(row: dict | None) -> dict | None:
        if not row:
            return None
        url = row.get("source_url")
        title = row.get("source_title") or row.get("brand_name") or "Medicine product reference"
        source_type = row.get("source_type") or "Medicine product reference"
        if not url:
            return None
        return {
            "title": str(title),
            "url": str(url),
            "source_type": str(source_type),
            "published_or_updated": None,
        }

    @staticmethod
    def _product_context(row: dict) -> str:
        brand = row.get("brand_name")
        generic = row.get("generic_name")
        manufacturer = row.get("manufacturer")
        strength = row.get("strength")
        form = row.get("form")
        parts = []
        if brand:
            parts.append(f"Product: {brand}.")
        if generic:
            parts.append(f"Active ingredient/composition: {generic}.")
        if manufacturer:
            parts.append(f"Manufacturer: {manufacturer}.")
        if strength or form:
            parts.append(f"Strength/form: {(strength or '').strip()} {(form or '').strip()}.".strip())
        parts.append("This identifies the medicine product; clinical use should be based on the supplied authoritative label or reference.")
        return " ".join(parts)

    @staticmethod
    def _brand_key(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def _india_context(row: dict | None) -> dict:
        if not row:
            return {}
        return {
            "india_brand_name": row.get("brand_name"),
            "india_generic_name": row.get("generic_name"),
            "india_manufacturer": row.get("manufacturer"),
            "india_strength": row.get("strength"),
            "india_form": row.get("form"),
        }

    @classmethod
    def _extract_medication_candidate(cls, question: str) -> str | None:
        q = question.lower()
        for name in cls.KNOWN:
            if re.search(rf"\b{re.escape(name)}\b", q):
                return name

        brand_patterns = [
            r"what\s+does\s+([A-Za-z0-9][A-Za-z0-9 .&+/-]{2,50}?)\s+(?:do|treat|contain|mean)\b",
            r"what\s+is\s+([A-Za-z0-9][A-Za-z0-9 .&+/-]{2,50}?)\s+(?:used|for)\b",
            r"(?:about|for|taking|take|using|use)\s+([A-Za-z0-9][A-Za-z0-9 .&+/-]{2,50})\b",
        ]
        for pattern in brand_patterns:
            match = re.search(pattern, question, re.I)
            if match:
                candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
                if candidate and candidate.lower() not in cls.STOPWORDS:
                    return candidate.lower()
        return None

    @staticmethod
    def _label_text(xml: str) -> str:
        text = re.sub(r"<[^>]+>", " ", xml)
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _select_relevant_context(text: str, question: str) -> str:
        keywords = [
            "boxed warning", "warnings", "precautions", "contraindications",
            "adverse reactions", "drug interactions", "indications and usage"
        ]
        q = question.lower()
        if "interaction" in q:
            preferred = ["drug interactions", "warnings", "precautions", "contraindications"]
        elif "side effect" in q or "adverse" in q:
            preferred = ["adverse reactions", "warnings", "precautions"]
        elif "use" in q or "used" in q or "treat" in q or "what does" in q:
            preferred = ["indications and usage", "warnings", "precautions"]
        else:
            preferred = keywords
        chunks = []
        lower = text.lower()
        for keyword in preferred:
            idx = lower.find(keyword)
            if idx >= 0:
                chunks.append(text[max(0, idx - 100): idx + 1400])
            if len(" ".join(chunks)) > 5000:
                break
        return " ".join(chunks)[:6000]
