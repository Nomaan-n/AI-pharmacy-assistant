from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

import httpx


RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


@dataclass
class MedicationMatch:
    query_name: str
    normalized_name: str
    generic_name: str | None = None
    ingredients: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    dosage_form: str | None = None
    rxcui: str | None = None
    confidence: float = 0.0
    source: str = "RxNorm"

    @property
    def purchase_links(self) -> list[dict[str, str]]:
        q = quote_plus(self.normalized_name)
        return [
            {"name": "Tata 1mg", "url": f"https://www.1mg.com/search/all?name={q}"},
            {"name": "Apollo Pharmacy", "url": f"https://www.apollopharmacy.in/search-medicines/{quote_plus(self.normalized_name.replace(' ', '-'))}"},
            {"name": "PharmEasy", "url": f"https://pharmeasy.in/search/all?name={q}"},
            {"name": "Netmeds", "url": f"https://www.netmeds.com/catalogsearch/result?q={q}"},
        ]


class MedicationCatalog:
    """Dynamic medicine-name resolver backed by NLM RxNorm.

    The app must not ship a tiny hard-coded list of medicines. RxNorm provides
    active ingredients, brands, products, and approximate name matching. The
    catalog is queried at request time so newly added/current concepts can be
    resolved without rebuilding the application.
    """

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    async def resolve(self, name: str) -> MedicationMatch | None:
        name = self._clean_name(name)
        if not name:
            return None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            candidate = await self._approximate(client, name)
            if not candidate:
                return None

            rxcui = str(candidate.get("rxcui", ""))
            matched_name = str(candidate.get("rxnormName") or candidate.get("name") or name)
            score = self._score(candidate)
            if not rxcui or score < 70:
                return None

            groups = await self._get_drugs(client, matched_name)
            generic = self._best_generic(groups) or self._generic_from_name(matched_name)
            ingredients = await self._ingredients(client, rxcui)
            brands = await self._brands(client, ingredients)

            if not ingredients and generic:
                ingredients = self._extract_ingredients(generic)

            return MedicationMatch(
                query_name=name,
                normalized_name=matched_name,
                generic_name=generic,
                ingredients=ingredients,
                brands=brands,
                dosage_form=self._dosage_form(generic or matched_name),
                rxcui=rxcui,
                confidence=score,
            )

    async def _approximate(self, client: httpx.AsyncClient, name: str) -> dict[str, Any] | None:
        try:
            response = await client.get(
                f"{RXNORM_BASE}/approximateTerm.json",
                params={"term": name, "maxEntries": 8, "option": 1},
            )
            response.raise_for_status()
            data = response.json().get("approximateGroup", {})
            candidates = data.get("candidate", []) or []
            if isinstance(candidates, dict):
                candidates = [candidates]
            return max(candidates, key=self._score, default=None)
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    async def _get_drugs(self, client: httpx.AsyncClient, name: str) -> list[dict[str, Any]]:
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
        except (httpx.HTTPError, ValueError, TypeError):
            return []

    async def _ingredients(self, client: httpx.AsyncClient, rxcui: str) -> list[str]:
        try:
            response = await client.get(f"{RXNORM_BASE}/rxcui/{rxcui}/related.json", params={"tty": "IN PIN MIN"})
            response.raise_for_status()
            groups = response.json().get("relatedGroup", {}).get("conceptGroup", []) or []
            result: list[str] = []
            for group in groups:
                for item in group.get("conceptProperties", []) or []:
                    value = item.get("name")
                    if value and value not in result:
                        result.append(value)
            return result[:8]
        except (httpx.HTTPError, ValueError, TypeError):
            return []

    async def _brands(self, client: httpx.AsyncClient, ingredients: list[str]) -> list[str]:
        # Resolve each ingredient to an RxCUI, then ask RxNorm for brands that
        # contain all ingredients. This gives same-ingredient brand options,
        # not unqualified therapeutic substitutions.
        ids: list[str] = []
        for ingredient in ingredients[:4]:
            try:
                response = await client.get(f"{RXNORM_BASE}/rxcui.json", params={"name": ingredient})
                response.raise_for_status()
                concepts = response.json().get("idGroup", {}).get("rxnormId", []) or []
                if concepts:
                    ids.append(str(concepts[0]))
            except (httpx.HTTPError, ValueError, TypeError):
                continue
        if not ids:
            return []
        try:
            response = await client.get(f"{RXNORM_BASE}/brands.json", params={"ingredientids": " ".join(ids)})
            response.raise_for_status()
            props = response.json().get("brandGroup", {}).get("conceptProperties", []) or []
            if isinstance(props, dict):
                props = [props]
            return [str(p.get("name")) for p in props if p.get("name")][:12]
        except (httpx.HTTPError, ValueError, TypeError):
            return []

    @staticmethod
    def _score(candidate: dict[str, Any]) -> float:
        try:
            return float(candidate.get("score", 0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _best_generic(products: list[dict[str, Any]]) -> str | None:
        # SCD is a clinical drug, SBD is branded. Prefer the unbranded product.
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
    def _extract_ingredients(name: str) -> list[str]:
        # Conservative fallback. RxNorm remains authoritative when available.
        value = re.sub(r"\s+\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)\b", " ", name, flags=re.I)
        return [value.split(" oral ", 1)[0].strip()] if value.strip() else []

    @staticmethod
    def _dosage_form(name: str) -> str | None:
        lower = name.lower()
        forms = ["tablet", "capsule", "oral solution", "oral suspension", "injection", "cream", "ointment", "gel", "patch", "inhaler", "spray", "drops"]
        for form in forms:
            if form in lower:
                return form
        return None

    @staticmethod
    def _clean_name(value: str) -> str:
        value = re.sub(r"[?!.]+$", "", value.strip())
        value = re.sub(r"\s+", " ", value)
        return value[:120]
