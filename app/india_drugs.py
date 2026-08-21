from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)


class IndiaDrugRegistry:
    """Best-effort resolver for Indian branded medicines.

    Uses the NRCeS/C-DAC Common Drug Codes for India service exposed by
    drugdb.in for identification and composition. Clinical claims remain
    grounded in authoritative labeling.
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
