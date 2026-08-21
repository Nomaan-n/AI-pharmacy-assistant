from typing import Any

from openai import OpenAI

from .config import settings

SYSTEM_PROMPT = """You are a safety-focused medication information assistant.

Your job is to explain medication information clearly using only the supplied grounded medication context plus general high-level knowledge when needed.

Rules:
- Do not diagnose conditions.
- Do not claim to be a doctor or pharmacist.
- Do not tell a user to start, stop, or change a prescription treatment.
- Do not invent medication facts, interactions, doses, contraindications, or sources.
- If the supplied medication context does not contain the requested fact, say that the available source context does not establish it.
- Do not provide individualized dosing instructions.
- For emergencies, direct the user to immediate professional/emergency care.
- Distinguish general educational information from personalized medical advice.
- Keep answers concise and structured.
"""


def generate_answer(question: str, medication: dict[str, Any] | None, safety_note: str | None) -> tuple[str, str]:
    if not settings.openai_api_key:
        return fallback_answer(question, medication, safety_note), "local-grounded"

    client = OpenAI(api_key=settings.openai_api_key)
    context = medication or {"message": "No matching medication was found in the local grounded dataset."}
    prompt = f"Question: {question}\n\nGrounded medication context:\n{context}\n\nSafety note:\n{safety_note or 'None detected.'}"

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        answer = response.choices[0].message.content or "I could not generate a response."
        return answer, "openai"
    except Exception:
        return fallback_answer(question, medication, safety_note), "local-grounded-fallback"


def fallback_answer(question: str, medication: dict[str, Any] | None, safety_note: str | None) -> str:
    if not medication:
        return "I could not match that medication to the assistant's grounded medication dataset. I can provide general guidance, but I cannot safely verify a medicine-specific answer from the available sources."

    lines = [
        f"**{medication['generic_name']}** ({medication['class']})",
        "",
        "**Common uses:** " + "; ".join(medication["uses"]),
        "**Common side effects:** " + "; ".join(medication["common_side_effects"]),
        "**Important warnings:** " + "; ".join(medication["warnings"]),
    ]
    if safety_note:
        lines += ["", f"**Safety:** {safety_note}"]
    return "\n".join(lines)
