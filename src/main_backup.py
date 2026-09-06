"""Command-line interface for the Bridgeline Ledger Assistant."""

import sys
from pathlib import Path

from src.cleaner import clean_ledger, analysis_ledger

from src.analytics import (
    vendor_total,
    overdue_invoices,
    vendor_spend,
    invoices_above_taxable,
    q3_gst,
    itc_exceptions,
    average_fabrication_payment_delay,
)

from src.anomaly_detector import data_quality_report
from src.query_router import route_question

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "data" / "ledger_2024_25.csv"


def print_source_rows(rows):
    """Print source rows consistently."""

    rows = sorted(set(int(row) for row in rows))

    print()
    print("Source rows:")
    print(", ".join(map(str, rows)))


def print_data_quality(report):
    """Print Q8 data-quality findings."""

    print("Answer:")
    print("Data-quality findings:")

    direct_source_rows = []

    # Future invoices
    if report["future_invoices"]:
        print("\nFuture invoice:")

        for item in report["future_invoices"]:
            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            direct_source_rows.append(item["source_row"])

    # Payment before invoice
    if report["payment_before_invoice"]:
        print("\nPayment before invoice:")

        for item in report["payment_before_invoice"]:
            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            direct_source_rows.append(item["source_row"])

    # Missing taxable amount
    if report["missing_taxable_amount"]:
        print("\nMissing taxable amount:")

        for item in report["missing_taxable_amount"]:
            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            direct_source_rows.append(item["source_row"])

    # Missing GSTIN
    if report["missing_gstin"]:
        print("\nMissing GSTIN:")

        for item in report["missing_gstin"]:
            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            direct_source_rows.append(item["source_row"])

    # GST mismatch
    if report["gst_mismatches"]:
        print("\nGST mismatch:")

        for item in report["gst_mismatches"]:
            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"difference ₹{item['difference']:,.2f} | "
                f"source row {item['source_row']}"
            )

            direct_source_rows.append(item["source_row"])

    # Duplicate invoices
    if report["duplicate_invoices"]:
        print("\nDuplicate invoice:")

        for item in report["duplicate_invoices"]:
            rows = item["source_rows"]

            print(
                f"- {item['invoice_no']} | " f"source rows {', '.join(map(str, rows))}"
            )

            direct_source_rows.extend(rows)

    # Vendor name variations
    if report["vendor_name_variations"]:
        print("\nVendor name variations:")

        for item in report["vendor_name_variations"]:
            print(f"- GSTIN: {item['gstin']}")
            print(f"  Names: {', '.join(item['names'])}")
            print(f"  Source rows: " f"{', '.join(map(str, item['source_rows']))}")

    if not any(report.values()):
        print("- No data-quality issues found.")

    if direct_source_rows:
        print_source_rows(direct_source_rows)


def main():

    if len(sys.argv) < 2:
        print('Usage: python -m src.main "your question"')
        return

    question = " ".join(sys.argv[1:])

    intent = route_question(question)

    if intent is None:
        print("Sorry, I could not understand the question.")
        return

    # Load and clean data
    df = clean_ledger(CSV_FILE)

    # Apply FY and duplicate policy
    analysis_df = analysis_ledger(df)

    # ---------------------------------------------------------
    # Q1 - Bharat Steel Works
    # ---------------------------------------------------------

    if intent == "bharat_total":

        bharat_rows = analysis_df[
            analysis_df["vendor_name_normalized"].str.contains(
                "BHARAT STEEL",
                na=False
            )
        ]
    

        result = bharat_rows["line_total_inr"].sum()

        print("Answer:")
        print(
            f"Bharat Steel Works total payable: "
            f"₹{result:,.2f}"
        )

        print_source_rows(
            bharat_rows["source_row"]
        )

    # ---------------------------------------------------------
    # Q2 - Overdue invoices
    # ---------------------------------------------------------

    elif intent == "overdue_invoices":

        result = overdue_invoices(analysis_df)

        print("Answer:")
        print(f"{len(result)} invoices are overdue.")

        for _, row in result.iterrows():

            amount = row["line_total_inr"]

            if amount != amount:
                amount_text = "Amount unavailable"
            else:
                amount_text = f"₹{amount:,.2f}"

            print(
                f"- {row['invoice_no']} | "
                f"source row {int(row['source_row'])}"
            )

        print_source_rows(result["source_row"])

    # ---------------------------------------------------------
    # Q3 - Highest spend vendor
    # ---------------------------------------------------------

    elif intent == "highest_spend_vendor":

        result = vendor_spend(analysis_df)

        top = result.iloc[0]

        vendor_key = top["vendor_key"]
        amount = top["total_inr"]

        matching_rows = analysis_df[
            analysis_df["vendor_key"] == vendor_key
        ]

        vendor_name = matching_rows.iloc[0][
            "vendor_name_original"
        ]

        print("Answer:")
        print(
            f"{vendor_name} has the highest spend: "
            f"₹{amount:,.2f}"
        )

        print_source_rows(
            matching_rows["source_row"]
        )

    # ---------------------------------------------------------
    # Q4 - Taxable amount above ₹5 lakh
    # ---------------------------------------------------------

    elif intent == "taxable_above_5l":

        result = invoices_above_taxable(analysis_df, threshold=500000)

        print("Answer:")
        print(f"{len(result)} invoices have taxable amount " f"above ₹5 lakh.")

        for _, row in result.iterrows():

            print(
                f"- {row['invoice_no']} | "
                f"₹{row['taxable_amount']:,.2f} | "
                f"source row {int(row['source_row'])}"
            )

        print_source_rows(result["source_row"])

    # ---------------------------------------------------------
    # Q5 - Q3 GST
    # ---------------------------------------------------------

    elif intent == "q3_gst":

        result = q3_gst(analysis_df)

        print("Answer:")
        print(f"GST charged in Q3: " f"₹{result:,.2f}")

        q3_rows = analysis_df[
            (analysis_df["invoice_date"] >= "2024-10-01")
            & (analysis_df["invoice_date"] <= "2024-12-31")
            & (~analysis_df["is_credit_note"])
        ]

        print_source_rows(q3_rows["source_row"])

    # ---------------------------------------------------------
    # Q6 - ITC exceptions
    # ---------------------------------------------------------

    elif intent == "itc_exceptions":

        result = itc_exceptions(analysis_df)

        print("Answer:")
        print(
            f"{len(result)} invoices have ITC exceptions."
        )

        for _, row in result.iterrows():

            print(
                f"- {row['invoice_no']} | "
                f"source row {int(row['source_row'])}"
            )

        print_source_rows(result["source_row"])

    # ---------------------------------------------------------
    # Q7 - Fabrication payment delay
    # ---------------------------------------------------------

    elif intent == "fabrication_delay":

        result = average_fabrication_payment_delay(analysis_df)

        print("Answer:")
        print(f"Average Fabrication payment delay: " f"{result:.2f} days")

        fabrication_rows = analysis_df[
            analysis_df["category"].str.lower() == "fabrication"
        ]

        print_source_rows(fabrication_rows["source_row"])

    # ---------------------------------------------------------
    # Q8 - Data quality
    # ---------------------------------------------------------

    elif intent == "data_quality":

        report = data_quality_report(df)

        print_data_quality(report)


if __name__ == "__main__":
    main()
