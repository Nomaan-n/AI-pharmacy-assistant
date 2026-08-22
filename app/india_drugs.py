from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)


# High-confidence Indian brand identities. These records are identification
# data only, not prescribing data. Exact matching is intentionally strict so a
# similarly named brand cannot silently replace the requested product.
KNOWN_BRANDS: dict[str, dict[str, str]] = {
    "zerodolsp": {
        "brand_name": "Zerodol-SP",
        "generic_name": "Aceclofenac 100 mg + Paracetamol 325 mg + Serratiopeptidase 15 mg",
        "manufacturer": "Ipca Laboratories Ltd",
        "strength": "100 mg + 325 mg + 15 mg",
        "form": "oral tablet",
        "source_url": "https://ipca.com/wp-content/pdf/revised-pricelist-of-all-domestic-formulations-applicable-22-09-2025.pdf",
        "source_title": "IPCA domestic formulations list",
        "source_type": "Manufacturer product reference",
    },
    "zerodolspas": {
        "brand_name": "Zerodol-Spas",
        "generic_name": "Drotaverine + Aceclofenac",
        "manufacturer": "Ipca Laboratories Ltd",
        "strength": "100 mg + 80 mg",
        "form": "oral tablet",
        "source_url": "https://www.ipca.com/pharmaceutical-formulations-manufacturers-india/?id=pr_95",
        "source_title": "IPCA pharmaceutical formulations",
        "source_type": "Manufacturer product reference",
    },
    "suhagra": {
        "brand_name": "Suhagra",
        "generic_name": "Sildenafil",
        "manufacturer": "Cipla Ltd",
        "strength": "Multiple strengths available; strength not specified in query",
        "form": "oral tablet",
        "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet",
        "source_title": "Apollo Pharmacy - Suhagra-50 Tablet",
        "source_type": "Indian product reference",
    },
    "suhagra50": {
        "brand_name": "Suhagra-50",
        "generic_name": "Sildenafil 50 mg",
        "manufacturer": "Cipla Ltd",
        "strength": "50 mg",
        "form": "oral tablet",
        "source_url": "https://www.apollopharmacy.in/medicine/suhagra-50mg-tablet",
        "source_title": "Apollo Pharmacy - Suhagra-50 Tablet",
        "source_type": "Indian product reference",
    },
    "suhagra100": {
        "brand_name": "Suhagra-100",
        "generic_name": "Sildenafil 100 mg",
        "manufacturer": "Cipla Ltd",
        "strength": "100 mg",
        "form": "oral tablet",
        "source_url": "https://www.apollopharmacy.in/medicine/suhagra-100mg-tablet",
        "source_title": "Apollo Pharmacy - Suhagra-100 Tablet",
        "source_type": "Indian product reference",
    },
    "augmentin625duo": {
        "brand_name": "Augmentin 625 Duo",
        "generic_name": "Amoxycillin 500 mg + Clavulanic Acid 125 mg",
        "manufacturer": "GSK India",
        "strength": "500 mg + 125 mg",
        "form": "film-coated tablet",
        "source_url": "https://india-pharma.gsk.com/media/6335/augmentin-duo-tablets.pdf",
        "source_title": "GSK India - Augmentin Duo prescribing information",
        "source_type": "Manufacturer product reference",
    },
    "augmentin1gduo": {
        "brand_name": "Augmentin 1g Duo",
        "generic_name": "Amoxycillin 875 mg + Clavulanic Acid 125 mg",
        "manufacturer": "GSK India",
        "strength": "875 mg + 125 mg",
        "form": "film-coated tablet",
        "source_url": "https://india-pharma.gsk.com/media/6335/augmentin-duo-tablets.pdf",
        "source_title": "GSK India - Augmentin Duo prescribing information",
        "source_type": "Manufacturer product reference",
    },
}

# Unambiguous spelling/strength aliases only. These never map one strength or
# formulation to another product.
BRAND_ALIASES: dict[str, str] = {
    "zerodolsp10032515": "zerodolsp",
    "zerodolsp10032515mg": "zerodolsp",
    "zerodolspas": "zerodolspas",
    "zerodolspas10080": "zerodolspas",
    "zerodolspas10080mg": "zerodolspas",
    "suhagra50mg": "suhagra50",
    "suhagra50mgtablet": "suhagra50",
    "suhagra100mg": "suhagra100",
    "suhagra100mgtablet": "suhagra100",
    "augmentin625": "augmentin625duo",
    "augmentin625mg": "augmentin625duo",
    "augmentin625duotablet": "augmentin625duo",
    "augmentin1g": "augmentin1gduo",
    "augmentin1gduotablet": "augmentin1gduo",
}


