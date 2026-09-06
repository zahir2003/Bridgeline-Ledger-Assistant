"""Data quality and anomaly detection."""

import pandas as pd


def data_quality_report(df: pd.DataFrame) -> dict:
    """Return the important data-quality findings."""

    report = {
        "future_invoices": [],
        "payment_before_invoice": [],
        "missing_taxable_amount": [],
        "missing_gstin": [],
        "gst_mismatches": [],
        "duplicate_invoices": [],
        "vendor_name_variations": [],
    }

    # 1. Future invoice dates
    rows = df[df["future_invoice_date"]]

    for _, row in rows.iterrows():
        report["future_invoices"].append(
            {
                "invoice_no": row["invoice_no"],
                "vendor": row["vendor_name_original"],
                "source_row": int(row["source_row"]),
            }
        )

    # 2. Payment date before invoice date
    rows = df[df["payment_before_invoice"]]

    for _, row in rows.iterrows():
        report["payment_before_invoice"].append(
            {
                "invoice_no": row["invoice_no"],
                "vendor": row["vendor_name_original"],
                "source_row": int(row["source_row"]),
            }
        )

    # 3. Missing taxable amount
    rows = df[df["missing_taxable_amount"]]

    for _, row in rows.iterrows():
        report["missing_taxable_amount"].append(
            {
                "invoice_no": row["invoice_no"],
                "vendor": row["vendor_name_original"],
                "source_row": int(row["source_row"]),
            }
        )

    # 4. Missing GSTIN
    rows = df[df["missing_gstin"]]

    for _, row in rows.iterrows():
        report["missing_gstin"].append(
            {
                "invoice_no": row["invoice_no"],
                "vendor": row["vendor_name_original"],
                "source_row": int(row["source_row"]),
            }
        )

    # 5. GST mismatches
    rows = df[df["gst_reconciliation_exception"]]

    for _, row in rows.iterrows():
        report["gst_mismatches"].append(
            {
                "invoice_no": row["invoice_no"],
                "vendor": row["vendor_name_original"],
                "source_row": int(row["source_row"]),
                "difference": float(row["gst_difference"]),
            }
        )

    # 6. Duplicate invoice numbers
    rows = df[df["is_duplicate_invoice"]]

    for invoice_no, group in rows.groupby("invoice_no"):
        report["duplicate_invoices"].append(
            {
                "invoice_no": invoice_no,
                "source_rows": [int(value) for value in group["source_row"].tolist()],
            }
        )

    # 7. Vendor name variations
    rows = df[df["vendor_name_variation"]]

    for gstin, group in rows.groupby("vendor_gstin"):
        names = group["vendor_name_original"].dropna().unique().tolist()

        if len(names) > 1:
            report["vendor_name_variations"].append(
                {
                    "gstin": gstin,
                    "names": names,
                    "source_rows": [
                        int(value) for value in group["source_row"].tolist()
                    ],
                }
            )

    return report
