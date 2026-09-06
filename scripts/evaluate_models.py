"""
Bridgeline Ledger Assistant
Automated Evaluation for Local Ollama Models

=========================================================
PROJECT EVALUATION DESIGN
=========================================================

This script evaluates the REAL application.

The evaluation flow is:

    Raw CSV
       |
       v
    Python cleaning
       |
       v
    Python policy / analysis
       |
       v
    Deterministic ground truth
       |
       +-----------------------------+
       |                             |
       v                             v
  LLM intent                    Real CLI app
  classification                execution
       |                             |
       +-------------+---------------+
                     |
                     v
              Compare results
                     |
                     v
             Evaluation report


IMPORTANT ARCHITECTURE DECISION
--------------------------------

The LLM is NOT trusted with financial calculations.

Ollama is used for:

    User question
        |
        v
    Intent classification

Python is responsible for:

    - financial calculations
    - payment rules
    - GST calculations
    - ITC rules
    - duplicate handling
    - source rows
    - final exact output

This means a 100% application accuracy score means:

    "The complete application produced the correct
     deterministic answer."

It does NOT mean:

    "The LLM independently calculated financial
     answers with 100% accuracy."

That distinction is intentionally documented here.
"""

# =========================================================
# STEP 1: IMPORT PYTHON LIBRARIES
# =========================================================

import os
import re
import subprocess
import sys
import time
from pathlib import Path

# =========================================================
# STEP 2: FIND PROJECT ROOT
# =========================================================
#
# Current file:
#
#     scripts/evaluate_models.py
#
# Project root:
#
#     bridgeline-ledger-assistant/
#
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Make sure Python can import the src package.
sys.path.insert(0, str(BASE_DIR))


# =========================================================
# STEP 3: IMPORT PROJECT FUNCTIONS
# =========================================================
#
# clean_ledger()
#     -> loads and cleans the original CSV
#
# analysis_ledger()
#     -> applies financial analysis rules
# =========================================================

from src.cleaner import clean_ledger, analysis_ledger

# =========================================================
# STEP 4: IMPORT DETERMINISTIC ANALYTICS
# =========================================================

