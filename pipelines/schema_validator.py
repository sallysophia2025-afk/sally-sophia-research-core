import json
from pathlib import Path
import jsonschema

DUBLIN_CORE_SCHEMA_PATH = Path("config/dublin_core_schema.json")
SCHEMA_ORG_PATH = Path("config/schema_org_ld.json")
INPUT_PROCESSED_JSON = Path("data/processed/claims_processed.json")
OUTPUT_JSONLD_PATH = Path("data/processed/claims_schema_org.jsonld")

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def to_dublin_core(claim: dict) -> dict:
    return {
        "identifier": claim.get("claim_id", ""),
        "source_identifier": claim.get("source_id", ""),
        "title": claim.get("claim_id", ""),
        "subject": f"Medical AI Governance: {claim.get('claim_type', 'GENERAL')}",
        "description": claim.get("claim_text", ""),
        "publisher": "SALLY SOPHIA Research Core",
        "coverage": claim.get("jurisdiction", "Global"),
        "authority": claim.get("authority", "Unspecified"),
        "date": claim.get("last_reviewed", "2026-09-24"),
        "type": "ClinicalEvidenceClaim",
        "rights": "CC-BY-4.0"
    }

def to_schema_org(claim: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "MedicalEntity",
        "@id": f"https://medicalai.miraheze.org/wiki/JPAIS-MED-REF#{claim.get('claim_id')}",
        "name": f"Evidence Claim: {claim.get('claim_id')}",
        "description": claim.get("claim_text", ""),
        "publishingPrinciples": "https://github.com/sallysophia2025-afk/sally-sophia-research-core",
        "legislationJurisdiction": claim.get("jurisdiction", "Global"),
        "citation": claim.get("evidence_url", ""),
        "status": claim.get("verification_status", "NOT_VERIFIED")
    }

def validate_schemas():
    print("--- Stage 03: Executing Formal Schema Validation ---")
    dc_schema = load_json(DUBLIN_CORE_SCHEMA_PATH)
    so_schema = load_json(SCHEMA_ORG_PATH)
    claims = load_json(INPUT_PROCESSED_JSON)

    print(f"Validating {len(claims)} records against schema protocols...")
    
    jsonld_bundle = {
        "@context": "https://schema.org",
        "@graph": []
    }

    dc_errors = 0
    so_errors = 0

    for idx, claim in enumerate(claims, start=1):
        # 1. Dublin Core Validation
        dc_record = to_dublin_core(claim)
        try:
            jsonschema.validate(instance=dc_record, schema=dc_schema)
        except jsonschema.ValidationError as e:
            print(f"✗ Dublin Core Error in row {idx} ({claim.get('claim_id')}): {e.message}")
            dc_errors += 1

        # 2. Schema.org JSON-LD Validation
        so_record = to_schema_org(claim)
        try:
            jsonschema.validate(instance=so_record, schema=so_schema)
            jsonld_bundle["@graph"].append(so_record)
        except jsonschema.ValidationError as e:
            print(f"✗ Schema.org Error in row {idx} ({claim.get('claim_id')}): {e.message}")
            so_errors += 1

    if dc_errors == 0 and so_errors == 0:
        print(f"✓ All {len(claims)} records 100% compliant with Dublin Core & Schema.org JSON-LD")
    else:
        raise ValueError(f"Validation failed: {dc_errors} DC errors, {so_errors} Schema.org errors")

    # Save canonical JSON-LD graph bundle
    with open(OUTPUT_JSONLD_PATH, "w", encoding="utf-8") as f:
        json.dump(jsonld_bundle, f, indent=2, ensure_ascii=False)
    print(f"✓ Exported validated JSON-LD bundle to {OUTPUT_JSONLD_PATH}")
    return True

if __name__ == "__main__":
    validate_schemas()
