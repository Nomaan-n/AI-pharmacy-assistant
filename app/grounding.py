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
        "suhagra": {
            "brand_name": "Suhagra",
            "generic_name": "Sildenafil",
            "manufacturer": "Cipla Ltd",
            "strength": "Multiple strengths; strength not specified in query",
            "form": "oral tablet",
            "source_url": "https://www.cipla.com/",
            "source_title": "Cipla - Suhagra product family",
            "source_type": "Indian manufacturer reference",
            "use_summary": "Suhagra contains sildenafil and is primarily used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation.",
        },
        "suhagra50": {
            "brand_name": "Suhagra 50",
            "generic_name": "Sildenafil 50 mg",
            "manufacturer": "Cipla Ltd",
            "strength": "50 mg",
            "form": "oral tablet",
            "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet",
            "source_title": "Suhagra-50 Tablet - Apollo Pharmacy",
            "source_type": "Indian product reference",
            "use_summary": "Suhagra 50 contains sildenafil and is used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation.",
        },
        "suhagra100": {
            "brand_name": "Suhagra 100",
            "generic_name": "Sildenafil 100 mg",
            "manufacturer": "Cipla Ltd",
            "strength": "100 mg",
            "form": "oral tablet",
            "source_url": "https://www.cipla.com/",
            "source_title": "Cipla - Suhagra product family",
            "source_type": "Indian manufacturer reference",
            "use_summary": "Suhagra 100 contains sildenafil and is used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation.",
        },
        "zerodolsp": {
            "brand_name": "Zerodol-SP",
            "generic_name": "Aceclofenac 100 mg + Paracetamol 325 mg + Serratiopeptidase 15 mg",
            "manufacturer": "Ipca Laboratories Ltd",
            "strength": "100 mg + 325 mg + 15 mg",
            "form": "oral tablet",
            "source_url": "https://www.ipca.com/",
            "source_title": "Ipca Laboratories - Zerodol product family",
            "source_type": "Indian manufacturer reference",
            "use_summary": "Zerodol-SP is a pain-relief combination used for short-term relief of pain and inflammation.",
        },
        "zerodolspas": {
            "brand_name": "Zerodol-Spas",
            "generic_name": "Aceclofenac 100 mg + Drotaverine Hydrochloride 80 mg",
            "manufacturer": "Ipca Laboratories Ltd",
            "strength": "100 mg + 80 mg",
            "form": "oral tablet",
            "source_url": "https://www.ipca.com/",
            "source_title": "Ipca Laboratories - Zerodol product family",
            "source_type": "Indian manufacturer reference",
            "use_summary": "Zerodol-Spas is a combination used for relief of pain associated with muscle or abdominal spasms.",
        },
    }
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

        label_result = await self._dailymed(medication_name, question)
        if label_result:
            medication, context, source = label_result
            merged = {"name": query, **india_context, **medication}
            sources = ([product_source] if product_source else []) + [source]
            return GroundingResult(merged, context, sources, True)

        # DailyMed does not cover every marketed product/ingredient. Fall back
        # to the FDA structured label API for clinical indication text, while
        # keeping the Indian product identity separate from the clinical label.
        fda_result = await self._openfda(medication_name, question)
        if fda_result:
            medication, context, source = fda_result
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
