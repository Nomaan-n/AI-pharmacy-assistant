#!/usr/bin/env python3
"""
Prioritize 3-character Instagram username candidates for manual verification.

No requests are made to Instagram. The script only scores candidate strings
locally and creates manageable verification batches.
"""

import csv
import re
from pathlib import Path

INPUT = Path("instagram_username_candidates.csv")
OUTPUT = Path("instagram_username_prioritized.csv")
BATCH_DIR = Path("instagram_username_batches")
BATCH_SIZE = 100

VOWELS = set("aeiou")
COMMON = set("abcdefghijklmnopqrstuvwxyz")

def score(username: str) -> int:
    s = username.lower()
    score = 0

    # Prefer visually clean letter combinations.
    if s.isalpha():
        score += 30
        if not any(c in VOWELS for c in s):
            score += 8
        if sum(c in VOWELS for c in s) == 1:
            score += 10
        if len(set(s)) == 3:
            score += 8

    # Prefer compact letter/number patterns that are easy to remember.
    if re.fullmatch(r"[a-z][0-9][a-z]", s):
        score += 24
    elif re.fullmatch(r"[a-z]{2}[0-9]", s):
        score += 18
    elif re.fullmatch(r"[a-z][0-9]{2}", s):
        score += 12

    # Avoid visually noisy repeated characters.
    if len(set(s)) == 1:
        score -= 25
    if s[0] == s[1] or s[1] == s[2]:
        score -= 6

    # Penalize hard-to-read digit-heavy combinations.
    if sum(c.isdigit() for c in s) == 3:
        score -= 18

    # Favor characters that are generally easy to distinguish.
    if not any(c in "il1o0" for c in s):
        score += 3

    return score

with INPUT.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for row in rows:
    row["score"] = score(row["username"])

rows.sort(key=lambda r: (-int(r["score"]), r["username"]))

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["username", "type", "status", "score"])
    w.writeheader()
    w.writerows(rows)

BATCH_DIR.mkdir(exist_ok=True)
for old in BATCH_DIR.glob("batch_*.csv"):
    old.unlink()

for start in range(0, len(rows), BATCH_SIZE):
    batch = rows[start:start + BATCH_SIZE]
    n = start // BATCH_SIZE + 1
    path = BATCH_DIR / f"batch_{n:04d}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["username", "type", "status", "score"])
        w.writeheader()
        w.writerows(batch)

print(f"Prioritized {len(rows):,} candidates.")
print(f"Created {(len(rows) + BATCH_SIZE - 1) // BATCH_SIZE:,} batches of up to {BATCH_SIZE}.")
print("No network requests were made.")
