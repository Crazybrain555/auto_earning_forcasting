# Actuals Local Trust Status Migration Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every generated and consumed Actuals receipt state that it proves local consistency only, while preserving all diagnostic validation and fail-closed historical promotion behavior.

**Architecture:** Version the Actuals contract once and expose one canonical `locally_consistent_untrusted` status from the shared contract module. Keep the independent forecast-seal receipt explicit as `forecast_seal_receipt_status`, remove the ambiguous `receipt_verified` evaluation field, and make the nested Actuals receipt the evaluation's single source of truth for Actuals trust. The scorer continues all definition, source, numeric-literal, reconciliation, hash, and chronology checks unchanged.

**Tech Stack:** Python standard library, unittest/pytest-compatible tests, JSON templates, Markdown contract documentation.

---

### Task 1: Lock the new trust semantics with failing tests

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/tests/test_training_score.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/tests/test_promotion_evidence_contract.py`

1. Change scorer expectations to contract `training_actuals/3.2`, Actuals status `locally_consistent_untrusted`, explicit `forecast_seal_receipt_status`, and no legacy `receipt_verified` key.
2. Add promotion-contract coverage that rejects absent, mismatched, or falsely elevated Actuals trust status.
3. Run the focused tests and preserve the expected RED evidence before implementation.

### Task 2: Migrate the shared Actuals contract and scorer

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/_actuals_contract.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/score_training_forecast.py`

1. Define the version and trust status centrally.
2. Emit the new status in the content-derived receipt.
3. Replace the ambiguous external-seal boolean/string with an explicit seal-receipt status.
4. Retain all existing local semantic, provenance, hash, numeric, reconciliation, and chronology validation.

### Task 3: Make promotion consumption fail closed and unambiguous

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/scripts/validate_promotion_evidence.py`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/tests/test_promotion_evidence_contract.py`

1. Require a verified external seal receipt independently from the local Actuals status.
2. Require the nested receipt's single Actuals status to be the canonical local-only status; do not add a duplicate top-level Actuals state.
3. Keep `historical_training` / `validated_on_holdout` blocked while no trusted append-only or signed host registry exists.

### Task 4: Migrate template and documentation

**Files:**
- Modify: `forecasting-skills/technology-company-forecasting-trainer/assets/templates/training_actuals_template.json`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/SKILL.md`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/references/historical-training-loop.md`
- Modify: `forecasting-skills/technology-company-forecasting-trainer/references/profit-forecast-accuracy.md`

1. Bump the template schema version to 3.2.
2. Document what each receipt proves and explicitly deny any external-truth interpretation.
3. Remove stale `validated` / `receipt_verified` wording for this contract.

### Task 5: Verify without release generation

1. Run the focused scoring and promotion tests.
2. Run targeted searches for stale contract/status names.
3. Run the package self-test and relevant regression suite.
4. Do not build the live release, commit, or push.