from src.analytics import (
    vendor_total,
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

from src.anomaly_detector import data_quality_report

# =========================================================
# STEP 6: IMPORT LOCAL OLLAMA CLASSIFIER
# =========================================================
#
# This is used ONLY to measure whether the LLM itself
# correctly identifies the question intent.
#
# It does NOT calculate any financial value.
# =========================================================

from src.llm import classify_question

# =========================================================
# STEP 7: DATA FILE
# =========================================================

RAW_FILE = BASE_DIR / "data" / "ledger_2024_25.csv"


# =========================================================
# STEP 8: MODELS TO COMPARE
# =========================================================
#
# Both models run locally through Ollama.
#
# Model 1:
#     Llama 3 8B
#
# Model 2:
#     Llama 3.2 3B
#
# =========================================================

MODELS = [
    "llama3:latest",
    "llama3.2:3b",
]


# =========================================================
# STEP 9: NUMBER OF REPEATED RUNS
# =========================================================
#
# A single run can sometimes be affected by:
#
# - model generation variation
# - first-load/model warm-up
# - temporary system load
#
# Therefore we run every question multiple times.
#
# 3 runs is enough for this small local evaluation.
#
# Total application runs:
#
#     2 models × 12 questions × 3 runs
#
#     = 72 application evaluations
#
# =========================================================

REPEAT_RUNS = 3


# =========================================================
# STEP 10: TEST QUESTIONS
# =========================================================
#
# Q1-Q8:
#     Assignment questions
#
# Q9-Q12:
#     Additional evaluation questions
#
# =========================================================

QUESTIONS = [
    ("Q1", "What is the total payable to Bharat Steel?"),
    ("Q2", "Which invoices are overdue as of 31 March 2025?"),
    ("Q3", "Which vendor has the highest spend?"),
    ("Q4", "Which invoices have taxable amounts above ₹5 lakh?"),
    ("Q5", "What is the GST charged in Q3?"),
    ("Q6", "Which invoices have ITC exceptions and why?"),
    ("Q7", "What is the average payment delay for Fabrication?"),
    ("Q8", "What are the suspicious or unreliable entries?"),
    ("Q9", "How much do we owe Bharat Steel Works?"),
    ("Q10", "Who is our biggest vendor by total spend?"),
    ("Q11", "Were Fabrication vendors paid early or late on average?"),
    ("Q12", "Tell me about the unreliable data in the ledger."),
]


# =========================================================
# STEP 11: EXPECTED INTENTS
# =========================================================
#
# These are the intents that Ollama should identify.
#
# This allows us to measure the LLM's actual classification
# accuracy separately from the deterministic Python answer.
#
# =========================================================

EXPECTED_INTENTS = {
    "Q1": "bharat_total",
    "Q2": "overdue_invoices",
    "Q3": "highest_spend_vendor",
    "Q4": "taxable_above_5l",
    "Q5": "q3_gst",
    "Q6": "itc_exceptions",
    "Q7": "fabrication_delay",
    "Q8": "data_quality",
    "Q9": "bharat_total",
    "Q10": "highest_spend_vendor",
    "Q11": "fabrication_delay",
    "Q12": "data_quality",
}


# =========================================================
# STEP 12: SUPPORTED INTENTS
# =========================================================
#
# These should match src/main.py and src/llm.py.
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
# STEP 13: TEXT NORMALIZATION
# =========================================================
#
# Used to make comparisons less sensitive to:
#
# - uppercase/lowercase
# - commas
# - extra spaces
#
# Example:
#
#     ₹6,402,037.70
#
# becomes:
#
#     6402037.70
#
# =========================================================


def normalize(text):
    """Normalize text for easier comparison."""

    text = str(text).lower()

    # Remove the Rupee symbol.
    text = text.replace("₹", "")

    # Remove thousands separators.
    text = text.replace(",", "")

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# STEP 14: CLASSIFY QUESTION WITH OLLAMA
# =========================================================
#
# This function measures the LLM's intent classification
# independently.
#
# IMPORTANT:
#
# This does NOT measure financial calculation ability.
#
# It measures:
#
#     Question understanding
#             +
#     Intent classification
#
# =========================================================


def classify_with_model(model, question):
    """
    Ask the selected Ollama model to classify a question.

    Returns:
        predicted_intent
    """

    # Set the model for this process.
    os.environ["OLLAMA_MODEL"] = model

    try:

        result = classify_question(question)

        intent = result.get("intent")

        if intent not in SUPPORTED_INTENTS:

            return "unknown"

        return intent

    except Exception:

        return "unknown"


# =========================================================
# STEP 15: RUN THE REAL APPLICATION
# =========================================================
#
# We execute the actual command:
#
#     python -m src.main "question"
#
# This is important.
#
# We are not testing a separate fake implementation.
#
# We are testing the application that will actually be
# submitted.
#
# =========================================================


def run_question(model, question):
    """Run the real CLI application using one model."""

    # Copy current environment.
    env = os.environ.copy()

    # Tell src.llm.py which model to use.
    env["OLLAMA_MODEL"] = model

    # Start timer.
    start = time.perf_counter()

    # Execute the real application.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            question,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=BASE_DIR,
    )

    # Calculate elapsed time.
    elapsed = time.perf_counter() - start

    # Get normal application output.
    answer = result.stdout.strip()

    # If the application failed, include the error.
    if result.returncode != 0:

        if result.stderr.strip():

            answer += "\n" + result.stderr.strip()

    return answer, elapsed, result.returncode


# =========================================================
# STEP 16: BUILD DETERMINISTIC GROUND TRUTH
# =========================================================
#
# The ground truth is generated by Python.
#
# This prevents the LLM from becoming the source of truth.
#
# =========================================================


