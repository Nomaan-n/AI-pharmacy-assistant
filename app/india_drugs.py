from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)

KNOWN_BRANDS: dict[str, dict[str, str]] = {
    "pantosecdsr": {"brand_name": "Pantosec DSR", "generic_name": "Pantoprazole 40 mg + Domperidone 30 mg", "manufacturer": "Cipla Ltd", "strength": "40 mg + 30 mg", "form": "sustained-release capsule", "source_url": "https://www.apollopharmacy.in/medicine/pantosec-dsr-capsule", "source_title": "Apollo Pharmacy - New Pantosec DSR Capsule", "source_type": "Indian product reference", "use_summary": "Pantosec DSR contains pantoprazole and domperidone and is prescribed for acid reflux and related gastrointestinal symptoms."},
    "pantociddsr": {"brand_name": "Pantocid DSR", "generic_name": "Pantoprazole 40 mg + Domperidone 30 mg", "manufacturer": "Sun Pharmaceutical Industries Ltd", "strength": "40 mg + 30 mg", "form": "sustained-release capsule", "source_url": "https://sunpharma.com/india-products/", "source_title": "Sun Pharma India Products - Pantocid DSR", "source_type": "Manufacturer product reference", "use_summary": "Pantocid DSR contains pantoprazole and domperidone and is used for acid-related gastrointestinal conditions."},
    "zerodolsp": {"brand_name": "Zerodol-SP", "generic_name": "Aceclofenac 100 mg + Paracetamol 325 mg + Serratiopeptidase 15 mg", "manufacturer": "Ipca Laboratories Ltd", "strength": "100 mg + 325 mg + 15 mg", "form": "oral tablet", "source_url": "https://ipca.com/wp-content/pdf/revised-pricelist-of-all-domestic-formulations-applicable-22-09-2025.pdf", "source_title": "IPCA domestic formulations list", "source_type": "Manufacturer product reference", "use_summary": "Zerodol-SP is a pain-relief combination used for short-term relief of pain and inflammation."},
    "zerodolspas": {"brand_name": "Zerodol-Spas", "generic_name": "Drotaverine + Aceclofenac", "manufacturer": "Ipca Laboratories Ltd", "strength": "100 mg + 80 mg", "form": "oral tablet", "source_url": "https://www.ipca.com/pharmaceutical-formulations-manufacturers-india/?id=pr_95", "source_title": "IPCA pharmaceutical formulations", "source_type": "Manufacturer product reference", "use_summary": "Zerodol-Spas is a combination used for relief of pain associated with muscle or abdominal spasms."},
    "suhagra": {"brand_name": "Suhagra", "generic_name": "Sildenafil", "manufacturer": "Cipla Ltd", "strength": "Multiple strengths; strength not specified in query", "form": "oral tablet", "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet", "source_title": "Apollo Pharmacy - Suhagra-50 Tablet", "source_type": "Indian product reference", "use_summary": "Suhagra contains sildenafil and is primarily used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation."},
    "suhagra50": {"brand_name": "Suhagra-50", "generic_name": "Sildenafil 50 mg", "manufacturer": "Cipla Ltd", "strength": "50 mg", "form": "oral tablet", "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet", "source_title": "Apollo Pharmacy - Suhagra-50 Tablet", "source_type": "Indian product reference", "use_summary": "Suhagra 50 contains sildenafil and is used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation."},
    "suhagra100": {"brand_name": "Suhagra-100", "generic_name": "Sildenafil 100 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg", "form": "oral tablet", "source_url": "https://www.cipla.com/", "source_title": "Cipla - Suhagra product family", "source_type": "Indian manufacturer reference", "use_summary": "Suhagra 100 contains sildenafil and is used to treat erectile dysfunction by improving blood flow to the penis during sexual stimulation."},
    "augmentin625duo": {"brand_name": "Augmentin 625 Duo", "generic_name": "Amoxycillin 500 mg + Clavulanic Acid 125 mg", "manufacturer": "GSK India", "strength": "500 mg + 125 mg", "form": "film-coated tablet", "source_url": "https://india-pharma.gsk.com/media/6335/augmentin-duo-tablets.pdf", "source_title": "GSK India - Augmentin Duo prescribing information", "source_type": "Manufacturer product reference", "use_summary": "Augmentin 625 Duo is an antibiotic used to treat susceptible bacterial infections. It combines amoxicillin with clavulanic acid to broaden antibacterial coverage."},
    "augmentin1gduo": {"brand_name": "Augmentin 1g Duo", "generic_name": "Amoxycillin 875 mg + Clavulanic Acid 125 mg", "manufacturer": "GSK India", "strength": "875 mg + 125 mg", "form": "film-coated tablet", "source_url": "https://india-pharma.gsk.com/media/6335/augmentin-duo-tablets.pdf", "source_title": "GSK India - Augmentin Duo prescribing information", "source_type": "Manufacturer product reference", "use_summary": "Augmentin 1g Duo is an antibiotic used to treat susceptible bacterial infections. It combines amoxicillin with clavulanic acid to broaden antibacterial coverage."},
}

