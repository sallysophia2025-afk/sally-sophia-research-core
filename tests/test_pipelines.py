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

# Policy verification tests
JPAIS_DIR = Path("policies/JPAIS_MED_REF")

def test_jpais_policy_blueprints_exist():
    assert (JPAIS_DIR / "JPAIS_BLUEPRINT.md").exists()
    assert (JPAIS_DIR / "ATTESTATION_THRESHOLDS.json").exists()
    assert (JPAIS_DIR / "PHYSICIAN_OVERSIGHT_STANDARDS.md").exists()
    assert (JPAIS_DIR / "README.md").exists()

def test_attestation_thresholds_valid_json():
    import json
    with open(JPAIS_DIR / "ATTESTATION_THRESHOLDS.json") as f:
        data = json.load(f)
    assert "risk_tiers" in data
    assert "TIER_1_INFORMATIONAL" in data["risk_tiers"]
    assert "TIER_2_CLINICAL_DECISION_SUPPORT" in data["risk_tiers"]
    assert "TIER_3_HIGH_ACUITY_INTERVENTION" in data["risk_tiers"]
    assert data["drift_circuit_breakers"]["population_stability_index_trip"] == 0.25

# Generator verification tests
def test_generator_module_exists_and_imports():
    from src.generator import deterministic_grounded_summary, SYSTEM_INSTRUCTION
    assert len(SYSTEM_INSTRUCTION) > 100
    mock_records = [{
        "claim_id": "CLM-ACAD-031",
        "claim_text": "Test claim text",
        "authorities": ["KMK 1423"],
        "jurisdictions": ["Indonesia"],
        "evidence_url": "https://jdih.kemkes.go.id"
    }]
    summary = deterministic_grounded_summary("Test Query", mock_records)
    assert "CLM-ACAD-031" in summary
    assert "KMK 1423" in summary
    assert "https://jdih.kemkes.go.id" in summary