def build_ground_truth(df):
    """Create deterministic ground truth for all questions."""

    truth = {}

    # =====================================================
    # STEP 16A: APPLY SAME ANALYSIS PIPELINE AS main.py
    # =====================================================
    #
    # This is very important.
    #
    # main.py does:
    #
    #     clean_ledger()
    #     analysis_ledger()
    #
    # Therefore the evaluator must do the same.
    #
    # =====================================================

    analysis_df = analysis_ledger(df)

    # =====================================================
    # Q1 / Q9 - BHARAT STEEL TOTAL
    # =====================================================

    bharat = analysis_df[
        analysis_df["vendor_name_normalized"]
        .astype(str)
        .str.contains(
            "bharat steel",
            case=False,
            na=False,
        )
    ]

    if bharat.empty:

        raise RuntimeError("Could not find Bharat Steel in the ledger.")

    bharat_key = bharat["vendor_key"].iloc[0]

    bharat_total = vendor_total(
        analysis_df,
        bharat_key,
    )

    bharat_sources = (
        analysis_df[analysis_df["vendor_key"] == bharat_key]["source_row"]
        .astype(int)
        .tolist()
    )

    truth["Q1"] = {
        "facts": [
            f"{bharat_total:.2f}",
        ],
        "invoices": [],
        "sources": sorted(set(bharat_sources)),
    }

    truth["Q9"] = {
        "facts": truth["Q1"]["facts"].copy(),
        "invoices": [],
        "sources": truth["Q1"]["sources"].copy(),
    }

    # =====================================================
    # Q2 - OVERDUE INVOICES
    # =====================================================

    overdue = overdue_invoices(analysis_df)

    truth["Q2"] = {
        "facts": [],
        "invoices": (overdue["invoice_no"].astype(str).tolist()),
        "sources": (overdue["source_row"].astype(int).tolist()),
    }

    # =====================================================
    # Q3 / Q10 - HIGHEST-SPEND VENDOR
    # =====================================================

    spend = vendor_spend(analysis_df)

    top = spend.iloc[0]

    top_key = top["vendor_key"]

    top_amount = float(top["total_inr"])

    top_rows = analysis_df[analysis_df["vendor_key"] == top_key]

    # Use the most common original spelling.
    top_vendor = top_rows["vendor_name_original"].value_counts().index[0]

    truth["Q3"] = {
        "facts": [
            top_vendor,
            f"{top_amount:.2f}",
        ],
        "invoices": [],
        "sources": (top_rows["source_row"].astype(int).tolist()),
    }

    truth["Q10"] = {
        "facts": truth["Q3"]["facts"].copy(),
        "invoices": [],
        "sources": truth["Q3"]["sources"].copy(),
    }

    # =====================================================
    # Q4 - TAXABLE AMOUNT ABOVE ₹5 LAKH
    # =====================================================

    taxable = invoices_above_taxable(
        analysis_df,
        threshold=500_000,
    )

    truth["Q4"] = {
        "facts": [],
        "invoices": (taxable["invoice_no"].astype(str).tolist()),
        "sources": (taxable["source_row"].astype(int).tolist()),
    }

    # =====================================================
    # Q5 - GST IN Q3
    # =====================================================

    gst = q3_gst(analysis_df)

    q3_rows = analysis_df[
        analysis_df["invoice_date"].between(
            "2024-10-01",
            "2024-12-31",
        )
        & (~analysis_df["is_credit_note"])
    ]

    truth["Q5"] = {
        "facts": [
            f"{gst:.2f}",
        ],
        "invoices": [],
        "sources": (q3_rows["source_row"].astype(int).tolist()),
    }

    # =====================================================
    # Q6 - ITC EXCEPTIONS
    # =====================================================

    itc = itc_exceptions(analysis_df)

    truth["Q6"] = {
        "facts": [],
        "invoices": (itc["invoice_no"].astype(str).tolist()),
        "sources": (itc["source_row"].astype(int).tolist()),
    }

    # =====================================================
    # Q7 / Q11 - FABRICATION PAYMENT DELAY
    # =====================================================

    delay = average_fabrication_payment_delay(analysis_df)

    fabrication = analysis_df[
        (analysis_df["category"].str.lower() == "fabrication")
        & (~analysis_df["is_credit_note"])
        & (analysis_df["payment_date"].notna())
    ]

    truth["Q7"] = {
        "facts": [
            f"{delay:.2f}",
        ],
        "invoices": [],
        "sources": (fabrication["source_row"].astype(int).tolist()),
    }

    truth["Q11"] = {
        "facts": truth["Q7"]["facts"].copy(),
        "invoices": [],
        "sources": truth["Q7"]["sources"].copy(),
    }

    # =====================================================
    # Q8 / Q12 - DATA QUALITY
    # =====================================================
    #
    # Use the cleaned dataframe directly.
    #
    # Data-quality exceptions may include rows that are not
    # part of normal financial analysis.
    #
    # =====================================================

    quality = data_quality_report(df)

    anomaly_invoices = []

    anomaly_sources = set()

    # -----------------------------------------------------
    # Future invoices
    # -----------------------------------------------------

    for item in quality["future_invoices"]:

        anomaly_invoices.append(item["invoice_no"])

        anomaly_sources.add(int(item["source_row"]))

    # -----------------------------------------------------
    # Payment before invoice
    # -----------------------------------------------------

    for item in quality["payment_before_invoice"]:

        anomaly_invoices.append(item["invoice_no"])

        anomaly_sources.add(int(item["source_row"]))

    # -----------------------------------------------------
    # Missing taxable amount
    # -----------------------------------------------------

    for item in quality["missing_taxable_amount"]:

        anomaly_invoices.append(item["invoice_no"])

        anomaly_sources.add(int(item["source_row"]))

    # -----------------------------------------------------
    # Missing GSTIN
    # -----------------------------------------------------

    for item in quality["missing_gstin"]:

        anomaly_invoices.append(item["invoice_no"])

        anomaly_sources.add(int(item["source_row"]))

    # -----------------------------------------------------
    # GST mismatch
    # -----------------------------------------------------

    for item in quality["gst_mismatches"]:

        anomaly_invoices.append(item["invoice_no"])

        anomaly_sources.add(int(item["source_row"]))

    # -----------------------------------------------------
    # Duplicate invoices
    # -----------------------------------------------------

    for item in quality["duplicate_invoices"]:

        anomaly_invoices.append(item["invoice_no"])

        for row in item["source_rows"]:

            anomaly_sources.add(int(row))

    # -----------------------------------------------------
    # Vendor name variations
    # -----------------------------------------------------
    #
    # Include their source rows because main.py displays
    # them as part of the data-quality findings.
    #
    # -----------------------------------------------------

    for item in quality["vendor_name_variations"]:

        for row in item["source_rows"]:

            anomaly_sources.add(int(row))

    # Remove duplicate invoice numbers.
    anomaly_invoices = list(dict.fromkeys(anomaly_invoices))

    truth["Q8"] = {
        "facts": [],
        "invoices": anomaly_invoices,
        "sources": sorted(anomaly_sources),
    }

    truth["Q12"] = {
        "facts": truth["Q8"]["facts"].copy(),
        "invoices": truth["Q8"]["invoices"].copy(),
        "sources": truth["Q8"]["sources"].copy(),
    }

    return truth