class IndiaDrugRegistry:
    """Best-effort resolver for Indian branded medicines.

    The registry is used for product identification, not clinical claims.
    Brand matching is deliberately strict: a near-match such as "Zerodol Spas"
    must never be presented as the requested "Zerodol-SP".
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def search(self, query: str | None, limit: int = 5) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if len(query) < 2:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(
                    f"{self.settings.india_drug_db_url}/search",
                    params={"q": query, "type": "medicine", "limit": limit},
                )
                response.raise_for_status()
                payload = response.json()
            return self._normalize_search(payload)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("India drug registry lookup failed: %s", type(exc).__name__)
            return []

    async def exact_brand(self, query: str | None, limit: int = 12) -> dict[str, Any] | None:
        """Return a product only when its registered brand exactly matches query."""
        query_key = self.normalize_brand(query)
        if not query_key:
            return None

        matches = await self.search(query, limit=limit)
        for match in matches:
            if self.normalize_brand(match.get("brand_name")) == query_key:
                return match

        canonical_key = BRAND_ALIASES.get(query_key, query_key)
        known = KNOWN_BRANDS.get(canonical_key)
        if known:
            return dict(known)
        return None

    async def same_composition_brands(
        self,
        generic_name: str | None,
        exclude_brand: str | None = None,
        limit: int = 20,
    ) -> list[str]:
        """Return only registry brands with the same normalized composition."""
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
            if not brand or not composition:
                continue
            if self.normalize_composition(composition) != target:
                continue
            brand_key = self.normalize_brand(brand)
            if not brand_key or brand_key == excluded or brand_key in seen:
                continue
            seen.add(brand_key)
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
                payload = response.json()
            return self._normalize_detail(payload)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def normalize_brand(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def normalize_composition(value: Any) -> str:
        value = str(value or "").lower()
        value = re.sub(r"\s+", "", value)
        value = re.sub(r"[^a-z0-9]+", "", value)
        return value

    @staticmethod
    def _normalize_search(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            rows = payload.get("results") or payload.get("medicines") or payload.get("data") or []
        else:
            rows = payload if isinstance(payload, list) else []
        if not isinstance(rows, list):
            return []
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized.append({
                "id": row.get("sctId") or row.get("sctid") or row.get("id") or row.get("conceptId"),
                "brand_name": row.get("brand") or row.get("brandName") or row.get("name") or row.get("medicineName"),
                "generic_name": row.get("generic") or row.get("genericName") or row.get("salt") or row.get("composition"),
                "manufacturer": row.get("manufacturer") or row.get("company") or row.get("firmName"),
                "strength": row.get("strength"),
                "form": row.get("doseForm") or row.get("form") or row.get("dosageForm"),
            })
        return [r for r in normalized if r.get("brand_name") or r.get("generic_name")]

    @staticmethod
    def _normalize_detail(payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        row = payload.get("medicine") if isinstance(payload.get("medicine"), dict) else payload
        return {
            "id": row.get("sctId") or row.get("sctid") or row.get("id") or row.get("conceptId"),
            "brand_name": row.get("brand") or row.get("brandName") or row.get("name") or row.get("medicineName"),
            "generic_name": row.get("generic") or row.get("genericName") or row.get("salt") or row.get("composition"),
            "manufacturer": row.get("manufacturer") or row.get("company") or row.get("firmName"),
            "strength": row.get("strength"),
            "form": row.get("doseForm") or row.get("form") or row.get("dosageForm"),
            "generic_id": row.get("genericId") or row.get("genericSctId") or row.get("genericSctID"),
        }

    @staticmethod
    def purchase_links(name: str) -> list[dict[str, str]]:
        q = quote_plus(name.strip())
        return [
            {"name": "Tata 1mg", "url": f"https://www.1mg.com/search/all?name={q}"},
            {"name": "Apollo Pharmacy", "url": f"https://www.apollopharmacy.in/search-medicines/{q}"},
            {"name": "Netmeds", "url": f"https://www.netmeds.com/catalogsearch/result?q={q}"},
            {"name": "PharmEasy", "url": f"https://pharmeasy.in/search/all?name={q}"},
        ]