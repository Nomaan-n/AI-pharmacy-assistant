from .config import get_settings

SYSTEM_PROMPT = """You are a medication-information assistant. You are not a doctor, pharmacist, diagnostician, or emergency service.

Rules:
- Use only the supplied DailyMed/NLM context for medication facts.
- Never invent drug facts, contraindications, interactions, doses, or citations.
- Do not diagnose.
- Never tell a user to start, stop, increase, or decrease prescription treatment.
- Never provide individualized dosing instructions.
- For urgent or treatment-change requests, prioritize appropriate professional care.
- Clearly distinguish supported information from unknown information.
- If the source context is insufficient, say so instead of guessing.
- Keep answers concise and structured.
"""

async def answer(question: str, context: str, safety_level: str, flags: list[str]) -> tuple[str, str]:
    settings = get_settings()

    # Safety-critical requests should never depend on an LLM being available.
    if safety_level == "urgent":
        return (
            "This may be an urgent medical situation. Seek prompt professional or emergency care rather than relying on this app.",
            "deterministic-safety",
        )
    if "treatment_change_request" in flags:
        return (
            "Do not stop, start, or change a prescribed medicine based only on this app. Contact the prescriber or pharmacist who knows the treatment and your medical history. If you have severe symptoms or signs of serious bleeding, seek urgent medical care.",
            "deterministic-safety",
        )

    if not settings.openai_api_key:
        return fallback_answer(context), "deterministic-fallback"

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        user_prompt = f"Question: {question}\nSafety level: {safety_level}\nSafety flags: {flags}\n\nGrounded DailyMed/NLM context:\n{context}"
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip(), "openai-responses"
    except Exception:
        pass
    return fallback_answer(context), "deterministic-fallback"

def fallback_answer(context: str) -> str:
    if not context or context.startswith("No DailyMed") or context.startswith("Live DailyMed") or context.startswith("No specific"):
        return "I could not retrieve enough reliable medication-label information to answer safely. Please provide the exact medicine name or consult a pharmacist or clinician."
    return "I retrieved relevant DailyMed/NLM label information. The AI explanation service is not configured, so I will not paraphrase the source and risk adding unsupported claims. Please open the cited label for the authoritative details."