# =========================================================
# STEP 17: FACT SCORE
# =========================================================
#
# IMPORTANT:
#
# If a question has no expected facts, return None.
#
# We DO NOT return 100%.
#
# This makes the evaluation more honest.
#
# =========================================================


def fact_score(answer, facts):
    """Return fact accuracy or None if not applicable."""

    if not facts:

        return None

    text = normalize(answer)

    found = 0

    for fact in facts:

        if normalize(fact) in text:

            found += 1

    return found / len(facts) * 100


# =========================================================
# STEP 18: INVOICE COMPLETENESS SCORE
# =========================================================


def invoice_score(answer, invoices):
    """Return invoice completeness or None if not applicable."""

    if not invoices:

        return None

    text = normalize(answer)

    found = 0

    for invoice in invoices:

        if normalize(invoice) in text:

            found += 1

    return found / len(invoices) * 100


# =========================================================
# STEP 19: EXTRACT SOURCE ROWS
# =========================================================
#
# Supports BOTH formats:
#
# Format A:
#
#     source row 81
#
# Format B:
#
#     Source rows:
#     2, 3, 21, 39
#
# =========================================================


def extract_source_rows(answer):
    """Extract source row numbers from application output."""

    text = str(answer)

    found_rows = set()

    # -----------------------------------------------------
    # FORMAT A
    #
    # source row 81
    # source rows 81
    # -----------------------------------------------------

    matches = re.findall(
        r"\bsource\s+rows?\s+(\d+)",
        text,
        flags=re.IGNORECASE,
    )

    for match in matches:

        found_rows.add(int(match))

    # -----------------------------------------------------
    # FORMAT B
    #
    # Source rows:
    # 2, 3, 21, 39
    #
    # -----------------------------------------------------

    block_matches = re.findall(
        r"source\s+rows?\s*:\s*([0-9,\s]+)",
        text,
        flags=re.IGNORECASE,
    )

    for block in block_matches:

        numbers = re.findall(
            r"\d+",
            block,
        )

        for number in numbers:

            found_rows.add(int(number))

    return found_rows


