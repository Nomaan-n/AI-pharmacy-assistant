from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import settings
from .llm import generate_answer
from .medications import find_medication
from .safety import safety_flags, safety_message

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND = BASE_DIR / "frontend" / "index.html"

app = FastAPI(
    title="AI Pharmacy Assistant",
    description="Safety-focused medication information API with grounded medication context and optional LLM assistance.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    medication: dict | None
    safety: dict
    source: dict | None
    provider: str


@app.get("/", include_in_schema=False)
def frontend():
    if not FRONTEND.exists():
        return {"name": "AI Pharmacy Assistant", "docs": "/docs"}
    return FileResponse(FRONTEND)


@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": bool(settings.openai_api_key)}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    medication = find_medication(question)
    flags = safety_flags(question)
    note = safety_message(flags)
    answer, provider = generate_answer(question, medication, note)

    source = None
    if medication:
        source = {"name": medication["source"], "url": medication["source_url"]}

    public_medication = None
    if medication:
        public_medication = {
            "generic_name": medication["generic_name"],
            "class": medication["class"],
        }

    return ChatResponse(
        answer=answer,
        medication=public_medication,
        safety={**flags, "message": note},
        source=source,
        provider=provider,
    )
