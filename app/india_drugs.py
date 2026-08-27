from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)

# High-confidence Indian products that may not be represented consistently across
# public catalog snapshots. This is a safety fallback, not the primary catalog.
KNOWN_BRANDS: dict[str, dict[str, str]] = {
    "nicip": {"brand_name": "Nicip", "generic_name": "Nimesulide 100 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg", "form": "oral tablet", "source_url": "https://www.apollopharmacy.in/medicine/nicip-tablet", "source_title": "Apollo Pharmacy - Nicip 100 mg Tablet", "source_type": "Indian product reference"},
    "nicip100": {"brand_name": "Nicip 100", "generic_name": "Nimesulide 100 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg", "form": "oral tablet", "source_url": "https://www.1mg.com/drugs/nicip-100mg-tablet-20853", "source_title": "Tata 1mg - Nicip 100 mg Tablet", "source_type": "Indian product reference"},
    "newnicip": {"brand_name": "New Nicip", "generic_name": "Nimesulide 100 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg", "form": "oral tablet", "source_url": "https://www.1mg.com/drugs/new-nicip-100mg-tablet-314215", "source_title": "Tata 1mg - New Nicip 100 mg Tablet", "source_type": "Indian product reference"},
    "nicipplus": {"brand_name": "Nicip Plus", "generic_name": "Nimesulide 100 mg + Paracetamol 325 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg + 325 mg", "form": "oral tablet", "source_url": "https://www.1mg.com/drugs/nicip-plus-tablet-163312", "source_title": "Tata 1mg - Nicip Plus Tablet", "source_type": "Indian product reference"},
    "nicipp": {"brand_name": "Nicip-P", "generic_name": "Nimesulide 100 mg + Paracetamol 325 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg + 325 mg", "form": "oral tablet", "source_url": "https://www.mims.com/india/drug/info/nicip-p", "source_title": "CIMS India - Nicip-P", "source_type": "Indian product reference"},
    "nicipd": {"brand_name": "Nicip-D", "generic_name": "Nimesulide 100 mg + Diclofenac sodium 50 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg + 50 mg", "form": "oral capsule", "source_url": "https://www.mims.com/india/drug/info/nicip-d", "source_title": "CIMS India - Nicip-D", "source_type": "Indian product reference"},
    "nicipmr": {"brand_name": "Nicip-MR", "generic_name": "Nimesulide 100 mg + Paracetamol 325 mg + Chlorzoxazone 375 mg", "manufacturer": "Cipla Ltd", "strength": "100 mg + 325 mg + 375 mg", "form": "oral tablet", "source_url": "https://www.mims.com/india/drug/info/nicip-mr", "source_title": "CIMS India - Nicip-MR", "source_type": "Indian product reference"},
    "nicipgel": {"brand_name": "Nicip Gel", "generic_name": "Nimesulide 10 mg/g", "manufacturer": "Cipla Ltd", "strength": "10 mg/g", "form": "topical gel", "source_url": "https://www.1mg.com/drugs/nicip-gel-262923", "source_title": "Tata 1mg - Nicip Gel", "source_type": "Indian product reference"},
    "pantosecdsr": {"brand_name": "Pantosec DSR", "generic_name": "Pantoprazole 40 mg + Domperidone 30 mg", "manufacturer": "Cipla Ltd", "strength": "40 mg + 30 mg", "form": "sustained-release capsule", "source_url": "https://www.apollopharmacy.in/medicine/pantosec-dsr-capsule", "source_title": "Apollo Pharmacy - Pantosec DSR Capsule", "source_type": "Indian product reference"},
    "pantociddsr": {"brand_name": "Pantocid DSR", "generic_name": "Pantoprazole 40 mg + Domperidone 30 mg", "manufacturer": "Sun Pharmaceutical Industries Ltd", "strength": "40 mg + 30 mg", "form": "sustained-release capsule", "source_url": "https://sunpharma.com/india-products/", "source_title": "Sun Pharma India Products - Pantocid DSR", "source_type": "Manufacturer product reference"},
    "zerodolsp": {"brand_name": "Zerodol-SP", "generic_name": "Aceclofenac 100 mg + Paracetamol 325 mg + Serratiopeptidase 15 mg", "manufacturer": "Ipca Laboratories Ltd", "strength": "100 mg + 325 mg + 15 mg", "form": "oral tablet", "source_url": "https://ipca.com/", "source_title": "IPCA domestic formulations", "source_type": "Manufacturer product reference"},
    "zerodolspas": {"brand_name": "Zerodol-Spas", "generic_name": "Drotaverine 80 mg + Aceclofenac 100 mg", "manufacturer": "Ipca Laboratories Ltd", "strength": "80 mg + 100 mg", "form": "oral tablet", "source_url": "https://www.ipca.com/", "source_title": "IPCA pharmaceutical formulations", "source_type": "Manufacturer product reference"},
    "suhagra": {"brand_name": "Suhagra", "generic_name": "Sildenafil", "manufacturer": "Cipla Ltd", "strength": "Multiple strengths", "form": "oral tablet", "source_url": "https://www.cipla.com/", "source_title": "Cipla product family", "source_type": "Manufacturer product reference"},
    "augmentin625duo": {"brand_name": "Augmentin 625 Duo", "generic_name": "Amoxycillin 500 mg + Clavulanic Acid 125 mg", "manufacturer": "GSK India", "strength": "500 mg + 125 mg", "form": "film-coated tablet", "source_url": "https://india-pharma.gsk.com/", "source_title": "GSK India product information", "source_type": "Manufacturer product reference"},
}

