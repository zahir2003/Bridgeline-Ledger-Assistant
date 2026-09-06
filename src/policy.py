"""Business rules taken directly from vendor_payment_policy.md."""

from __future__ import annotations

from datetime import date

REPORTING_DATE = date(2025, 3, 31)
FY_START = date(2024, 4, 1)
FY_END = date(2025, 3, 31)
USD_TO_INR = 83.50

PAYMENT_TERMS_DAYS = {
    "Raw Material": 30,
    "Fabrication": 45,
    "Transport": 15,
    "Consumables": 30,
    "Tooling": 30,
    "Safety": 30,
    "Services": 45,
}


def payment_term_days(category: str) -> int:
    """Return the policy payment term for a procurement category."""
    try:
        return PAYMENT_TERMS_DAYS[category]
    except KeyError as exc:
        raise ValueError(f"Unknown procurement category: {category!r}") from exc


def due_date(invoice_date, category):
    """Invoice date + standard category term."""
    return invoice_date + __import__("pandas").Timedelta(
        days=payment_term_days(category)
    )


def is_overdue(row, reporting_date=REPORTING_DATE) -> bool:
    """Apply the policy definition of overdue as of a reporting date."""
    if row["is_credit_note"]:
        return False

    invoice_date = row["invoice_date"]
    if invoice_date is None or __import__("pandas").isna(invoice_date):
        return False

    due = due_date(invoice_date, row["category"])

    # Unpaid as of reporting date means no payment date or payment after it.
    unpaid_as_of_date = (
        __import__("pandas").isna(row["payment_date"])
        or row["payment_date"].date() > reporting_date
    )

    return unpaid_as_of_date and reporting_date > due.date()


def payment_delay_days(row) -> int | None:
    """Payment date - invoice date - standard term, preserving negatives."""
    import pandas as pd

    if row["is_credit_note"] or pd.isna(row["payment_date"]) or pd.isna(row["invoice_date"]):
        return None

    return (
        row["payment_date"] - row["invoice_date"]
    ).days - payment_term_days(row["category"])


def itc_reasons(row) -> list[str]:
    """Return policy-supported reasons an invoice cannot be claimed for ITC."""
    import pandas as pd

    reasons = []

    if pd.isna(row["vendor_gstin"]):
        reasons.append("Supplier GSTIN is missing.")

    if row.get("gst_reconciliation_exception", False):
        reasons.append(
            "Recorded GST does not reconcile with taxable amount × stated GST rate within ₹1."
        )

    return reasons
