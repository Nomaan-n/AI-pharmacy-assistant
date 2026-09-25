# 3-character username candidate generator

Generates all 3-character candidates using:
- a-z only
- a-z plus 0-9

It deliberately does not automate Instagram requests. The CSV is a queue for
manual verification in Instagram, where final username availability is decided.

Run:

    python tools/generate_instagram_username_candidates.py

Output:

    instagram_username_candidates.csv
