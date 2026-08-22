from .config import get_settings
import logging
import re

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a concise medication-information assistant. You are not a doctor, pharmacist, diagnostician, or emergency service.

Use only the supplied verified medication context for medication facts. The context may come from DailyMed/NLM or a verified Indian product reference. Treat the source type as authoritative only for the facts explicitly supplied.

OUTPUT RULES ARE STRICT:
- Answer only the user's actual question. Never summarize or reproduce the label.
- For a simple question such as "What does this medicine do?", respond in EXACTLY 2 short paragraphs, with no heading.
- Paragraph 1: say what the medicine is and, in plain language, what it does.
- Paragraph 2: give only the 2-4 most common general uses supported by the source.
- Keep the entire answer under 70 words.
- Do NOT mention individual bacteria, organisms, strains, beta-lactamase, exhaustive indications, H. pylori, triple therapy, detailed mechanisms, pharmacology, or other technical label details unless the user specifically asks about them.
- Do not include doses, contraindications, interactions, warnings, or treatment instructions unless the user specifically asks.
- Do not use Markdown tables.
- Do not add facts that are not supported by the supplied medication context.
- Never diagnose or give individualized treatment advice.
- Never tell a user to start, stop, increase, or decrease prescription treatment.
- If the source context is insufficient, say so instead of guessing.
- If the supplied context contains a "Verified use summary", use that summary directly for a simple "what does it do?" question. Do not refuse merely because a DailyMed label is unavailable.
- Write naturally for a phone screen.

IMPORTANT: For a simple "What does it do?" question, do not turn the answer into a mini drug monograph. The user wants a quick explanation, not the full label.
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
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        user_prompt = (
            f"Question: {question}\n"
            f"Safety level: {safety_level}\n"
            f"Safety flags: {flags}\n\n"
            f"Grounded medication context:\n{context}"
        )
        response = await client.responses.create(
            model=settings.groq_model,
            input=f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\nUSER REQUEST:\n{user_prompt}",
        )
        text = getattr(response, "output_text", None)
        if text:
            compacted = compact_answer(text.strip(), question)
            # If the model ignores a verified product-use summary and claims it
            # has no information, use the deterministic summary instead.
            if re.search(r"\b(i (?:don't|do not) have|couldn['’]t find|no information|unable to provide)\b", compacted, re.I):
                deterministic = fallback_answer(context)
                if deterministic and not deterministic.startswith("I retrieved verified"):
                    return deterministic, "deterministic-product-summary"
            return compacted, "groq-responses"
    except Exception as exc:
        logger.exception(
            "Groq Responses API request failed (model=%s, error_type=%s)",
            settings.groq_model,
            type(exc).__name__,
        )
    return fallback_answer(context), "deterministic-fallback"


def compact_answer(text: str, question: str) -> str:
    text = re.sub(r"^\s*(answer|response)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    words = text.split()
    if len(words) <= 70:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    count = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        if not sentence_words:
            continue
        if count + len(sentence_words) > 70:
            break
        kept.append(sentence.strip())
        count += len(sentence_words)
        if count >= 35:
            break

    if kept:
        return " ".join(kept)

    return " ".join(words[:70]).rstrip(" ,;:") + "."


def fallback_answer(context: str) -> str:
    if not context or context.startswith("No specific"):
        return "I could not retrieve enough reliable medication information to answer safely. Please provide the exact medicine name."

    match = re.search(r"Verified use summary:\s*(.+?)(?:\s+This identifies the medicine product|$)", context, flags=re.IGNORECASE)
    if match:
        summary = match.group(1).strip()
        return summary

    return "I retrieved verified medication information, but the explanation service is temporarily unavailable. Please open the cited source for the authoritative details."
