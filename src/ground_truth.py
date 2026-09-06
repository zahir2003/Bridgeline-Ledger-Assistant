"""Generate the ground-truth answers for the eight assignment questions.

Run from the project root:
    python -m src.ground_truth

The calculations are deterministic and do not use an LLM.
"""

from __future__ import annotations

import pandas as pd

from .analytics import (
    average_fabrication_payment_delay,
    data_quality_report,
    invoices_above_taxable,
    itc_exceptions,
    overdue_invoices,
    q3_gst,
    vendor_spend,
)
from .cleaner import analysis_ledger, clean_ledger
from .policy import REPORTING_DATE

CSV_PATH = "data/ledger_2024_25.csv"


def money(value: float) -> str:
    return f"₹{value:,.2f}"


def source_rows(df: pd.DataFrame) -> str:
    if df.empty:
        return "None"
    return ", ".join(str(int(x)) for x in df["source_row"].tolist())


def print_q1(df: pd.DataFrame) -> None:
    """Q1: Bharat Steel Works total payable."""
    # GSTIN is the primary identity. Find the GSTIN from the ledger itself.
    matches = df[df["vendor_name_normalized"].str.contains("BHARAT STEEL", na=False)]
    keys = matches["vendor_key"].dropna().unique()

    rows = df[df["vendor_key"].isin(keys)].copy()
    total = rows["line_total_inr"].sum()

    print("Q1. Total payable to Bharat Steel Works")
    print(f"Answer: {money(total)}")
    print(f"Source rows: {source_rows(rows)}")
    print()


def print_q2(df: pd.DataFrame) -> None:
    overdue = overdue_invoices(df)

    print("Q2. Overdue invoices as at 31 March 2025")
    print(f"Count: {len(overdue)}")
    print("Invoices: " + ", ".join(str(x) for x in overdue["invoice_no"].tolist()))
    print(f"Source rows: {source_rows(overdue)}")
    print()


def print_q3(df: pd.DataFrame) -> None:
    ranking = vendor_spend(df)

    if ranking.empty:
        print("Q3. Highest-spend vendor")
        print("Answer: No result")
        print()
        return

    top = ranking.iloc[0]
    rows = df[df["vendor_key"].eq(top["vendor_key"])]

    display_name = rows["vendor_name_original"].iloc[0]

    print("Q3. Vendor with highest FY 2024-25 spend")
    print(f"Vendor: {display_name}")
    print(f"Total: {money(float(top['total_inr']))}")
    print(f"Invoice/credit-note rows: {source_rows(rows)}")
    print()


def print_q4(df: pd.DataFrame) -> None:
    result = invoices_above_taxable(df, 500_000)

    print("Q4. Invoices with taxable amount above ₹5,00,000")
    print(f"Count: {len(result)}")

    for _, row in result.iterrows():
        print(
            f"  {row['invoice_no']} | "
            f"{row['vendor_name_original']} | "
            f"{money(row['taxable_amount'])} | "
            f"source row {int(row['source_row'])}"
        )

    print()


def print_q5(df: pd.DataFrame) -> None:
    total = q3_gst(df)

    q3 = df[
        df["invoice_date"].between("2024-10-01", "2024-12-31") & ~df["is_credit_note"]
    ]

    print("Q5. Total GST charged in Q3")
    print(f"Answer: {money(total)}")
    print(f"Source rows: {source_rows(q3)}")
    print()


def print_q6(df: pd.DataFrame) -> None:
    result = itc_exceptions(df)

    print("Q6. Invoices that cannot be claimed for input tax credit")
    print(f"Count of policy-supported exceptions: {len(result)}")

    for _, row in result.iterrows():
        print(
            f"  {row['invoice_no']} | "
            f"{row['vendor_name']} | "
            f"{' '.join(row['reasons'])} | "
            f"source row {int(row['source_row'])}"
        )

    print()


def print_q7(df: pd.DataFrame) -> None:
    avg = average_fabrication_payment_delay(df)

    fabrication = df[
        (df["category"] == "Fabrication")
        & ~df["is_credit_note"]
        & df["payment_date"].notna()
    ]

    print("Q7. Average payment delay for Fabrication")
    print(f"Answer: {avg:.2f} days")
    print(f"Source rows: {source_rows(fabrication)}")
    print()


def print_q8(df: pd.DataFrame) -> None:
    report = data_quality_report(df)

    print("Q8. Duplicate, suspicious or unreliable entries")
    print()

    labels = {
        "future_invoice_dates": "Future invoice dates",
        "payment_before_invoice": "Payment date before invoice date",
        "missing_taxable_amount": "Missing taxable amount",
        "missing_gstin": "Missing supplier GSTIN",
        "gst_reconciliation_exceptions": "GST reconciliation exceptions",
        "duplicate_invoice_numbers": "Duplicate invoice numbers",
    }

    for key, label in labels.items():
        result = report[key]

        print(f"{label}: {len(result)}")

        if not result.empty:
            for _, row in result.iterrows():
                print(
                    f"  {row['invoice_no']} | "
                    f"{row['vendor_name_original']} | "
                    f"source row {int(row['source_row'])}"
                )

        print()


def main() -> None:
    raw = clean_ledger(CSV_PATH)
    df = analysis_ledger(raw)

    print("=" * 70)
    print("BRIDGELINE LEDGER ASSISTANT — GROUND TRUTH")
    print(f"Reporting date: {REPORTING_DATE}")
    print(f"Raw ledger rows: {len(raw)}")
    print(f"Rows eligible for FY analytics: {len(df)}")
    print("=" * 70)
    print()

    print_q1(df)
    print_q2(df)
    print_q3(df)
    print_q4(df)
    print_q5(df)
    print_q6(df)
    print_q7(df)
    print_q8(raw)


if __name__ == "__main__":
    main()
