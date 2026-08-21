from dataclasses import dataclass
import re
import httpx
from .config import get_settings
from .medication_catalog import MedicationCatalog

@dataclass
class GroundingResult:
    medication: dict
    context: str
    sources: list[dict]
    grounded: bool


class DailyMedRetriever:
    """Resolve current medicine names dynamically, then ground facts in DailyMed."""

    STOPWORDS = {
        "my", "the", "a", "an", "this", "that", "medicine", "medication",
        "drug", "tablet", "capsule", "prescribed", "dose", "dosage", "pill",
        "blood", "thinner", "pain", "question", "does", "do", "used", "use",
        "uses", "side", "effects", "about", "for", "what", "is", "are"
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.catalog = MedicationCatalog(self.settings.request_timeout_seconds)

    async def retrieve(self, question: str) -> GroundingResult:
        candidate = self._extract_medication_candidate(question)
        if not candidate:
            return GroundingResult({}, "No specific medication was identified. Do not infer a drug from a medication category or symptom.", [], False)

        match = await self.catalog.resolve(candidate)
        lookup_name = match.normalized_name if match else candidate
        ingredient_name = match.ingredients[0] if match and match.ingredients else None

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(
                    f"{self.settings.daily_med_base_url}/spls.json",
                    params={"drug_name": lookup_name, "name_type": "both", "pagesize": 5, "page": 1},
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("data", [])

                # If a brand/product did not resolve directly, retry using the
                # normalized ingredient. This is important for brand queries.
                if not rows and ingredient_name:
                    response = await client.get(
                        f"{self.settings.daily_med_base_url}/spls.json",
                        params={"drug_name": ingredient_name, "name_type": "generic", "pagesize": 5, "page": 1},
                    )
                    response.raise_for_status()
                    rows = response.json().get("data", [])

                if not rows:
                    return GroundingResult(
                        self._medication_payload(candidate, match),
                        f"No current DailyMed label was found for '{candidate}'.",
                        self._sources_for_match(match),
                        False,
                    )

                row = rows[0]
                set_id = row.get("setid") or row.get("SETID")
                title = row.get("title") or row.get("TITLE") or "DailyMed label"
                if not set_id:
                    return GroundingResult(self._medication_payload(candidate, match), "A DailyMed result was found but no label ID was returned.", [], False)

                label_response = await client.get(f"{self.settings.daily_med_base_url}/spls/{set_id}.xml")
                label_response.raise_for_status()
                text = self._label_text(label_response.text)
                context = self._select_relevant_context(text, question)
                source = {
                    "title": str(title),
                    "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}",
                    "source_type": "DailyMed/NLM",
                    "published_or_updated": None,
                }
                medication = self._medication_payload(candidate, match)
                medication.update({"name": candidate, "title": str(title), "label_set_id": str(set_id)})
                return GroundingResult(medication, context, [source, *self._sources_for_match(match)], bool(context))
        except (httpx.HTTPError, ValueError, KeyError):
            return GroundingResult(self._medication_payload(candidate, match), f"Live DailyMed retrieval was unavailable for '{candidate}'.", self._sources_for_match(match), False)

    @classmethod
    def _extract_medication_candidate(cls, question: str) -> str | None:
        q = " ".join(question.strip().split())
        patterns = [
            r"what\s+does\s+(.+?)\s+do\b",
            r"what\s+is\s+(.+?)(?:\s+used\s+for|\s+for|\s+and\s+|\?|$)",
            r"uses?\s+of\s+(.+?)(?:\?|$)",
            r"side\s+effects?\s+of\s+(.+?)(?:\?|$)",
            r"about\s+(.+?)(?:\?|$)",
            r"(?:taking|take|using|use)\s+(.+?)(?:\s+for\s+|\s+and\s+|\?|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, q, re.I)
            if match:
                candidate = cls._clean_candidate(match.group(1))
                if candidate:
                    return candidate
        return None

    @classmethod
    def _clean_candidate(cls, value: str) -> str | None:
        value = re.sub(r"\b(my|the|this|medicine|medication|tablet|capsule)\b", " ", value, flags=re.I)
        value = re.sub(r"\s+", " ", value).strip(" ,.:;?!")
        if not value or len(value) > 100:
            return None
        if all(token.lower() in cls.STOPWORDS for token in value.split()):
            return None
        return value

    @staticmethod
    def _medication_payload(candidate: str, match) -> dict:
        if not match:
            return {"name": candidate}
        return {
            "name": candidate,
            "generic_name": match.generic_name,
            "brands": match.brands,
            "ingredients": match.ingredients,
            "dosage_form": match.dosage_form,
            "rxcui": match.rxcui,
            "confidence": match.confidence,
            "purchase_links": match.purchase_links,
        }

    @staticmethod
    def _sources_for_match(match) -> list[dict]:
        if not match:
            return []
        return [{"title": "RxNorm / U.S. National Library of Medicine", "url": f"https://rxnav.nlm.nih.gov/REST/rxcui/{match.rxcui}", "source_type": "RxNorm/NLM", "published_or_updated": None}]

    @staticmethod
    def _label_text(xml: str) -> str:
        text = re.sub(r"<[^>]+>", " ", xml)
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _select_relevant_context(text: str, question: str) -> str:
        keywords = ["boxed warning", "warnings", "precautions", "contraindications", "adverse reactions", "drug interactions", "indications and usage"]
        q = question.lower()
        if "interaction" in q:
            preferred = ["drug interactions", "warnings", "precautions", "contraindications"]
        elif "side effect" in q or "adverse" in q:
            preferred = ["adverse reactions", "warnings", "precautions"]
        elif "use" in q or "used" in q or "treat" in q or "do" in q:
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
