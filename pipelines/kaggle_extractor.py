import csv
import json
from pathlib import Path
import pandas as pd

RAW_DATA_PATH = Path("data/raw/claims.csv")
PROCESSED_DIR = Path("data/processed")

def extract_and_transform():
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw data file not found at {RAW_DATA_PATH}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    clean_rows = []
    header = []

    with open(RAW_DATA_PATH, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]
        expected_cols = len(header)  # 11 columns

        for line_no, row in enumerate(reader, start=2):
            if not row or not any(row):
                continue

            # Auto-repair rows with duplicate empty commas between authority and evidence_url
            if len(row) == expected_cols + 1 and row[8] == "" and row[9] == "":
                del row[9]

            # Trim trailing empty fields if present
            while len(row) > expected_cols and row[-1] == "":
                row.pop()

            if len(row) == expected_cols:
                clean_rows.append([cell.strip() for cell in row])
            else:
                print(f"Warning: Skipped line {line_no} (found {len(row)} fields, expected {expected_cols})")

    df = pd.DataFrame(clean_rows, columns=header)

    # Export cleaned CSV
    processed_csv = PROCESSED_DIR / "claims_processed.csv"
    df.to_csv(processed_csv, index=False)
    print(f"✓ Saved processed CSV to {processed_csv} ({len(df)} records)")

    # Export canonical JSON
    processed_json = PROCESSED_DIR / "claims_processed.json"
    with open(processed_json, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, indent=2, ensure_ascii=False)
    print(f"✓ Saved canonical JSON to {processed_json}")

if __name__ == "__main__":
    extract_and_transform()
