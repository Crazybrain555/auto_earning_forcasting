"""Strict delivery must never downgrade an undeclared contract to legacy mode."""
import json
import subprocess
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts/validate_delivery.py"


def _run(tmp_path: Path, contract_version):
    workspace = tmp_path / "run"
    workspace.mkdir()
    manifest = {
        "run_id": "run://TEST",
        "entity": "TEST",
        "security": "TEST",
        "as_of": "2026-07-20T00:00:00Z",
        "purpose": "test",
        "fiscal_calendar": "calendar",
        "currency": "USD",
        "accounting_basis": "GAAP",
        "horizons": {"annual_years": 3},
        # These legacy fields must not make strict mode accept or route v1.
        "selected_mechanisms": ["unit-volume-price-cost"],
        "mechanism_weights": {"unit-volume-price-cost": 1.0},
        "readiness_target": "research-grade",
        "phase_status": {"contract": "complete"},
    }
    if contract_version is not None:
        manifest["contract_version"] = contract_version
    (workspace / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--workspace", str(workspace), "--strict"],
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return result, {item["check"]: item for item in payload["checks"]}


def test_strict_rejects_missing_contract_version_instead_of_legacy_fallback(tmp_path):
    result, checks = _run(tmp_path, None)
    assert result.returncode != 0
    gate = checks["manifest:contract-version-v2"]
    assert not gate["passed"]
    assert "missing" in gate["detail"].lower()
    assert not checks["manifest:v2-no-manual-weights"]["passed"]


def test_strict_rejects_non_v2_contract_version(tmp_path):
    result, checks = _run(tmp_path, "1.9")
    assert result.returncode != 0
    gate = checks["manifest:contract-version-v2"]
    assert not gate["passed"]
    assert "1.9" in gate["detail"]


def test_strict_recognizes_explicit_v2_contract(tmp_path):
    _, checks = _run(tmp_path, "2.0")
    assert checks["manifest:contract-version-v2"]["passed"]


def test_delivery_contract_documents_strict_v2_no_fallback_rule():
    text = (SKILL / "references/full-company-delivery-contract.md").read_text(encoding="utf-8").lower()
    for concept in (
        "strict validation requires an explicit major-version-2 `contract_version`",
        "no legacy fallback",
        "manual importance weights",
    ):
        assert concept in text, concept
