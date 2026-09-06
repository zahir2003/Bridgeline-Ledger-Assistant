"""Convert natural-language questions into supported ledger intents."""


def route_question(question: str) -> str | None:
    """Return the intent for a user question."""

    text = question.lower().strip()

    # Q1
    if "bharat" in text and ("total" in text or "payable" in text or "amount" in text):
        return "bharat_total"

    # Q2
    if "overdue" in text:
        return "overdue_invoices"

    # Q3
    if "highest" in text and ("spend" in text or "vendor" in text):
        return "highest_spend_vendor"

    # Q4
    if (
        "5 lakh" in text or "500000" in text or "5,00,000" in text
    ) and "taxable" in text:
        return "taxable_above_5l"

    # Q5
    if "gst" in text and (
        "q3" in text or "october" in text or "november" in text or "december" in text
    ):
        return "q3_gst"

    # Q6
    if "itc" in text or "input tax credit" in text:
        return "itc_exceptions"

    # Q7
    if "fabrication" in text and (
        "delay" in text or "payment" in text or "average" in text
    ):
        return "fabrication_delay"

    # Q8
    if (
        "duplicate" in text
        or "suspicious" in text
        or "unreliable" in text
        or "data quality" in text
        or "data-quality" in text
        or "anomal" in text
    ):
        return "data_quality"

    return None
