from __future__ import annotations

import csv
import os
import sqlite3
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv"
SUPPLEMENT_PATH = Path("data/verified_india_additions.csv")
OUT = os.environ.get("INDIA_DRUG_INDEX", "data/india_medicines.sqlite3")
TMP = "/tmp/indian_medicine_data.csv"


def norm(value: str | None) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def insert_row(db: sqlite3.Connection, row: dict[str, str], source: str) -> bool:
    name = str(row.get("name", "")).strip()
    if not name:
        return False
    c1 = str(row.get("short_composition1", "")).strip()
    c2 = str(row.get("short_composition2", "")).strip()
    manufacturer = str(row.get("manufacturer_name", "")).strip()
    name_norm = norm(name)
    composition = " + ".join(x for x in (c1, c2) if x)

    # Prevent a supplemental record from duplicating an existing upstream product.
    exists = db.execute(
        "SELECT 1 FROM medicines WHERE name_norm=? AND manufacturer=? AND composition_norm=? LIMIT 1",
        (name_norm, manufacturer, norm(composition)),
    ).fetchone()
    if exists:
        return False

    db.execute(
        "INSERT INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            str(row.get("id", "")).strip(),
            name,
            name_norm,
            str(row.get("price(₹)", "")).strip(),
            manufacturer,
            str(row.get("type", "")).strip(),
            str(row.get("pack_size_label", "")).strip(),
            c1,
            c2,
            norm(composition),
            str(row.get("Is_discontinued", "FALSE")).strip().upper(),
        ),
    )
    return True


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("Downloading current Indian medicine dataset...")
    urllib.request.urlretrieve(SOURCE_URL, TMP)

    if os.path.exists(OUT):
        os.remove(OUT)
    db = sqlite3.connect(OUT)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """
        CREATE TABLE medicines (
            id TEXT,
            name TEXT NOT NULL,
            name_norm TEXT NOT NULL,
            price TEXT,
            manufacturer TEXT,
            medicine_type TEXT,
            pack_size TEXT,
            composition1 TEXT,
            composition2 TEXT,
            composition_norm TEXT NOT NULL,
            discontinued TEXT
        )
        """
    )
    db.execute("CREATE INDEX idx_name_norm ON medicines(name_norm)")
    db.execute("CREATE INDEX idx_composition_norm ON medicines(composition_norm)")
    db.execute("CREATE INDEX idx_manufacturer ON medicines(manufacturer)")

    inserted = 0
    skipped = 0
    with open(TMP, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # The upstream source explicitly marks discontinued products.
            discontinued = str(row.get("Is_discontinued", "")).strip().upper()
            if discontinued in {"TRUE", "1", "YES", "Y"}:
                skipped += 1
                continue
            if insert_row(db, row, "upstream"):
                inserted += 1
            if inserted % 5000 == 0 and inserted:
                db.commit()

    supplement_added = 0
    supplement_skipped_discontinued = 0
    supplement_missing = 0
    if SUPPLEMENT_PATH.exists():
        with SUPPLEMENT_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                discontinued = str(row.get("Is_discontinued", "FALSE")).strip().upper()
                if discontinued in {"TRUE", "1", "YES", "Y"}:
                    supplement_skipped_discontinued += 1
                    continue
                if not str(row.get("name", "")).strip():
                    supplement_missing += 1
                    continue
                if insert_row(db, row, "verified_supplement"):
                    supplement_added += 1

    db.commit()
    db.execute("ANALYZE")
    db.commit()
    total = db.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    db.close()
    print(
        f"Built {OUT}: {total} active products; excluded {skipped} upstream discontinued records; "
        f"added {supplement_added} verified supplemental products; "
        f"skipped {supplement_skipped_discontinued} discontinued supplemental records."
    )


if __name__ == "__main__":
    main()
