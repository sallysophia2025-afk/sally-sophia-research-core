# JPAIS-MED-REF: Clinical AI Governance & Evidentiary Integrity Blueprint
**Series Code:** JPAIS-MED-REF-001  
**Architectural Layer:** Layer 4 (Knowledge Content & Governance)  
**Standard:** Entity Verification & Jurisprudential Grounding Protocol  
**Version:** 1.0.0  

The **Jurisprudential & Algorithmic Integrity System for Medicine (JPAIS)** defines mandatory governance, auditability, and evidentiary transaction binding across the clinical AI lifecycle.

---

## The Six Core Pillars

### Pillar 1: Jurisprudential Grounding
* **Legal Alignment**: Every model deployment must cite and verify compliance with prevailing health legislation (e.g., UU No. 17/2023, Permenkes No. 24/2022, and KMK No. HK.01.07/Menkes/1423/2022).
* **Data Sovereignty & Custody**: Clinical medical records belong strictly to the healthcare institution (Fasyankes). Processing and feature extraction must preserve local institutional governance and avoid cross-border data leakage.

### Pillar 2: Pre-Deployment Safety Validation
* **Reporting Compliance**: Evaluation protocols must align with CONSORT-AI, SPIRIT-AI, and TRIPOD+AI standards.
* **Separation of Cohorts**: Strict patient-level separation across training, validation, and test splits to eliminate data leakage.
* **Performance Floor**: Minimum area under the receiver operating characteristic curve (AUROC) $\ge 0.85$ and expected calibration error (ECE) $\le 0.05$ on external validation cohorts prior to clinical trial authorization.

### Pillar 3: Algorithmic Transparency & Attestation
* **Cryptographic Attestation**: Every deployed model weight file must carry a verifiable SHA-256 hash registered in repository metadata.
* **Dataset Cards**: Documented provenance including inclusion/exclusion criteria, demographics, missingness, and label sources.

### Pillar 4: Physician Oversight & Autonomy Thresholds
* **Assistive Boundary**: AI outputs serve strictly as decision support tools; they never independently sign clinical orders or prescribe treatment.
* **Mandatory Attestation**: Clinical decisions incorporating AI recommendations require explicit physician authentication and attestation in the EMR record.

### Pillar 5: Continuous Surveillance & Circuit Breakers
* **Covariate Shift Detection**: Automated daily Kolmogorov-Smirnov and Population Stability Index (PSI) tests on incoming clinical data streams.
* **Circuit Breaker Trigger**: If PSI $> 0.25$ or unexplained error spikes occur, the system automatically revokes autonomous recommendation mode and falls back to manual clinical protocols.

### Pillar 6: MED-REF Evidentiary Binding
* **Canonical Identifiers**: Every factual medical claim is bound to a stable identifier (`CLM-[TYPE]-[ID]`) and primary regulatory source (`SRC-[HASH]`).
* **Traceable Citations**: Model predictions must resolve to verifiable legal articles, clinical practice guidelines, or peer-reviewed literature.