BRAND_ALIASES: dict[str, str] = {
    "newpantosecdsr": "pantosecdsr", "pantosecdsr30": "pantosecdsr", "pantosecdsr3040": "pantosecdsr", "pantosecds": "pantosecdsr",
    "pantociddsr3040": "pantociddsr", "pantociddsr30": "pantociddsr",
    "zerodolsp10032515": "zerodolsp", "zerodolspas10080": "zerodolspas",
    "suhagra50mg": "suhagra", "suhagra100mg": "suhagra", "augmentin625": "augmentin625duo", "augmentin625mg": "augmentin625duo",
    "nicip100mg": "nicip100", "nicip100mgtablet": "nicip100", "newnicip100": "newnicip", "newnicip100mg": "newnicip",
    "nicip100mgtablet": "nicip100", "nicipplus100325": "nicipplus", "nicipp100325": "nicipp",
}


class IndiaDrugRegistry:
    """Large Indian medicine catalog with exact, prefix, substring and remote fallback lookup."""

    DATASET_URL = "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv"

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.db_path = Path("data/india_medicines.sqlite3")

    def _connect(self) -> sqlite3.Connection | None:
        if not self.db_path.exists():
            return None
        db = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        return db

    async def search(self, query: str | None, limit: int = 50) -> list[dict[str, Any]]:
        q = self.normalize_brand(query)
        if len(q) < 2:
            return []
        rows: list[dict[str, Any]] = []
        db = self._connect()
        if db:
            try:
                # Search exact, prefix, substring and token fragments. The previous
                # implementation could miss valid brands when punctuation, strength,
                # or formulation text differed from the user's spelling.
                sql = """
                SELECT * FROM medicines
                WHERE name_norm = ?
                   OR name_norm LIKE ?
                   OR name_norm LIKE ?
                   OR composition_norm LIKE ?
                ORDER BY CASE
                    WHEN name_norm = ? THEN 0
                    WHEN name_norm LIKE ? THEN 1
                    WHEN name_norm LIKE ? THEN 2
                    ELSE 3 END,
                    length(name_norm)
                LIMIT ?
                """
                params = (q, q + "%", "%" + q + "%", "%" + q + "%", q, q + "%", "%" + q + "%", max(1, min(limit, 100)))
                for row in db.execute(sql, params):
                    rows.append(self._row(row))
            finally:
                db.close()
        if rows:
            return rows

        # Secondary public registry fallback for products missing from the local snapshot.
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(
                    f"{self.settings.india_drug_db_url}/search",
                    params={"q": query, "type": "medicine", "limit": limit, "detail": "full"},
                )
                response.raise_for_status()
                return self._normalize_search(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return []

    async def exact_brand(self, query: str | None, limit: int = 50) -> dict[str, Any] | None:
        q = self.normalize_brand(query)
        if not q:
            return None
        alias = BRAND_ALIASES.get(q, q)
        known = KNOWN_BRANDS.get(alias)
        if known:
            return dict(known)
        matches = await self.search(query, limit)
        for match in matches:
            if self.normalize_brand(match.get("brand_name")) == q:
                return match
        # If the query is a clean brand prefix such as "nicip", returning the
        # shortest matching active product is safer than declaring the brand absent.
        if matches:
            return sorted(matches, key=lambda x: len(self.normalize_brand(x.get("brand_name"))))[0]
        return None

    async def same_composition_brands(self, generic_name: str | None, exclude_brand: str | None = None, limit: int = 50) -> list[str]:
        if not generic_name:
            return []
        matches = await self.search(generic_name, limit)
        target = self.normalize_composition(generic_name)
        excluded = self.normalize_brand(exclude_brand)
        result, seen = [], set()
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

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        c1, c2 = str(row["composition1"] or "").strip(), str(row["composition2"] or "").strip()
        composition = " + ".join(x for x in (c1, c2) if x)
        return {"id": row["id"], "brand_name": row["name"], "generic_name": composition or None, "manufacturer": row["manufacturer"] or None, "strength": None, "form": row["medicine_type"] or None, "pack_size": row["pack_size"] or None, "price_inr": row["price"] or None, "source_title": "Indian Medicine Dataset", "source_url": "https://github.com/junioralive/Indian-Medicine-Dataset", "source_type": "Indian active medicine catalog", "is_discontinued": False}

    @staticmethod
    def normalize_brand(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def normalize_composition(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    @staticmethod
    def _normalize_search(payload: Any) -> list[dict[str, Any]]:
        rows = payload.get("results") or payload.get("medicines") or payload.get("data") or [] if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            result.append({"id": row.get("sctId") or row.get("sctid") or row.get("id") or row.get("conceptId"), "brand_name": row.get("brand") or row.get("brandName") or row.get("name") or row.get("medicineName"), "generic_name": row.get("generic") or row.get("genericName") or row.get("salt") or row.get("composition"), "manufacturer": row.get("manufacturer") or row.get("company") or row.get("firmName"), "strength": row.get("strength"), "form": row.get("doseForm") or row.get("form") or row.get("dosageForm"), "source_title": "Indian medicine registry", "source_type": "Indian medicine registry"})
        return [r for r in result if r.get("brand_name") or r.get("generic_name")]

    @staticmethod
    def purchase_links(name: str) -> list[dict[str, str]]:
        q = quote_plus(name.strip())
        return [{"name": "Tata 1mg", "url": f"https://www.1mg.com/search/all?name={q}"}, {"name": "Apollo Pharmacy", "url": f"https://www.apollopharmacy.in/search-medicines/{q}"}, {"name": "Netmeds", "url": f"https://www.netmeds.com/catalogsearch/result?q={q}"}, {"name": "PharmEasy", "url": f"https://pharmeasy.in/search/all?name={q}"}]