# =========================================================
# STEP 20: SOURCE SCORE
# =========================================================


def source_score(answer, sources):
    """Return source accuracy or None if not applicable."""

    if not sources:

        return None

    expected_rows = set(int(row) for row in sources)

    found_rows = extract_source_rows(answer)

    found = len(expected_rows.intersection(found_rows))

    return found / len(expected_rows) * 100


# =========================================================
# STEP 21: CALCULATE APPLICATION SCORE
# =========================================================
#
# We use:
#
#     Facts       = 40%
#     Completeness = 40%
#     Sources      = 20%
#
# BUT:
#
# Non-applicable categories are excluded from the
# calculation.
#
# Example:
#
# Q1:
#
# Facts       = 100
# Invoices    = N/A
# Sources     = 100
#
# Overall:
#
#     (100 × 40 + 100 × 20) / 60
#
#     = 100%
#
# This is more honest than pretending invoices were tested.
#
# =========================================================


def application_score(answer, expected):
    """Calculate application correctness."""

    facts = fact_score(
        answer,
        expected["facts"],
    )

    invoices = invoice_score(
        answer,
        expected["invoices"],
    )

    sources = source_score(
        answer,
        expected["sources"],
    )

    # Store only metrics that actually apply.
    weighted_scores = []

    if facts is not None:

        weighted_scores.append((facts, 0.40))

    if invoices is not None:

        weighted_scores.append((invoices, 0.40))

    if sources is not None:

        weighted_scores.append((sources, 0.20))

    # Safety check.
    if not weighted_scores:

        overall = 100.0

    else:

        total_score = sum(score * weight for score, weight in weighted_scores)

        total_weight = sum(weight for _, weight in weighted_scores)

        overall = total_score / total_weight

    return (
        facts,
        invoices,
        sources,
        overall,
    )


# =========================================================
# STEP 22: FORMAT SCORE
# =========================================================
#
# Print:
#
#     100%
#
# or:
#
#     N/A
#
# =========================================================


def format_score(value):
    """Format a score for terminal output."""

    if value is None:

        return "N/A"

    return f"{value:.0f}%"


