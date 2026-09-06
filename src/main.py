"""Command-line interface for the Bridgeline Ledger Assistant."""

import sys
from pathlib import Path

# =========================================================
# STEP 1: FORCE UTF-8 OUTPUT
# =========================================================
# Windows PowerShell may use cp1252 by default.
#
# The application prints the Indian Rupee symbol (₹), so
# stdout/stderr are explicitly changed to UTF-8.
#
# This prevents errors such as:
# UnicodeEncodeError: 'charmap' codec can't encode character
# =========================================================

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# =========================================================
# STEP 2: IMPORT LOCAL OLLAMA INTENT CLASSIFIER
# =========================================================
# IMPORTANT ARCHITECTURE DECISION:
#
# Ollama is ONLY used to understand the user's natural-
# language question.
#
# Example:
#
# "Who did we spend the most money with?"
#
#          ↓ Ollama
#
# {"intent": "highest_spend_vendor"}
#
# Ollama does NOT:
# - calculate totals
# - calculate GST
# - calculate payment delays
# - decide source rows
# - rewrite financial results
#
# This keeps financial answers deterministic.
# =========================================================

from .llm import classify_question

# =========================================================
# STEP 3: IMPORT DATA CLEANING
# =========================================================
# clean_ledger()
#     -> loads the original CSV
#     -> cleans dates and money values
#     -> creates source_row
#     -> detects duplicate/superseded rows
#     -> performs data-quality checks
#
# analysis_ledger()
#     -> applies FY and duplicate-invoice rules
#     -> returns the rows that should be used for financial
#        analysis
# =========================================================

from .cleaner import clean_ledger, analysis_ledger

# =========================================================
# STEP 4: IMPORT DETERMINISTIC ANALYTICS
# =========================================================
# All financial calculations happen here in Python.
#
# Python is responsible for:
# - overdue calculations
# - vendor spend
# - taxable threshold
# - GST total
# - ITC exceptions
# - payment delay
#
# This follows the assignment requirement that the LLM
# should not perform spreadsheet arithmetic.
# =========================================================

from .analytics import (
    overdue_invoices,
    vendor_spend,
    invoices_above_taxable,
    q3_gst,
    itc_exceptions,
    average_fabrication_payment_delay,
)

# =========================================================
# STEP 5: IMPORT DATA-QUALITY DETECTOR
# =========================================================
# Data-quality findings are also generated entirely by
# deterministic Python rules.
# =========================================================

from .anomaly_detector import data_quality_report

# =========================================================
# STEP 6: IMPORT FALLBACK PYTHON ROUTER
# =========================================================
# If Ollama:
# - is unavailable
# - returns invalid JSON
# - returns "unknown"
# - returns an unsupported intent
#
# this keyword-based router gets another chance to identify
# the question.
#
# This improves reliability without changing calculations.
# =========================================================

from .query_router import route_question

# =========================================================
# STEP 7: PROJECT PATHS
# =========================================================
# __file__ = src/main.py
# parent   = src
# parent.parent = project root
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = BASE_DIR / "data" / "ledger_2024_25.csv"


# =========================================================
# STEP 8: SUPPORTED INTENTS
# =========================================================
# Keeping the supported intents in one place lets us verify
# that Ollama returned something the application can handle.
# =========================================================

SUPPORTED_INTENTS = {
    "bharat_total",
    "overdue_invoices",
    "highest_spend_vendor",
    "taxable_above_5l",
    "q3_gst",
    "itc_exceptions",
    "fabrication_delay",
    "data_quality",
}


# =========================================================
# STEP 9: SOURCE ROW PRINTING HELPER
# =========================================================
# Every answer should be auditable.
#
# source_row refers to the original CSV row number.
# =========================================================


def print_source_rows(rows):
    """Print sorted and unique source rows."""

    rows = sorted(set(int(row) for row in rows))

    print()
    print("Source rows:")

    if rows:
        print(", ".join(map(str, rows)))
    else:
        print("None")


# =========================================================
# STEP 10: POLICY REFERENCE HELPER
# =========================================================
# The assignment asks us to provide source rows and policy
# references where relevant.
#
# We keep the policy label simple and human-readable.
# =========================================================


def print_policy_reference(policy_text):
    """Print the policy rule used for the calculation."""

    if not policy_text:
        return

    print()
    print("Policy used:")
    print(policy_text)


