# JPAIS-MED-REF: Physician Oversight & Clinical Interaction Standards
**Series Code:** JPAIS-MED-REF-002  
**Target Audience:** Chief Medical Officers, Attending Physicians, Clinical Informaticists  
**Status:** Approved  

---

## 1. Primary Rule of Clinical Primacy

1. **Non-Delegable Responsibility**: The attending physician of record retains ultimate clinical, legal, and ethical responsibility for patient diagnosis, care pathways, and clinical interventions.
2. **Advisory Posture**: AI-generated inferences, risk scores, and candidate diagnoses are advisory tools and must never override clinical judgment.

---

## 2. Physician Interaction Protocol

### A. Presentation of AI Insights
Whenever an AI inference is displayed in the Electronic Medical Record (EMR/RME):
* The interface must display the **underlying evidence card** (`CLM-ID`), similarity confidence score, and primary citation link.
* Known contraindications, uncertainty estimates, and model limitations must remain visible alongside the prediction.

### B. The Physician Override Workflow
1. Physicians may reject, modify, or accept any AI recommendation without institutional penalty.
2. **Override Documentation**: If a high-acuity (Tier 2 or Tier 3) recommendation is dismissed or overridden, the EMR must prompt for a brief clinical rationale (e.g., *"Patient has unmodeled atypical presentation"* or *"Clinical history contradicts automated reading"*).
3. Overrides are logged to the continuous quality improvement (CQI) telemetry stream to monitor model performance and bias.

---

## 3. Digital Signatures & Attestation Requirements

To satisfy evidentiary transaction binding:
* Each clinical order influenced by AI must capture the active model version (`v-med-ref-X.X.X`), input feature hash, prediction payload, and the clinician's digital signature timestamp.
* Audit trails must remain immutable, tamper-evident, and queryable for retrospective clinical governance audits.