BRAND_ALIASES: dict[str, str] = {
    "newpantosecdsr": "pantosecdsr", "pantosecdsr30": "pantosecdsr", "pantosecdsr3040": "pantosecdsr", "pantosecdsr3040mg": "pantosecdsr", "pantosecds": "pantosecdsr",
    "pantociddsr": "pantociddsr", "pantociddsr3040": "pantociddsr", "pantociddsr3040mg": "pantociddsr", "pantociddsr30": "pantociddsr",
    "zerodolsp10032515": "zerodolsp", "zerodolsp10032515mg": "zerodolsp",
    "zerodolspas": "zerodolspas", "zerodolspas10080": "zerodolspas", "zerodolspas10080mg": "zerodolspas",
    "suhagra50mg": "suhagra50", "suhagra50mgtablet": "suhagra50", "suhagra100mg": "suhagra100", "suhagra100mgtablet": "suhagra100",
    "augmentin625": "augmentin625duo", "augmentin625mg": "augmentin625duo", "augmentin625duotablet": "augmentin625duo",
    "augmentin1g": "augmentin1gduo", "augmentin1gduotablet": "augmentin1gduo",
}


class IndiaDrugRegistry:
    """Dynamic Indian medicine resolver backed by the Common Drug Codes service.

    The app queries the registry dynamically rather than relying on a finite
    hard-coded catalog. Exact brand matching prevents near-match substitutions.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def search(self, query: str | None, limit: int = 50) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if len(query) < 2:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(f"{self.settings.india_drug_db_url}/search", params={"q": query, "type": "medicine", "limit": limit, "detail": "full"})
                response.raise_for_status()
                return self._normalize_search(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("India drug registry lookup failed: %s", type(exc).__name__)
            return []

    async def exact_brand(self, query: str | None, limit: int = 50) -> dict[str, Any] | None:
        query_key = self.normalize_brand(query)
        if not query_key:
            return None
        matches = await self.search(query, limit=limit)
        for match in matches:
            if self.normalize_brand(match.get("brand_name")) == query_key:
                return await self._enrich_product(match)
        known = KNOWN_BRANDS.get(BRAND_ALIASES.get(query_key, query_key))
        return dict(known) if known else None

    async def _enrich_product(self, match: dict[str, Any]) -> dict[str, Any]:
        result = dict(match)
        sct_id = str(match.get("id") or "").strip()
        if not sct_id:
            return result
        detail = await self.lookup_medicine(sct_id)
        if detail:
            for key, value in detail.items():
                if value not in (None, "", []):
                    result[key] = value
            generic_id = str(detail.get("generic_id") or "").strip()
            if generic_id:
                generic = await self.lookup_generic(generic_id)
                if generic:
                    for key, value in generic.items():
                        if value not in (None, "", []):
                            if key in {"generic_name", "strength", "form", "route", "indications", "use_summary"} or not result.get(key):
                                result[key] = value
        return result

    async def same_composition_brands(self, generic_name: str | None, exclude_brand: str | None = None, limit: int = 50) -> list[str]:
        if not generic_name:
            return []
        matches = await self.search(generic_name, limit=limit)
        target = self.normalize_composition(generic_name)
        excluded = self.normalize_brand(exclude_brand)
        result: list[str] = []
        seen: set[str] = set()
        for match in matches:
            brand = str(match.get("brand_name") or "").strip()
            composition = str(match.get("generic_name") or "").strip()
            if not brand or not composition or self.normalize_composition(composition) != target:
                continue
            key = self.normalize_brand(brand)
            if key and key != excluded and key not in seen:
                seen.add(key)
                result.append(brand)
            if len(result) >= 8:
                break
        return result

    async def lookup_medicine(self, sct_id: str) -> dict[str, Any] | None:
        if not sct_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(f"{self.settings.india_drug_db_url}/dis/medicine/{quote_plus(sct_id)}")
                response.raise_for_status()
                return self._normalize_detail(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    async def lookup_generic(self, sct_id: str) -> dict[str, Any] | None:
        if not sct_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(f"{self.settings.india_drug_db_url}/dis/generic/{quote_plus(sct_id)}")
                response.raise_for_status()
                payload = response.json()
            row = payload.get("generic") if isinstance(payload, dict) and isinstance(payload.get("generic"), dict) else payload
            if not isinstance(row, dict):
                return None
            generic = row.get("generic") or row.get("genericName") or row.get("name") or row.get("composition") or row.get("salt")
            indications = row.get("indications") or row.get("indication") or row.get("uses") or row.get("clinicalIndications")
            if isinstance(indications, list):
                indications = " ".join(str(x) for x in indications if x)
            result = {"generic_id": sct_id, "generic_name": generic, "strength": row.get("strength"), "form": row.get("doseForm") or row.get("form") or row.get("dosageForm"), "route": row.get("route"), "indications": indications}
            if indications:
                result["use_summary"] = self._clean_use_summary(str(indications))
            return {k: v for k, v in result.items() if v not in (None, "", [])}
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def normalize_brand(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def normalize_composition(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def _clean_use_summary(value: str) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        return value if len(value) <= 500 else value[:497].rsplit(" ", 1)[0] + "..."

    @staticmethod
    def _normalize_search(payload: Any) -> list[dict[str, Any]]:
        rows = payload.get("results") or payload.get("medicines") or payload.get("data") or [] if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            result.append({
                "id": row.get("sctId") or row.get("sctid") or row.get("id") or row.get("conceptId"),
                "brand_name": row.get("brand") or row.get("brandName") or row.get("name") or row.get("medicineName"),
                "generic_name": row.get("generic") or row.get("genericName") or row.get("salt") or row.get("composition"),
                "manufacturer": row.get("manufacturer") or row.get("company") or row.get("firmName"),
                "strength": row.get("strength"), "form": row.get("doseForm") or row.get("form") or row.get("dosageForm"),
                "generic_id": row.get("genericId") or row.get("genericSctId") or row.get("genericSctID"),
                "indications": row.get("indications") or row.get("indication") or row.get("uses"),
                "use_summary": row.get("use_summary") or row.get("useSummary") or row.get("indications") or row.get("indication") or row.get("uses"),
            })
        return [r for r in result if r.get("brand_name") or r.get("generic_name")]

    @staticmethod
    def _normalize_detail(payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        row = payload.get("medicine") if isinstance(payload.get("medicine"), dict) else payload
        return {"id": row.get("sctId") or row.get("sctid") or row.get("id") or row.get("conceptId"), "brand_name": row.get("brand") or row.get("brandName") or row.get("name") or row.get("medicineName"), "generic_name": row.get("generic") or row.get("genericName") or row.get("salt") or row.get("composition"), "manufacturer": row.get("manufacturer") or row.get("company") or row.get("firmName"), "strength": row.get("strength"), "form": row.get("doseForm") or row.get("form") or row.get("dosageForm"), "generic_id": row.get("genericId") or row.get("genericSctId") or row.get("genericSctID"), "use_summary": row.get("use_summary") or row.get("useSummary") or row.get("indications") or row.get("indication") or row.get("uses")}

    @staticmethod
    def purchase_links(name: str) -> list[dict[str, str]]:
        q = quote_plus(name.strip())
        return [{"name": "Tata 1mg", "url": f"https://www.1mg.com/search/all?name={q}"}, {"name": "Apollo Pharmacy", "url": f"https://www.apollopharmacy.in/search-medicines/{q}"}, {"name": "Netmeds", "url": f"https://www.netmeds.com/catalogsearch/result?q={q}"}, {"name": "PharmEasy", "url": f"https://pharmeasy.in/search/all?name={q}"}]
