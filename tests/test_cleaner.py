import pandas as pd

from src.cleaner import parse_date, parse_money


def test_parse_money():
    assert parse_money("Rs. 781,057") == 781057.0
    assert parse_money("₹12,345.50") == 12345.50
    assert parse_money("-84,000") == -84000.0


def test_parse_dates():
    assert parse_date("2025-01-08") == pd.Timestamp("2025-01-08")
    assert parse_date("08.02.2025") == pd.Timestamp("2025-02-08")
    assert parse_date("04-Apr-2024") == pd.Timestamp("2024-04-04")
