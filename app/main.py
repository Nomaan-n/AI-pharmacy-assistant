from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import get_settings
from .grounding import DailyMedRetriever
from .llm import answer
from .safety import assess, DISCLAIMER, URGENT_DISCLAIMER
from .schemas import ChatRequest, ChatResponse, MedicationContext, Safety

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A safety-aware medication information assistant grounded in DailyMed labeling.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.allow_origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

retriever = DailyMedRetriever()
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
async def home():
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "llm_configured": bool(settings.openai_api_key)}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    level, flags = assess(request.question)
    grounded = await retriever.retrieve(request.question)
    answer_text, provider = await answer(request.question, grounded.context, level, flags)
    disclaimer = URGENT_DISCLAIMER if level == "urgent" else DISCLAIMER
    return ChatResponse(
        answer=answer_text,
        medication=MedicationContext(**grounded.medication),
        safety=Safety(level=level, flags=flags, disclaimer=disclaimer),
        sources=grounded.sources,
        grounded=grounded.grounded,
        provider=provider,
    )
