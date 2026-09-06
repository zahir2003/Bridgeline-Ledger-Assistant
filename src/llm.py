"""Local Ollama integration."""

import os
import json
import ollama

MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_HOST = "http://127.0.0.1:11434"

client = ollama.Client(host=OLLAMA_HOST)


def ask_ollama(prompt: str) -> str:
    """Send a prompt to the local Ollama model."""
    response = client.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response["message"]["content"]


def classify_question(question: str) -> dict:
    """
    Use Ollama to identify the supported ledger intent.

    Ollama only understands the question.
    Python performs all financial calculations.
    """

    prompt = f"""
You are a question classifier for a financial ledger assistant.

Classify the user's question into exactly ONE of these intents:

- bharat_total
- overdue_invoices
- highest_spend_vendor
- taxable_above_5l
- q3_gst
- itc_exceptions
- fabrication_delay
- data_quality
- unknown

Return ONLY valid JSON.

Example:
{{"intent": "bharat_total"}}

User question:
{question}
"""

    try:
        response = ask_ollama(prompt)
        return json.loads(response)
    except Exception:
        return {"intent": "unknown"}


def generate_answer(question: str, result: str) -> str:
    """
    Turn the deterministic Python result into a natural-language answer.

    Ollama must not calculate, modify, or invent any numbers.
    """

    prompt = f"""
You are a financial ledger assistant.

Answer the user's question using ONLY the Python result below.

Rules:
- Do not recalculate anything.
- Do not change any numbers.
- Do not invent information.
- Do not add facts that are not in the Python result.
- Keep the answer concise and clear.
- Preserve source rows exactly.
- If a value is negative, explain its meaning instead of changing it.
- Return only the answer, without saying "Python result".

User question:
{question}

Python result:
{result}
"""

    try:
        return ask_ollama(prompt)
    except Exception:
        return result
