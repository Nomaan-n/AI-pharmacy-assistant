from dataclasses import dataclass
import re
import httpx
from .config import get_settings

@dataclass
class GroundingResult:
    medication: dict
    context: str
    sources: list[dict]
    grounded: bool

class DailyMedRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def retrieve(self, question: str) -> GroundingResult:
        medication = self._extract_medication_candidate(question)
        if not medication:
            return GroundingResult({}, "No specific medication identified.", [], False)
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(
                    f"{self.settings.daily_med_base_url}/spls.json",
                    params={"drug_name": medication, "name_type": "both", "pagesize": 3, "page": 1},
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("data", [])
                if not rows:
                    return GroundingResult({}, f"No DailyMed label was found for '{medication}'.", [], False)
                row = rows[0]
                set_id = row.get("setid") or row.get("SETID")
                title = row.get("title") or row.get("TITLE") or "DailyMed label"
                if not set_id:
                    return GroundingResult({}, "A DailyMed result was found but no label ID was returned.", [], False)
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
                return GroundingResult(
                    {"name": medication, "title": str(title), "label_set_id": str(set_id)},
                    context,
                    [source],
                    bool(context),
                )
        except (httpx.HTTPError, ValueError, KeyError):
            return GroundingResult({}, f"Live DailyMed retrieval was unavailable for '{medication}'.", [], False)

    @staticmethod
    def _extract_medication_candidate(question: str) -> str | None:
        known = [
            "acetaminophen", "paracetamol", "ibuprofen", "amoxicillin", "metformin",
            "amlodipine", "losartan", "atorvastatin", "omeprazole", "cetirizine",
            "azithromycin", "diclofenac", "pantoprazole", "levothyroxine", "aspirin",
            "warfarin", "insulin", "prednisone", "salbutamol", "albuterol"
        ]
        q = question.lower()
        for name in known:
            if re.search(rf"\b{re.escape(name)}\b", q):
                return name
        match = re.search(r"(?:about|for|taking|take|using|use)\s+([A-Za-z][A-Za-z-]{2,30})\b", question, re.I)
        return match.group(1) if match else None

    @staticmethod
    def _label_text(xml: str) -> str:
        text = re.sub(r"<[^>]+>", " ", xml)
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _select_relevant_context(text: str, question: str) -> str:
        keywords = ["boxed warning", "warnings", "precautions", "contraindications", "adverse reactions", "drug interactions", "indications and usage"]
        q = question.lower()
        preferred = ["drug interactions", "adverse reactions", "warnings", "precautions"] if "interaction" in q or "side effect" in q else keywords
        chunks = []
        lower = text.lower()
        for keyword in preferred:
            idx = lower.find(keyword)
            if idx >= 0:
                chunks.append(text[max(0, idx - 100): idx + 1200])
            if len(" ".join(chunks)) > 5000:
                break
        return " ".join(chunks)[:6000]
