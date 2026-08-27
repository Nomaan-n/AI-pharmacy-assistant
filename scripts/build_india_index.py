from __future__ import annotations

import csv
import os
import sqlite3
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv"
OUT = os.environ.get("INDIA_DRUG_INDEX", "data/india_medicines.sqlite3")
TMP = "/tmp/indian_medicine_data.csv"


def norm(value: str | None) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("Downloading current Indian medicine dataset...")
    urllib.request.urlretrieve(SOURCE_URL, TMP)

    if os.path.exists(OUT):
        os.remove(OUT)
    db = sqlite3.connect(OUT)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
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
    """)
    db.execute("CREATE INDEX idx_name_norm ON medicines(name_norm)")
    db.execute("CREATE INDEX idx_composition_norm ON medicines(composition_norm)")
    db.execute("CREATE INDEX idx_manufacturer ON medicines(manufacturer)")

    inserted = 0
    skipped = 0
    with open(TMP, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # The source explicitly marks discontinued products. Keep active products only.
            discontinued = str(row.get("Is_discontinued", "")).strip().upper()
            if discontinued in {"TRUE", "1", "YES", "Y"}:
                skipped += 1
                continue
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            c1 = str(row.get("short_composition1", "")).strip()
            c2 = str(row.get("short_composition2", "")).strip()
            composition = " + ".join(x for x in (c1, c2) if x)
            db.execute(
                "INSERT INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(row.get("id", "")), name, norm(name), str(row.get("price(₹)", "")).strip(),
                    str(row.get("manufacturer_name", "")).strip(), str(row.get("type", "")).strip(),
                    str(row.get("pack_size_label", "")).strip(), c1, c2, norm(composition), discontinued,
                ),
            )
            inserted += 1
            if inserted % 5000 == 0:
                db.commit()
    db.commit()
    db.execute("ANALYZE")
    db.commit()
    db.close()
    print(f"Built {OUT}: {inserted} active medicines; excluded {skipped} discontinued records.")


if __name__ == "__main__":
    main()