# =========================================================
# STEP 11: DATA-QUALITY REPORT PRINTER
# =========================================================
# Q8 contains:
# - invoice numbers
# - GSTINs
# - differences
# - source rows
#
# It is printed directly by Python so an LLM cannot omit or
# modify any finding.
# =========================================================


def print_data_quality(report):
    """Print deterministic data-quality findings."""

    print("Answer:")
    print("Data-quality findings:")

    # Store every source row that supports a finding.
    all_source_rows = []

    # -----------------------------------------------------
    # 11A. FUTURE INVOICES
    # -----------------------------------------------------

    if report["future_invoices"]:
        print()
        print("Future invoice:")

        for item in report["future_invoices"]:

            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            all_source_rows.append(item["source_row"])

    # -----------------------------------------------------
    # 11B. PAYMENT BEFORE INVOICE
    # -----------------------------------------------------

    if report["payment_before_invoice"]:
        print()
        print("Payment before invoice:")

        for item in report["payment_before_invoice"]:

            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            all_source_rows.append(item["source_row"])

    # -----------------------------------------------------
    # 11C. MISSING TAXABLE AMOUNT
    # -----------------------------------------------------

    if report["missing_taxable_amount"]:
        print()
        print("Missing taxable amount:")

        for item in report["missing_taxable_amount"]:

            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            all_source_rows.append(item["source_row"])

    # -----------------------------------------------------
    # 11D. MISSING GSTIN
    # -----------------------------------------------------

    if report["missing_gstin"]:
        print()
        print("Missing GSTIN:")

        for item in report["missing_gstin"]:

            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"source row {item['source_row']}"
            )

            all_source_rows.append(item["source_row"])

    # -----------------------------------------------------
    # 11E. GST MISMATCH
    # -----------------------------------------------------

    if report["gst_mismatches"]:
        print()
        print("GST mismatch:")

        for item in report["gst_mismatches"]:

            print(
                f"- {item['invoice_no']} | "
                f"{item['vendor']} | "
                f"difference ₹{item['difference']:,.2f} | "
                f"source row {item['source_row']}"
            )

            all_source_rows.append(item["source_row"])

    # -----------------------------------------------------
    # 11F. DUPLICATE INVOICES
    # -----------------------------------------------------

    if report["duplicate_invoices"]:
        print()
        print("Duplicate invoice:")

        for item in report["duplicate_invoices"]:

            rows = [int(row) for row in item["source_rows"]]

            print(
                f"- {item['invoice_no']} | " f"source rows {', '.join(map(str, rows))}"
            )

            all_source_rows.extend(rows)

    # -----------------------------------------------------
    # 11G. VENDOR NAME VARIATIONS
    # -----------------------------------------------------
    # FIX:
    # Previously these source rows were displayed inside the
    # section but were NOT added to the final Source rows
    # list.
    #
    # Now they are included as well.
    # -----------------------------------------------------

    if report["vendor_name_variations"]:
        print()
        print("Vendor name variations:")

        for item in report["vendor_name_variations"]:

            rows = [int(row) for row in item["source_rows"]]

            print(f"- GSTIN: {item['gstin']}")
            print(f"  Names: {', '.join(item['names'])}")
            print(f"  Source rows: {', '.join(map(str, rows))}")

            all_source_rows.extend(rows)

    # -----------------------------------------------------
    # 11H. NO ISSUES
    # -----------------------------------------------------

    if not any(report.values()):
        print("- No data-quality issues found.")

    # -----------------------------------------------------
    # 11I. FINAL AUDIT SOURCE ROWS
    # -----------------------------------------------------

    if all_source_rows:
        print_source_rows(all_source_rows)

    print_policy_reference(
        "Data-quality exceptions, duplicate-invoice rule, "
        "and GST reconciliation rules."
    )


# =========================================================
# STEP 12: MAIN APPLICATION
# =========================================================


