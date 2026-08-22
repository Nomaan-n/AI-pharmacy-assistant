from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from .config import get_settings
from .india_drugs import IndiaDrugRegistry


RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_BASE = "https://api.fda.gov/drug/label.json"


class UniversalDrugResolver:
    """Resolve medicines dynamically instead of maintaining a finite hard-coded catalog.

    Source priority is: exact Indian product registry, RxNorm, openFDA labels.
    DailyMed remains the preferred source for US label grounding and is handled
    by the existing retriever. A source is used for facts only when it returns
    an identifiable product or ingredient.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.timeout = settings.request_timeout_seconds
        self.india = IndiaDrugRegistry()

    async def resolve(self, query: str | None) -> dict[str, Any] | None:
        query = self._clean(query)
        if not query:
            return None

        # Exact Indian brand identity first. This prevents near-match errors such
        # as Zerodol-SP being replaced by Zerodol Spas.
        india = await self.india.exact_brand(query)
        if india:
            return self._with_source(india, "Indian medicine registry")

        rx = await self._rxnorm(query)
        if rx:
            return rx

        fda = await self._openfda(query)
        if fda:
            return fda

        return None

    async def _rxnorm(self, query: str) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{RXNORM_BASE}/approximateTerm.json",
                    params={"term": query, "maxEntries": 8, "option": 1},
                )
                response.raise_for_status()
                candidates = response.json().get("approximateGroup", {}).get("candidate", []) or []
                if isinstance(candidates, dict):
                    candidates = [candidates]
                candidates = sorted(candidates, key=self._score, reverse=True)
                candidate = next((c for c in candidates if self._score(c) >= 85), None)
                if not candidate:
                    return None

                rxcui = str(candidate.get("rxcui") or "")
                matched = str(candidate.get("rxnormName") or candidate.get("name") or query)
                if not rxcui:
                    return None

                ingredients = await self._rx_related(client, rxcui)
                products = await self._rx_drugs(client, matched)
                generic = self._best_generic(products) or self._generic_from_name(matched)
                form = self._dosage_form(matched)
                brand = self._brand_from_name(matched)

                return {
                    "brand_name": brand,
                    "generic_name": generic,
                    "manufacturer": None,
                    "strength": None,
                    "form": form,
                    "rxcui": rxcui,
                    "ingredients": ingredients,
                    "source_title": f"RxNorm: {matched}",
                    "source_url": f"https://rxnav.nlm.nih.gov/REST/rxcui/{quote_plus(rxcui)}/allProperties.json",
                    "source_type": "RxNorm/NLM",
                }
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return None

    async def _rx_related(self, client: httpx.AsyncClient, rxcui: str) -> list[str]:
        try:
            response = await client.get(
                f"{RXNORM_BASE}/rxcui/{quote_plus(rxcui)}/related.json",
                params={"tty": "IN PIN MIN"},
            )
            response.raise_for_status()
            groups = response.json().get("relatedGroup", {}).get("conceptGroup", []) or []
            result: list[str] = []
            for group in groups:
                for item in group.get("conceptProperties", []) or []:
                    name = item.get("name")
                    if name and name not in result:
                        result.append(str(name))
            return result[:8]
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return []

    async def _rx_drugs(self, client: httpx.AsyncClient, name: str) -> list[dict[str, Any]]:
        try:
            response = await client.get(f"{RXNORM_BASE}/drugs.json", params={"name": name})
            response.raise_for_status()
            groups = response.json().get("drugGroup", {}).get("conceptGroup", []) or []
            result: list[dict[str, Any]] = []
            for group in groups:
                props = group.get("conceptProperties", []) or []
                if isinstance(props, dict):
                    props = [props]
                result.extend(props)
            return result
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return []

    async def _openfda(self, query: str) -> dict[str, Any] | None:
        escaped = query.replace('"', "\\\"")
        searches = [
            f'openfda.brand_name:"{escaped}"',
            f'openfda.generic_name:"{escaped}"',
            f'openfda.substance_name:"{escaped}"',
        ]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for search in searches:
                    response = await client.get(OPENFDA_BASE, params={"search": search, "limit": 1})
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    results = response.json().get("results", []) or []
                    if not results:
                        continue
                    row = results[0]
                    fda = row.get("openfda", {}) or {}
                    brands = fda.get("brand_name") or []
                    generics = fda.get("generic_name") or fda.get("substance_name") or []
                    forms = fda.get("dosage_form") or []
                    manufacturers = fda.get("manufacturer_name") or []
                    return {
                        "brand_name": brands[0] if brands else None,
                        "generic_name": generics[0] if generics else None,
                        "manufacturer": manufacturers[0] if manufacturers else None,
                        "strength": None,
                        "form": forms[0] if forms else None,
                        "source_title": "openFDA drug label",
                        "source_url": "https://open.fda.gov/apis/drug/label/",
                        "source_type": "openFDA",
                    }
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return None
        return None

    @staticmethod
    def _with_source(row: dict[str, Any], source_type: str) -> dict[str, Any]:
        result = dict(row)
        result.setdefault("source_title", str(row.get("brand_name") or "Indian medicine registry"))
        result.setdefault("source_url", "https://drugdb.in/")
        result.setdefault("source_type", source_type)
        return result

    @staticmethod
    def _score(candidate: dict[str, Any]) -> float:
        try:
            return float(candidate.get("score", 0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _best_generic(products: list[dict[str, Any]]) -> str | None:
        for tty in ("SCD", "GPCK", "IN", "PIN", "MIN"):
            for product in products:
                if product.get("tty") == tty and product.get("name"):
                    return str(product["name"])
        return None

    @staticmethod
    def _generic_from_name(name: str) -> str | None:
        value = re.sub(r"\s*\[[^]]+\]\s*$", "", name).strip()
        return value or None

    @staticmethod
    def _brand_from_name(name: str) -> str | None:
        if " [" in name:
            return name.split(" [", 1)[0].strip()
        return None

    @staticmethod
    def _dosage_form(name: str) -> str | None:
        lower = name.lower()
        forms = [
            "oral solution", "oral suspension", "extended-release tablet", "tablet",
            "capsule", "injection", "cream", "ointment", "gel", "patch", "inhaler",
            "spray", "drops", "syrup", "suppository", "powder", "granules",
        ]
        for form in forms:
            if form in lower:
                return form
        return None

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if not value:
            return None
        value = re.sub(r"[?!.]+$", "", value.strip())
        value = re.sub(r"\s+", " ", value)
        return value[:120] or None
