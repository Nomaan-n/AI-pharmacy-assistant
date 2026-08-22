from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import get_settings
from .grounding import DailyMedRetriever
from .llm import answer
from .safety import assess, DISCLAIMER, URGENT_DISCLAIMER
from .schemas import ChatRequest, ChatResponse, MedicationContext, Safety
from .india_drugs import IndiaDrugRegistry

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A safety-aware medication information assistant grounded in DailyMed labeling and Indian drug identification data.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.allow_origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

retriever = DailyMedRetriever()
india_registry = IndiaDrugRegistry()
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
async def home():
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "llm_configured": bool(settings.groq_api_key), "india_registry": True}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    level, flags = assess(request.question)
    grounded = await retriever.retrieve(request.question)
    answer_text, provider = await answer(request.question, grounded.context, level, flags)
    medication = dict(grounded.medication)

    original_brand = medication.get("india_brand_name")
    composition = medication.get("india_generic_name") or medication.get("generic_name")
    india_alternatives = await india_registry.same_composition_brands(
        str(composition) if composition else None,
        exclude_brand=str(original_brand) if original_brand else None,
    )

    purchase_name = original_brand or medication.get("name") or request.question
    medication["india_alternatives"] = india_alternatives
    medication["purchase_links"] = IndiaDrugRegistry.purchase_links(str(purchase_name))

    disclaimer = URGENT_DISCLAIMER if level == "urgent" else DISCLAIMER
    return ChatResponse(
        answer=answer_text,
        medication=MedicationContext(**medication),
        safety=Safety(level=level, flags=flags, disclaimer=disclaimer),
        sources=grounded.sources,
        grounded=grounded.grounded,
        provider=provider,
    )
