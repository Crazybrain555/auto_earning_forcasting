# Source and Claim Epistemic Authority Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent opinions or statements from becoming factual causal/external tests through source-type renaming while preserving legitimate historical facts, independent measurements, technical bounds, management plans, and scenario-only use.

**Architecture:** Add one controlled `epistemic_class` to SourceRecord and make it, together with controlled authority, independence, directness, and root provenance, the sole runtime basis for epistemic permission; `source_type` and `role` remain retrieval descriptions only. Every model-changing `future_execution` or `external_state` claim must use a causal/external test from an `independent_external_observation` root record and carry a frozen authority review that binds both the exact source IDs and their epistemic classes. Opinion documents may cite observations, but the underlying observation must be represented as its own original factual SourceRecord and linked directly.

**Tech Stack:** Python standard library, JSON Schema, JSON/JSONL templates, pytest, Markdown method contracts.

---

### Task 1: Lock the bypass and legitimate cases with RED tests

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/tests/test_claim_permission_contract.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/tests/test_forward_evidence_authority_contract.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/tests/test_forward_signal_claim_binding.py`

1. Add `epistemic_class` to test SourceRecords and class bindings to frozen review fixtures.
2. Add the exact `expert_interview_transcript` + `leading_indicator` + causal-test exploit and require rejection.
3. Add positive cases for official history, independent external measurements, technical bounds, management plans, and scenario-only opinions.
4. Add rejection for missing/unknown/incompatible classes and stale review class bindings.
5. Run focused tests and retain the expected RED evidence.

### Task 2: Centralize SourceRecord epistemic classification

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/provenance_contract.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/validate_delivery.py`

1. Define the controlled class enum and compatibility rules once in the shared provenance contract.
2. Remove source-type/role inference from claim authority decisions.
3. Permit causal/external tests only from direct, independent, original `independent_external_observation` records.
4. Require frozen authority review for every model-changing predictive proposition and bind it to the source-class map.

### Task 3: Align research and forward runtime consumers

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/validate_research_completeness.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/validate_forward_evidence_workspace.py`
- Modify fixtures only where the new required contract is exercised.

1. Validate epistemic classes at research ingest.
2. Validate exact source-class maps in review judgments.
3. Ensure forward Base hard-anchor logic consumes the same shared semantic contract.

### Task 4: Migrate schemas and templates

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/assets/schemas/source_record.schema.json`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/assets/templates/source_manifest_template.json`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/assets/templates/research_quality_review_template.json`
- Modify affected test and package fixtures.

1. Require the controlled `epistemic_class` enum in SourceRecord v3.
2. Expose the class in the source template and the exact source-class review binding in the review template contract.
3. Keep open `source_type` explicitly descriptive and non-authoritative.

### Task 5: Update canonical method documentation

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/references/research-sop.md`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/references/core-source-and-evidence.md`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/assets/method_system.json`

1. Document the controlled classes and proposition-specific boundaries.
2. State that opinion documents cannot self-promote; an underlying observation is a separate root SourceRecord.
3. Preserve management-plan and scenario-only permissions without treating either as external fact.

### Task 6: Verify without live or Git operations

1. Run claim-permission tests, forward-evidence tests, and material-assumption tests.
2. Run focused delivery/research contract regressions affected by SourceRecord fixtures.
3. Search for remaining source-type authority inference and run `git diff --check`.
4. Do not generate or edit the live release, commit, or push.
