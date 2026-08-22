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
    """Resolve medicine identity dynamically without a finite hard-coded catalog.

    Identity priority:
      1. Exact Indian product registry match.
      2. High-confidence RxNorm concept match.
      3. Exact openFDA brand/generic/substance match.

    Clinical claims are NOT generated here. The grounding pipeline separately
    uses authoritative labels after identity resolution.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.timeout = settings.request_timeout_seconds
        self.india = IndiaDrugRegistry()

    async def resolve(self, query: str | None) -> dict[str, Any] | None:
        query = self._clean(query)
        if not query:
            return None

        # Never replace an exact Indian brand with a fuzzy near-match.
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
                candidates = (
                    response.json().get("approximateGroup", {}).get("candidate", []) or []
                )
                if isinstance(candidates, dict):
                    candidates = [candidates]
                candidates = sorted(candidates, key=self._score, reverse=True)
                candidate = next((c for c in candidates if self._rxnorm_candidate_is_safe(query, c)), None)
                if not candidate:
                    return None

                rxcui = str(candidate.get("rxcui") or "")
                matched = str(candidate.get("rxnormName") or candidate.get("name") or query)
                if not rxcui:
                    return None

                ingredients = await self._rx_related(client, rxcui)
                generic = ", ".join(
                    value for value in ingredients if value and not self._looks_like_product(value)
                ) or self._generic_from_name(matched)

                return {
                    "brand_name": self._brand_from_name(matched),
                    "generic_name": generic,
                    "manufacturer": None,
                    "strength": self._strength_from_name(matched),
                    "form": self._dosage_form(matched),
                    "rxcui": rxcui,
                    "ingredients": ingredients,
                    "rxnorm_name": matched,
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
            return result[:12]
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return []

    async def _openfda(self, query: str) -> dict[str, Any] | None:
        escaped = query.replace('"', '\\"')
        searches = [
            ("brand_name", f'openfda.brand_name:"{escaped}"'),
            ("generic_name", f'openfda.generic_name:"{escaped}"'),
            ("substance_name", f'openfda.substance_name:"{escaped}"'),
        ]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for field, search in searches:
                    response = await client.get(OPENFDA_BASE, params={"search": search, "limit": 5})
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    results = response.json().get("results", []) or []
                    for row in results:
                        fda = row.get("openfda", {}) or {}
                        brands = self._as_list(fda.get("brand_name"))
                        generics = self._as_list(fda.get("generic_name") or fda.get("substance_name"))
                        if not self._openfda_match(query, field, brands, generics):
                            continue
                        forms = self._as_list(fda.get("dosage_form"))
                        manufacturers = self._as_list(fda.get("manufacturer_name"))
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

    @classmethod
    def _rxnorm_candidate_is_safe(cls, query: str, candidate: dict[str, Any]) -> bool:
        if cls._score(candidate) < 90:
            return False
        matched = str(candidate.get("rxnormName") or candidate.get("name") or "").strip()
        if not matched:
            return False
        q = cls._normalize(query)
        m = cls._normalize(matched)
        return q == m or m.startswith(q) or q in m

    @staticmethod
    def _openfda_match(query: str, field: str, brands: list[str], generics: list[str]) -> bool:
        q = UniversalDrugResolver._normalize(query)
        values = brands if field == "brand_name" else generics
        return q in [UniversalDrugResolver._normalize(value) for value in values]

    @staticmethod
    def _with_source(row: dict[str, Any], source_type: str) -> dict[str, Any]:
        result = dict(row)
        result.setdefault("source_title", str(row.get("brand_name") or "Indian medicine registry"))
        result.setdefault("source_type", source_type)
        return result

    @staticmethod
    def _score(candidate: dict[str, Any]) -> float:
        try:
            return float(candidate.get("score", 0))
        except (TypeError, ValueError):
            return 0.0

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
    def _strength_from_name(name: str) -> str | None:
        matches = re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%|units?)\b", name, flags=re.IGNORECASE)
        return " + ".join(dict.fromkeys(matches)) if matches else None

    @staticmethod
    def _dosage_form(name: str) -> str | None:
        lower = name.lower()
        forms = [
            "oral solution", "oral suspension", "extended-release tablet", "delayed-release tablet",
            "tablet", "capsule", "injection", "cream", "ointment", "gel", "patch", "inhaler",
            "spray", "drops", "syrup", "suppository", "powder", "granules",
        ]
        for form in forms:
            if form in lower:
                return form
        return None

    @staticmethod
    def _looks_like_product(value: str) -> bool:
        lower = value.lower()
        return any(token in lower for token in (" tablet", " capsule", " solution", " suspension", " cream", " ointment", " injection", " inhaler"))

    @staticmethod
    def _as_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if not value:
            return None
        value = re.sub(r"[?!.]+$", "", value.strip())
        value = re.sub(r"\s+", " ", value)
        return value[:120] or None
