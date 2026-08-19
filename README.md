# AI Pharmacy Assistant

A lightweight medication information and safety assistant with browser-based medicine/prescription image scanning.

## Features

- Mobile-friendly medication search
- Curated medication information
- Broad medication lookup architecture
- Camera capture using the device camera
- Photo upload for medicine packages and prescriptions
- Browser OCR using Tesseract.js
- Candidate medicine matching against the app database
- FastAPI API and health endpoint

## Scanner

Open `/static/scan.html` from the running app. On a phone, **Open camera** requests the rear camera where supported. A photo can also be uploaded from the gallery.

The scanner performs OCR locally in the browser. Handwritten prescriptions can be difficult to read and OCR can make dangerous errors, so extracted medicine names and doses must be confirmed by a pharmacist or prescriber. The scanner is not a prescription validator and does not authorize dispensing.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` and the scanner at `http://127.0.0.1:8000/static/scan.html`.
