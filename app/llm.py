from .config import get_settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a concise medication-information assistant. You are not a doctor, pharmacist, diagnostician, or emergency service.

Rules:
- Use only the supplied DailyMed/NLM context for medication facts.
- Answer the user's actual question directly. Do not dump the entire label into the answer.
- For simple questions such as "What does this medicine do?" or "What is it used for?", give a short plain-language explanation of the main uses only.
- Prefer 1 short paragraph or 2-4 simple bullet points. Keep routine medication explanations under about 120 words unless the user asks for detail.
- Do not use Markdown tables. Do not list every organism, indication, formulation detail, or label section unless the user specifically asks for it.
- Mention important qualifiers only when they materially change the meaning of the answer.
- Never invent drug facts, contraindications, interactions, doses, or citations.
- Do not diagnose.
- Never tell a user to start, stop, increase, or decrease prescription treatment.
- Never provide individualized dosing instructions.
- For urgent or treatment-change requests, prioritize appropriate professional care.
- Clearly distinguish supported information from unknown information.
- If the source context is insufficient, say so instead of guessing.
- End with a brief safety reminder only when useful, not a long disclaimer.
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

    if not settings.groq_api_key:
        return fallback_answer(context), "deterministic-fallback"

    try:
        # Groq exposes an OpenAI-compatible Responses API, so the existing
        # OpenAI client dependency can be reused without adding a new SDK.
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        user_prompt = (
            f"Question: {question}\n"
            f"Safety level: {safety_level}\n"
            f"Safety flags: {flags}\n\n"
            f"Grounded DailyMed/NLM context:\n{context}"
        )
        response = await client.responses.create(
            model=settings.groq_model,
            input=f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\nUSER REQUEST:\n{user_prompt}",
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip(), "groq-responses"
    except Exception as exc:
        # Keep the public response safe, but do not hide the actual provider
        # failure from operators. Never log the API key or request contents.
        logger.exception(
            "Groq Responses API request failed (model=%s, error_type=%s)",
            settings.groq_model,
            type(exc).__name__,
        )
    return fallback_answer(context), "deterministic-fallback"

def fallback_answer(context: str) -> str:
    if not context or context.startswith("No DailyMed") or context.startswith("Live DailyMed") or context.startswith("No specific"):
        return "I could not retrieve enough reliable medication-label information to answer safely. Please provide the exact medicine name or consult a pharmacist or clinician."
    return "I retrieved relevant DailyMed/NLM label information, but the AI explanation service is temporarily unavailable. Please open the cited label for the authoritative details."