def main():
    """Run the Bridgeline Ledger Assistant."""

    # -----------------------------------------------------
    # STEP 12A: READ THE QUESTION
    # -----------------------------------------------------
    #
    # Example:
    #
    # python -m src.main \
    # "What is the total payable to Bharat Steel?"
    # -----------------------------------------------------

    if len(sys.argv) < 2:

        print('Usage: python -m src.main "your question"')

        return

    question = " ".join(sys.argv[1:]).strip()

    if not question:

        print('Usage: python -m src.main "your question"')

        return

    # -----------------------------------------------------
    # STEP 12B: ASK OLLAMA FOR THE INTENT
    # -----------------------------------------------------
    # Ollama only understands/classifies the question.
    # -----------------------------------------------------

    llm_result = classify_question(question)

    intent = llm_result.get("intent")

    # -----------------------------------------------------
    # STEP 12C: VALIDATE THE LLM INTENT
    # -----------------------------------------------------
    # FIX:
    #
    # Previously the fallback router only ran when:
    #
    # intent == "unknown"
    #
    # If Ollama returned None or an unexpected value, the
    # fallback did not run.
    #
    # Now ANY unsupported value triggers the deterministic
    # fallback router.
    # -----------------------------------------------------

    if intent not in SUPPORTED_INTENTS:

        intent = route_question(question)

    # -----------------------------------------------------
    # STEP 12D: HANDLE UNSUPPORTED QUESTIONS SAFELY
    # -----------------------------------------------------

    if intent not in SUPPORTED_INTENTS:

        print(
            "Sorry, I could not understand the question "
            "or it is not currently supported."
        )

        return

    # -----------------------------------------------------
    # STEP 12E: LOAD AND CLEAN ORIGINAL LEDGER
    # -----------------------------------------------------

    df = clean_ledger(CSV_FILE)

    # -----------------------------------------------------
    # STEP 12F: APPLY ANALYSIS RULES
    # -----------------------------------------------------
    # This applies:
    # - FY scope
    # - duplicate supersession
    # - other analysis filtering
    # -----------------------------------------------------

    analysis_df = analysis_ledger(df)

    # =====================================================
    # Q1 - BHARAT STEEL TOTAL PAYABLE
    # =====================================================

    if intent == "bharat_total":

        # Find every analysed Bharat Steel row.
        bharat_rows = analysis_df[
            analysis_df["vendor_name_normalized"].str.contains(
                "BHARAT STEEL",
                na=False,
            )
        ]

        # Python performs exact arithmetic.
        result = float(bharat_rows["line_total_inr"].sum())

        source_rows = bharat_rows["source_row"].tolist()

        # -------------------------------------------------
        # IMPORTANT FIX:
        #
        # We print the exact Python value directly.
        #
        # We DO NOT send the number/source rows to Ollama
        # for rewriting.
        # -------------------------------------------------

        print("Answer:")

        print(f"Bharat Steel Works total payable: " f"₹{result:,.2f}")

        print_source_rows(source_rows)

        print_policy_reference(
            "FY 2024-25 scope, currency conversion, "
            "credit-note rule and duplicate-invoice rule."
        )

    # =====================================================
    # Q2 - OVERDUE INVOICES
    # =====================================================

    elif intent == "overdue_invoices":

        result = overdue_invoices(analysis_df)

        print("Answer:")
        print(f"{len(result)} invoices are overdue " f"as at 31 March 2025.")

        for _, row in result.iterrows():

            print(f"- {row['invoice_no']} | " f"source row {int(row['source_row'])}")

        print_source_rows(result["source_row"].tolist())

        print_policy_reference(
            "Category payment terms; an invoice is overdue "
            "when unpaid at the reporting date and elapsed "
            "days exceed the standard payment term."
        )

    # =====================================================
    # Q3 - HIGHEST-SPEND VENDOR
    # =====================================================

    elif intent == "highest_spend_vendor":

        result = vendor_spend(analysis_df)

        top = result.iloc[0]

        vendor_key = top["vendor_key"]

        amount = float(top["total_inr"])

        matching_rows = analysis_df[analysis_df["vendor_key"] == vendor_key]

        vendor_name = matching_rows.iloc[0]["vendor_name_original"]

        source_rows = matching_rows["source_row"].tolist()

        print("Answer:")

        print(f"{vendor_name} has the highest spend: " f"₹{amount:,.2f}")

        print_source_rows(source_rows)

        print_policy_reference(
            "FY 2024-25 scope, currency conversion, "
            "credit-note rule and duplicate-invoice rule."
        )

    # =====================================================
    # Q4 - TAXABLE AMOUNT ABOVE ₹5 LAKH
    # =====================================================

    elif intent == "taxable_above_5l":

        result = invoices_above_taxable(
            analysis_df,
            threshold=500_000,
        )

        print("Answer:")

        print(f"{len(result)} invoices have taxable amount " f"above ₹5 lakh.")

        for _, row in result.iterrows():

            print(
                f"- {row['invoice_no']} | "
                f"₹{row['taxable_amount']:,.2f} | "
                f"source row {int(row['source_row'])}"
            )

        print_source_rows(result["source_row"].tolist())

        print_policy_reference("FY 2024-25 scope and duplicate-invoice rule.")

    # =====================================================
    # Q5 - GST CHARGED IN Q3
    # =====================================================

    elif intent == "q3_gst":

        # Python calculates the exact GST total.
        result = q3_gst(analysis_df)

        # Use the same date criteria as q3_gst().
        q3_rows = analysis_df[
            analysis_df["invoice_date"].between(
                "2024-10-01",
                "2024-12-31",
            )
            & (~analysis_df["is_credit_note"])
        ]

        print("Answer:")

        print(f"GST charged in Q3 " f"(October-December 2024): " f"₹{result:,.2f}")

        print_source_rows(q3_rows["source_row"].tolist())

        print_policy_reference(
            "GST reporting with FY 2024-25 scope; "
            "credit notes are excluded from GST charged."
        )

    # =====================================================
    # Q6 - ITC UNAVAILABLE / EXCEPTIONS
    # =====================================================

    elif intent == "itc_exceptions":

        result = itc_exceptions(analysis_df)

        print("Answer:")

        print(f"{len(result)} invoices have ITC exceptions.")

        for _, row in result.iterrows():

            reasons = ", ".join(row["reasons"])

            print(
                f"- {row['invoice_no']} | "
                f"{row['vendor_name']} | "
                f"Reason: {reasons} | "
                f"source row {int(row['source_row'])}"
            )

        print_source_rows(result["source_row"].tolist())

        print_policy_reference(
            "ITC is unavailable when GSTIN is missing or "
            "when expected GST and recorded GST differ by "
            "more than ₹1 until corrected."
        )

    # =====================================================
    # Q7 - AVERAGE FABRICATION PAYMENT DELAY
    # =====================================================

    elif intent == "fabrication_delay":

        result = average_fabrication_payment_delay(analysis_df)

        # -------------------------------------------------
        # IMPORTANT FIX:
        #
        # average_fabrication_payment_delay() only uses:
        #
        # - Fabrication rows
        # - non-credit-note rows
        # - rows with payment_date
        #
        # The old main.py used ALL Fabrication rows for the
        # source list.
        #
        # That could include rows that did not contribute to
        # the actual average.
        #
        # Now the source population matches the calculation.
        # -------------------------------------------------

        fabrication_rows = analysis_df[
            (analysis_df["category"].str.lower() == "fabrication")
            & (~analysis_df["is_credit_note"])
            & (analysis_df["payment_date"].notna())
        ]

        print("Answer:")

        print(f"Average Fabrication payment delay: " f"{result:.2f} days")

        # Preserve the negative value exactly.
        if result < 0:

            print(
                f"Interpretation: {abs(result):.2f} days early "
                f"on average relative to the contractual "
                f"payment due date."
            )

        elif result > 0:

            print(
                f"Interpretation: {result:.2f} days late "
                f"on average relative to the contractual "
                f"payment due date."
            )

        else:

            print(
                "Interpretation: Payments were made on the "
                "contractual due date on average."
            )

        print_source_rows(fabrication_rows["source_row"].tolist())

        print_policy_reference(
            "Fabrication payment term = 45 days. "
            "Payment delay = payment date - invoice date "
            "- standard payment term. Negative values are "
            "preserved."
        )

    # =====================================================
    # Q8 - DUPLICATE / SUSPICIOUS / UNRELIABLE DATA
    # =====================================================

    elif intent == "data_quality":

        # Use the original cleaned ledger rather than
        # analysis_df because Q8 must also expose rows that
        # may later be excluded from analytical totals.
        report = data_quality_report(df)

        print_data_quality(report)


# =========================================================
# STEP 13: PYTHON ENTRY POINT
# =========================================================
#
# Run with:
#
# python -m src.main "your question"
#
# Example:
#
# python -m src.main \
# "Which vendor has the highest spend?"
# =========================================================

if __name__ == "__main__":
    main()
