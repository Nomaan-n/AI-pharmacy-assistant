import io, re
from PIL import Image
import pytesseract

MAX_BYTES=8*1024*1024

def ocr_image(data: bytes):
    if len(data)>MAX_BYTES: raise ValueError("Image exceeds 8 MB limit")
    try:
        img=Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        raise ValueError("Unsupported or invalid image") from e
    text=pytesseract.image_to_string(img)
    return {"text":text.strip(),"status":"ocr_only","verified":False}

def parse_prescription(text):
    lines=[re.sub(r"\s+"," ",x).strip() for x in text.splitlines() if x.strip()]
    meds=[]
    patterns=[re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9+\- ]{2,60}?)\s+(?P<strength>\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%|IU)\b)",re.I)]
    for line in lines:
        for p in patterns:
            m=p.search(line)
            if m:
                meds.append({"candidate_name":m.group("name").strip(" .,-"),"strength":m.group("strength"),"raw_line":line,"confidence":"candidate"})
                break
    return {"raw_text":text,"medications":meds,"verified":False,"notice":"OCR and parsing produce candidates only. A pharmacist or clinician must confirm uncertain handwriting, medicine identity, dose and directions."}
