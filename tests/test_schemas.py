import json
from pathlib import Path
import pytest
import jsonschema

from pipelines.schema_validator import to_dublin_core, to_schema_org

PROCESSED_JSON = Path("data/processed/claims_processed.json")
DC_SCHEMA = Path("config/dublin_core_schema.json")
SO_SCHEMA = Path("config/schema_org_ld.json")

@pytest.fixture(scope="module")
def claims_data():
    assert PROCESSED_JSON.exists(), "claims_processed.json must exist"
    with open(PROCESSED_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def schemas():
    with open(DC_SCHEMA, "r") as f:
        dc = json.load(f)
    with open(SO_SCHEMA, "r") as f:
        so = json.load(f)
    return dc, so

def test_claims_count_and_keys(claims_data):
    assert len(claims_data) >= 47
    required_keys = {"claim_id", "source_id", "claim_text", "status", "verification_status"}
    for claim in claims_data:
        assert required_keys.issubset(claim.keys())
        assert claim["claim_id"].startswith("CLM-")
        assert len(claim["claim_text"]) > 0

def test_dublin_core_compliance(claims_data, schemas):
    dc_schema, _ = schemas
    for claim in claims_data:
        record = to_dublin_core(claim)
        jsonschema.validate(instance=record, schema=dc_schema)

def test_schema_org_jsonld_compliance(claims_data, schemas):
    _, so_schema = schemas
    for claim in claims_data:
        record = to_schema_org(claim)
        jsonschema.validate(instance=record, schema=so_schema)
