import sys
from pathlib import Path

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.cleaner import clean_ledger, save_cleaned_ledger

RAW_FILE = BASE_DIR / "data" / "ledger_2024_25.csv"
CLEANED_FILE = BASE_DIR / "data" / "ledger_cleaned.csv"


def main():
    df = clean_ledger(RAW_FILE)

    save_cleaned_ledger(df, CLEANED_FILE)

    print(f"Raw rows: {len(df)}")
    print(f"Cleaned CSV saved to: {CLEANED_FILE}")


if __name__ == "__main__":
    main()