# =========================================================
# STEP 23: MAIN EVALUATION
# =========================================================


def main():

    print("=" * 80)
    print("BRIDGELINE LEDGER ASSISTANT")
    print("HONEST AUTOMATED MODEL EVALUATION")
    print("=" * 80)

    print()
    print(
        "Architecture: " "Ollama intent classification + deterministic Python analytics"
    )

    print(f"Repeated runs per question/model: {REPEAT_RUNS}")

    # =====================================================
    # STEP 23A: CREATE GROUND TRUTH
    # =====================================================

    print()
    print("Creating deterministic Python ground truth...")

    df = clean_ledger(RAW_FILE)

    truth = build_ground_truth(df)

    print(f"Ledger rows : {len(df)}")

    print(f"Questions   : {len(QUESTIONS)}")

    print(f"Models      : {len(MODELS)}")

    print(f"Total application runs: " f"{len(MODELS) * len(QUESTIONS) * REPEAT_RUNS}")

    # =====================================================
    # STEP 23B: STORE ALL RESULTS
    # =====================================================

    all_results = []

    # =====================================================
    # STEP 23C: TEST EACH MODEL
    # =====================================================

    for model in MODELS:

        print()
        print("=" * 80)
        print(f"MODEL: {model}")
        print("=" * 80)

        for question_id, question in QUESTIONS:

            expected_intent = EXPECTED_INTENTS[question_id]

            # -------------------------------------------------
            # Store repeated run results.
            # -------------------------------------------------

            run_results = []

            # -------------------------------------------------
            # Repeat the same question several times.
            # -------------------------------------------------

            for run_number in range(
                1,
                REPEAT_RUNS + 1,
            ):

                # =============================================
                # STEP 23C-1:
                # TEST LLM INTENT CLASSIFICATION
                # =============================================

                predicted_intent = classify_with_model(
                    model,
                    question,
                )

                intent_correct = predicted_intent == expected_intent

                # =============================================
                # STEP 23C-2:
                # TEST REAL APPLICATION
                # =============================================

                answer, elapsed, return_code = run_question(
                    model,
                    question,
                )

                # =============================================
                # STEP 23C-3:
                # COMPARE APPLICATION ANSWER
                # =============================================

                facts, invoices, sources, overall = application_score(
                    answer,
                    truth[question_id],
                )

                # =============================================
                # STORE THIS RUN
                # =============================================

                run_results.append(
                    {
                        "run": run_number,
                        "intent": predicted_intent,
                        "intent_correct": intent_correct,
                        "facts": facts,
                        "invoices": invoices,
                        "sources": sources,
                        "overall": overall,
                        "time": elapsed,
                        "return_code": return_code,
                        "answer": answer,
                    }
                )

            # -------------------------------------------------
            # Calculate average scores across repeated runs.
            # -------------------------------------------------

            intent_accuracy = (
                sum(1 for result in run_results if result["intent_correct"])
                / len(run_results)
                * 100
            )

            # -------------------------------------------------
            # Average only applicable metrics.
            # -------------------------------------------------

            fact_values = [
                result["facts"] for result in run_results if result["facts"] is not None
            ]

            invoice_values = [
                result["invoices"]
                for result in run_results
                if result["invoices"] is not None
            ]

            source_values = [
                result["sources"]
                for result in run_results
                if result["sources"] is not None
            ]

            average_facts = sum(fact_values) / len(fact_values) if fact_values else None

            average_invoices = (
                sum(invoice_values) / len(invoice_values) if invoice_values else None
            )

            average_sources = (
                sum(source_values) / len(source_values) if source_values else None
            )

            # Average application score.
            average_overall = sum(result["overall"] for result in run_results) / len(
                run_results
            )

            # Average response time.
            average_time = sum(result["time"] for result in run_results) / len(
                run_results
            )

            # -------------------------------------------------
            # Check whether every application run passed.
            # -------------------------------------------------

            application_pass = average_overall >= 80

            # -------------------------------------------------
            # Check whether every intent classification passed.
            # -------------------------------------------------

            intent_pass = intent_accuracy == 100

            # -------------------------------------------------
            # Overall question status.
            #
            # We require BOTH:
            #
            #     Intent classification >= 80%
            #
            # AND
            #
            #     Application answer >= 80%
            # -------------------------------------------------

            question_pass = intent_accuracy >= 80 and average_overall >= 80

            status = "PASS" if question_pass else "FAIL"

            # -------------------------------------------------
            # Print question result.
            # -------------------------------------------------

            print(
                f"{question_id} | "
                f"{status} | "
                f"Intent: {intent_accuracy:.0f}% | "
                f"Facts: {format_score(average_facts)} | "
                f"Complete: {format_score(average_invoices)} | "
                f"Sources: {format_score(average_sources)} | "
                f"Answer: {average_overall:.0f}% | "
                f"Avg Time: {average_time:.2f}s"
            )

            # -------------------------------------------------
            # If a question fails, show useful debugging data.
            # -------------------------------------------------

            if not question_pass:

                print(f"  Expected intent: " f"{expected_intent}")

                print(
                    f"  Predicted intents: "
                    f"{', '.join(result['intent'] for result in run_results)}"
                )

                print("  Application answers:")

                for result in run_results:

                    print(f"    Run {result['run']}:")

                    print(
                        "      "
                        + result["answer"].replace(
                            "\n",
                            "\n      ",
                        )
                    )

            # -------------------------------------------------
            # Store summarized result.
            # -------------------------------------------------

            all_results.append(
                {
                    "model": model,
                    "question": question_id,
                    "intent_accuracy": intent_accuracy,
                    "facts": average_facts,
                    "invoices": average_invoices,
                    "sources": average_sources,
                    "overall": average_overall,
                    "time": average_time,
                    "status": status,
                    "runs": run_results,
                }
            )

    # =====================================================
    # STEP 24: FINAL MODEL MATRIX
    # =====================================================

    print()
    print("=" * 80)
    print("FINAL MODEL EVALUATION MATRIX")
    print("=" * 80)

    print(
        f"{'Model':<20}"
        f"{'Intent':>10}"
        f"{'Facts':>10}"
        f"{'Complete':>12}"
        f"{'Sources':>10}"
        f"{'Answer':>10}"
        f"{'Avg Time':>12}"
    )

    print("-" * 84)

    model_summaries = []

    for model in MODELS:

        results = [result for result in all_results if result["model"] == model]

        # -------------------------------------------------
        # Intent accuracy.
        # -------------------------------------------------

        avg_intent = sum(result["intent_accuracy"] for result in results) / len(results)

        # -------------------------------------------------
        # Facts.
        # -------------------------------------------------

        fact_values = [
            result["facts"] for result in results if result["facts"] is not None
        ]

        avg_facts = sum(fact_values) / len(fact_values) if fact_values else None

        # -------------------------------------------------
        # Completeness.
        # -------------------------------------------------

        invoice_values = [
            result["invoices"] for result in results if result["invoices"] is not None
        ]

        avg_invoices = (
            sum(invoice_values) / len(invoice_values) if invoice_values else None
        )

        # -------------------------------------------------
        # Sources.
        # -------------------------------------------------

        source_values = [
            result["sources"] for result in results if result["sources"] is not None
        ]

        avg_sources = sum(source_values) / len(source_values) if source_values else None

        # -------------------------------------------------
        # Application answer accuracy.
        # -------------------------------------------------

        avg_answer = sum(result["overall"] for result in results) / len(results)

        # -------------------------------------------------
        # Average response time.
        # -------------------------------------------------

        avg_time = sum(result["time"] for result in results) / len(results)

        print(
            f"{model:<20}"
            f"{avg_intent:>9.1f}%"
            f"{format_score(avg_facts):>10}"
            f"{format_score(avg_invoices):>12}"
            f"{format_score(avg_sources):>10}"
            f"{avg_answer:>9.1f}%"
            f"{avg_time:>11.2f}s"
        )

        model_summaries.append(
            {
                "model": model,
                "intent": avg_intent,
                "facts": avg_facts,
                "invoices": avg_invoices,
                "sources": avg_sources,
                "answer": avg_answer,
                "time": avg_time,
            }
        )

    # =====================================================
    # STEP 25: MODEL RECOMMENDATION
    # =====================================================
    #
    # Selection logic:
    #
    # 1. Prefer a model with >= 80% intent accuracy.
    # 2. Prefer a model with >= 80% application accuracy.
    # 3. If both are reliable, prefer the faster model.
    #
    # We do NOT choose based on speed alone.
    #
    # =====================================================

    print()
    print("=" * 80)
    print("MODEL RECOMMENDATION")
    print("=" * 80)

    reliable_models = [
        summary
        for summary in model_summaries
        if (summary["intent"] >= 80 and summary["answer"] >= 80)
    ]

    if reliable_models:

        # Sort by:
        #
        # 1. Higher answer accuracy
        # 2. Higher intent accuracy
        # 3. Lower response time
        #
        recommended = sorted(
            reliable_models,
            key=lambda item: (
                -item["answer"],
                -item["intent"],
                item["time"],
            ),
        )[0]

        # If models have identical accuracy, the faster one
        # becomes the practical recommendation.
        same_accuracy = [
            item
            for item in reliable_models
            if (
                item["answer"] == recommended["answer"]
                and item["intent"] == recommended["intent"]
            )
        ]

        if len(same_accuracy) > 1:

            recommended = min(
                same_accuracy,
                key=lambda item: item["time"],
            )

        print(f"Recommended model: " f"{recommended['model']}")

        print()
        print(
            f"Reason: {recommended['model']} achieved "
            f"{recommended['intent']:.1f}% intent accuracy "
            f"and {recommended['answer']:.1f}% application "
            f"answer accuracy with an average response time "
            f"of {recommended['time']:.2f}s."
        )

        print()
        print(
            "Financial calculations are performed "
            "deterministically by Python, so the smaller "
            "local model is sufficient if it provides reliable "
            "intent classification."
        )

    else:

        print("No model reached the reliability threshold.")

    # =====================================================
    # STEP 26: EVALUATION INTERPRETATION
    # =====================================================

    print()
    print("=" * 80)
    print("HOW TO INTERPRET THESE RESULTS")
    print("=" * 80)

    print(
        "1. Intent accuracy measures how correctly Ollama "
        "understands the user's question."
    )

    print(
        "2. Facts, completeness and source scores measure "
        "the final application's answer."
    )

    print(
        "3. Financial calculations are NOT performed by the "
        "LLM. Python performs them deterministically."
    )

    print(
        "4. Therefore, high application accuracy does not "
        "mean the LLM can independently calculate finances."
    )

    print(
        "5. N/A means that a metric does not apply to that "
        "question and is excluded from its score."
    )

    print(
        "6. Repeated runs reduce the chance that one model "
        "response determines the entire evaluation."
    )

    # =====================================================
    # STEP 27: SCORING INFORMATION
    # =====================================================

    print()
    print("=" * 80)
    print("APPLICATION SCORING")
    print("=" * 80)

    print("Facts accuracy : 40%")

    print("Completeness   : 40%")

    print("Source rows    : 20%")

    print("PASS threshold : 80%")

    print(f"Repeated runs  : {REPEAT_RUNS}")

    print("=" * 80)


# =========================================================
# STEP 28: PYTHON ENTRY POINT
# =========================================================
#
# Run from the project root:
#
#     python scripts/evaluate_models.py
#
# =========================================================

if __name__ == "__main__":

    main()
