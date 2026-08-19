# AI Pharmacy Assistant

A simple, mobile-first medication information assistant. It combines a curated educational dataset with live **NIH RxNorm** medication-concept lookup, so it is not limited to a tiny hard-coded list.

## What it does

- Search common medicines
- Search the broader RxNorm medication vocabulary
- Show common uses and high-level safety notes for curated medicines
- Return RxCUI identifiers for live medication concepts
- Provide a clean browser UI and JSON API
- Work well on phones and desktop

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## API

- `GET /health`
- `GET /api/medicines`
- `GET /api/medicine/{medicine_name}`
- `GET /api/search?q={query}`

## Important safety boundary

This is an educational information tool, not a diagnostic or prescribing system. It should not invent doses, diagnose illness, or replace a pharmacist or clinician. Individual dosing, interactions, pregnancy, paediatric use, allergies, contraindications, and emergencies require appropriate professional or authoritative label guidance.

## Data

Medication concept lookup uses the public NIH RxNorm API. RxNorm is useful for broad medication vocabulary and identifiers, but a production clinical product should pair it with authoritative labeling and clinical decision support rather than treating a medication name alone as sufficient safety advice.
