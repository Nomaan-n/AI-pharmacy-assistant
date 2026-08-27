#!/usr/bin/env python3
"""Build an active-only Indian medicine catalog from the upstream dataset."""
from __future__ import annotations
import csv
import gzip
import io
import json
import os
import urllib.request

SOURCE_URL = os.environ.get("MEDICINE_DATASET_URL", "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv")
OUTPUT = "data/active_indian_medicines.jsonl.gz"

def main() -> None:
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        raw = response.read()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    rows = []
    for row in reader:
        if str(row.get("Is_discontinued", "")).strip().lower() not in {"false", "0", "no", "n"}:
            continue
        name = (row.get("name") or "").strip()
        if not name:
            continue
        rows.append({
            "id": row.get("id"),
            "name": name,
            "manufacturer": (row.get("manufacturer_name") or "").strip(),
            "type": (row.get("type") or "").strip(),
            "pack_size": (row.get("pack_size_label") or "").strip(),
            "composition_1": (row.get("short_composition1") or "").strip(),
            "composition_2": (row.get("short_composition2") or "").strip(),
            "price_inr": row.get("price(₹)"),
            "is_discontinued": False,
        })
    rows.sort(key=lambda item: (item["name"].casefold(), item.get("manufacturer", "").casefold()))
    os.makedirs("data", exist_ok=True)
    with gzip.open(OUTPUT, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    with open("data/active_medicine_catalog_meta.json", "w", encoding="utf-8") as handle:
        json.dump({"source": SOURCE_URL, "active_count": len(rows), "discontinued_excluded": True}, handle, indent=2)
    print(f"Wrote {len(rows)} active medicines to {OUTPUT}")

if __name__ == "__main__":
    main()
