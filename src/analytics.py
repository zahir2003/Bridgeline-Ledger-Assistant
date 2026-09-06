"""Deterministic ledger calculations.

The language model must not perform these calculations. This module does.
"""

from __future__ import annotations

import pandas as pd

from .policy import (
    REPORTING_DATE,
    is_overdue,
    payment_delay_days,
    itc_reasons,
)


def vendor_total(df: pd.DataFrame, vendor_key: str) -> float:
    """Total FY payable/spend for one normalized vendor key, including credit notes."""
    rows = df[df["vendor_key"].eq(vendor_key)]
    return float(rows["line_total_inr"].sum())


def overdue_invoices(df: pd.DataFrame) -> pd.DataFrame:
    """Return invoices overdue as of 31 March 2025."""
    mask = (~df["is_credit_note"]) & df.apply(
        lambda row: is_overdue(row, REPORTING_DATE), axis=1
    )
    return df[mask].copy()


def vendor_spend(df: pd.DataFrame) -> pd.DataFrame:
    """Rank vendors by FY spend/payable amount."""
    result = (
        df.groupby("vendor_key", dropna=False)
        .agg(
            total_inr=("line_total_inr", "sum"),
            invoice_count=("invoice_no", "count"),
        )
        .sort_values("total_inr", ascending=False)
        .reset_index()
    )
    return result


def invoices_above_taxable(df: pd.DataFrame, threshold=500_000) -> pd.DataFrame:
    """Invoices with taxable amount above the supplied threshold."""
    return df[
        (~df["is_credit_note"])
        & df["taxable_amount"].notna()
        & (df["taxable_amount"] > threshold)
    ].copy()


def q3_gst(df: pd.DataFrame) -> float:
    """Recorded GST charged for Q3: 1 Oct–31 Dec 2024."""
    mask = (
        df["invoice_date"].between("2024-10-01", "2024-12-31")
        & ~df["is_credit_note"]
    )
    return float(df.loc[mask, "gst_amount"].sum())


def itc_exceptions(df: pd.DataFrame) -> pd.DataFrame:
    """Invoices with policy-supported reasons for ITC non-claimability."""
    rows = []

    for _, row in df[~df["is_credit_note"]].iterrows():
        reasons = itc_reasons(row)
        if reasons:
            rows.append(
                {
                    "source_row": row["source_row"],
                    "invoice_no": row["invoice_no"],
                    "vendor_name": row["vendor_name_original"],
                    "reasons": reasons,
                }
            )

    return pd.DataFrame(rows)


def average_fabrication_payment_delay(df: pd.DataFrame) -> float:
    """Average payment delay for paid Fabrication invoices with payment dates."""
    fabrication = df[
        (df["category"] == "Fabrication")
        & ~df["is_credit_note"]
        & df["payment_date"].notna()
    ].copy()

    delays = fabrication.apply(payment_delay_days, axis=1).dropna()
    return float(delays.mean())


def data_quality_report(df: pd.DataFrame) -> dict:
    """Return policy-defined data-quality exceptions for later Q8 work."""
    return {
        "future_invoice_dates": df[df["future_invoice_date"]].copy(),
        "payment_before_invoice": df[df["payment_before_invoice"]].copy(),
        "missing_taxable_amount": df[df["missing_taxable_amount"]].copy(),
        "missing_gstin": df[df["missing_gstin"]].copy(),
        "gst_reconciliation_exceptions": df[
            df["gst_reconciliation_exception"]
        ].copy(),
        "duplicate_invoice_numbers": df[
            df["is_duplicate_invoice"]
        ].copy(),
    }
