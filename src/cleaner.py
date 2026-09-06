"""Cleaning and normalization for the raw Bridgeline ledger."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def parse_money(value):
    """Convert messy money strings such as 'Rs. 12,345.60' to float."""
    if pd.isna(value) or str(value).strip() == "":
        return float("nan")

    text = str(value).strip()
    text = text.replace(",", "").replace("Rs.", "").replace("₹", "")
    text = re.sub(r"\s+", "", text)

    try:
        return float(text)
    except ValueError:
        return float("nan")


def parse_date(value):
    """Parse the date formats present in the supplied ledger.

    ISO dates are handled explicitly so day/month ordering is never guessed.
    """
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT

    text = str(value).strip()

    explicit_formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
    )

    for fmt in explicit_formats:
        try:
            return pd.to_datetime(text, format=fmt)
        except (TypeError, ValueError):
            pass

    # Final fallback for any unexpected textual date.
    return pd.to_datetime(text, dayfirst=True, errors="coerce")


def normalize_vendor_name(name):
    """Create a conservative fallback vendor key.

    GSTIN is preferred for identity when available. This key is only used
    when GSTIN is missing; the original vendor name is never overwritten.
    """
    if pd.isna(name):
        return ""

    text = str(name).upper().strip()
    text = re.sub(r"[.,]", " ", text)
    text = re.sub(r"\b(PVT|PRIVATE|LTD|LIMITED)\b", " ", text)
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_ledger(csv_path: str | Path) -> pd.DataFrame:
    """Load and normalize the raw ledger without changing source data."""
    df = pd.read_csv(csv_path, dtype=str)
    df.insert(0, "source_row", range(2, len(df) + 2))  # CSV header is row 1.

    df["invoice_date"] = df["invoice_date"].map(parse_date)
    df["payment_date"] = df["payment_date"].map(parse_date)

    for column in ["quantity", "unit_rate", "taxable_amount", "gst_amount"]:
        df[column] = df[column].map(parse_money)

    df["gst_rate"] = (
        df["gst_rate"]
        .str.replace("%", "", regex=False)
        .str.strip()
        .astype(float)
    )

    df["currency"] = df["currency"].str.strip().str.upper()
    df["payment_status"] = df["payment_status"].str.strip().str.title()
    df["vendor_gstin"] = df["vendor_gstin"].replace(r"^\s*$", pd.NA, regex=True)

    df["vendor_name_original"] = df["vendor_name"]
    df["vendor_name_normalized"] = df["vendor_name"].map(normalize_vendor_name)

    # GSTIN is the strongest supplier identity available in this dataset.
    df["vendor_key"] = df["vendor_gstin"].fillna(
        "NAME:" + df["vendor_name_normalized"]
    )

    df["is_credit_note"] = df["invoice_no"].str.upper().str.startswith("CN-")
    df["is_duplicate_invoice"] = df["invoice_no"].duplicated(
        keep=False
    )

    # Policy: later/revised entry supersedes earlier duplicate.
    df["is_superseded_duplicate"] = False
    for _, group in df.groupby("invoice_no", sort=False):
        if len(group) > 1:
            df.loc[group.index[:-1], "is_superseded_duplicate"] = True

    df["in_scope_fy_2024_25"] = (
        df["invoice_date"].between("2024-04-01", "2025-03-31")
    )

    # Convert line total to INR. Credit notes remain negative.
    df["line_total"] = df["taxable_amount"] + df["gst_amount"]
    df["line_total_inr"] = df["line_total"]
    usd_mask = df["currency"].eq("USD")
    df.loc[usd_mask, "line_total_inr"] = df.loc[usd_mask, "line_total"] * 83.50

    # Helpful data-quality fields. We surface these; we do not silently fix them.
    df["missing_taxable_amount"] = df["taxable_amount"].isna()
    df["missing_gst_amount"] = df["gst_amount"].isna()
    df["missing_gstin"] = df["vendor_gstin"].isna()
    df["future_invoice_date"] = df["invoice_date"] > pd.Timestamp("2025-03-31")
    df["payment_before_invoice"] = (
        df["payment_date"].notna()
        & df["invoice_date"].notna()
        & (df["payment_date"] < df["invoice_date"])
    )

    expected_gst = df["taxable_amount"] * df["gst_rate"] / 100
    df["expected_gst"] = expected_gst
    df["gst_difference"] = (expected_gst - df["gst_amount"]).abs()
    df["gst_reconciliation_exception"] = (
        df["taxable_amount"].notna()
        & df["gst_amount"].notna()
        & (df["gst_difference"] > 1)
    )

    df = add_vendor_spelling_flags(df)
    return df


def analysis_ledger(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows eligible for FY analytics after policy exclusions."""
    return df[
        df["in_scope_fy_2024_25"]
        & ~df["is_superseded_duplicate"]
    ].copy()


def save_cleaned_ledger(
    df: pd.DataFrame,
    output_path: str | Path
) -> None:
    """Save the cleaned ledger as a derived CSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)


def add_vendor_spelling_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect vendors that appear under different names.

    GSTIN is used as the supplier identity when available.
    The original vendor names are preserved.
    """

    df = df.copy()

    df["vendor_name_variant_count"] = 1
    df["vendor_name_variation"] = False

    # Only reliable when GSTIN is available.
    gstin_groups = (
        df[df["vendor_gstin"].notna()]
        .groupby("vendor_gstin")["vendor_name_original"]
        .transform("nunique")
    )

    mask = df["vendor_gstin"].notna()

    df.loc[mask, "vendor_name_variant_count"] = gstin_groups[mask]
    df.loc[mask, "vendor_name_variation"] = gstin_groups[mask] > 1

    return df


def save_cleaned_ledger(df: pd.DataFrame, output_path: str | Path) -> None:
    """Save the cleaned ledger as a derived CSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
