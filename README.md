# AI Pharmacy Assistant

A lightweight, mobile-friendly pharmacy information demo built with FastAPI.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Features

- Mobile-friendly browser interface
- Medicine search
- Common medication information
- Safety notes and practical tips
- JSON API
- Health endpoint

## API

`GET /health`  
`GET /api/medicines`  
`GET /api/medicine/{medicine_name}`  
`GET /api/search?q={query}`

## Safety

This is an educational demo, not a diagnostic or prescribing system. Medication decisions should be checked with a qualified healthcare professional.