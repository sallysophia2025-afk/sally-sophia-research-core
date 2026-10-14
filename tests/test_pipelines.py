from pathlib import Path
import pandas as pd
import pytest

PROCESSED_CSV = Path("data/processed/claims_processed.csv")
PROCESSED_JSON = Path("data/processed/claims_processed.json")
SCHEMA_ORG_JSONLD = Path("data/processed/claims_schema_org.jsonld")

def test_processed_files_exist():
    assert PROCESSED_CSV.exists(), "Processed CSV must exist"
    assert PROCESSED_JSON.exists(), "Processed JSON must exist"
    assert SCHEMA_ORG_JSONLD.exists(), "Schema.org JSON-LD bundle must exist"

def test_csv_structure_and_no_missing_critical():
    df = pd.read_csv(PROCESSED_CSV)
    assert len(df) >= 47
    assert "claim_id" in df.columns
    assert "claim_text" in df.columns
    assert df["claim_id"].isnull().sum() == 0
    assert df["claim_text"].isnull().sum() == 0
