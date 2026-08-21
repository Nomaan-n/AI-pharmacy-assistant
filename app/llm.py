import json
from .config import get_settings

SYSTEM_PROMPT = """You are a medication-information assistant. You are not a doctor, pharmacist, diagnostician, or emergency service.

Rules:
- Answer only from the supplied grounded medication context when it is relevant.
- Never invent drug facts, contraindications, interactions, doses, or citations.
- Do not diagnose.
- Do not tell a user to start, stop, increase, or decrease prescription treatment.
- Do not provide individualized dosing instructions.
- For urgent safety flags, prioritize immediate professional/emergency care over explanation.
- Clearly distinguish what the source supports from what is unknown.
- Keep answers concise, structured, and understandable.
- If the supplied source does not contain enough information, say so.
"""

async def answer(question: str, context: str, safety_level: str, flags: list[str]) -> tuple[str, str]:
    settings = get_settings()
    if not settings.openai_api_key:
        return fallback_answer(question, context, safety_level, flags), "deterministic-fallback"
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        user_prompt = f"Question: {question}\nSafety level: {safety_level}\nSafety flags: {flags}\n\nGrounded source context:\n{context}"
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
    return fallback_answer(question, context, safety_level, flags), "deterministic-fallback"

def fallback_answer(question: str, context: str, safety_level: str, flags: list[str]) -> str:
    if safety_level == "urgent":
        return "This question may involve an urgent medical situation. Seek prompt professional or emergency care rather than relying on this app."
    if not context or context.startswith("No DailyMed") or context.startswith("Live DailyMed"):
        return "I could not retrieve a reliable medication label for this question. I do not want to guess. Please provide the exact medicine name or consult a pharmacist or clinician."
    return "I found relevant information in the medication label, but the AI explanation service is not configured. Please review the cited DailyMed label for the authoritative details."
