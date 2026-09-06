from pathlib import Path

from src.cleaner import clean_ledger
from src.anomaly_detector import data_quality_report

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "data" / "ledger_2024_25.csv"


def test_data_quality_report():
    df = clean_ledger(CSV_FILE)

    report = data_quality_report(df)

    assert len(report["future_invoices"]) == 1
    assert len(report["payment_before_invoice"]) == 1
    assert len(report["missing_taxable_amount"]) == 1
    assert len(report["missing_gstin"]) == 4
    assert len(report["gst_mismatches"]) == 1
    assert len(report["duplicate_invoices"]) == 1
