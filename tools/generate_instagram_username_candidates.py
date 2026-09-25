#!/usr/bin/env python3
"""
Generate a complete 3-character username candidate list and a manual
verification queue.

This tool does NOT automate requests to Instagram.
"""

from itertools import product
from pathlib import Path
import csv

LETTERS = "abcdefghijklmnopqrstuvwxyz"
CHARS = LETTERS + "0123456789"

OUT = Path("instagram_username_candidates.csv")

rows = []
for p in product(LETTERS, repeat=3):
    rows.append(("".join(p), "letters-only", "unverified"))

for p in product(CHARS, repeat=3):
    s = "".join(p)
    # Avoid duplicating the letters-only section.
    if s not in {r[0] for r in rows}:
        rows.append((s, "letters+numbers", "unverified"))

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["username", "type", "status"])
    w.writerows(rows)

print(f"Wrote {len(rows):,} candidates to {OUT}")
