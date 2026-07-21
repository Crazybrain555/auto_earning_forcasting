import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "scripts/project_historical_capability_view.py"
    spec = importlib.util.spec_from_file_location("historical_capability_projection", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workspace(path: Path) -> Path:
    path.mkdir()
    (path / "mode_config.json").write_text(
        json.dumps(
            {
                "run_mode": "historical_train",
                "phase": "forecast",
                "actuals_retrieval_allowed": False,
                "as_of": "2020-01-31T00:00:00Z",
            }
        )
    )
    (path / "training_state.json").write_text(
        json.dumps({"case_id": "CASE-1", "case_role": "validation", "phase": "forecast"})
    )
    (path / "run_manifest.json").write_text(
        json.dumps(
            {
                "contract_version": "2.0",
                "method_version": "10.0.0+git:test",
                "run_id": "run://CASE-1",
                "entity": "Example",
                "security": "EX",
                "as_of": "2020-01-31T00:00:00Z",
                "run_mode": "historical_train",
                "training_iteration_id": "ITER-1",
                "purpose": "forecast revenue and attributable profit",
                "fiscal_calendar": "calendar",
                "currency": "USD",
                "accounting_basis": {},
                "horizons": {"annual_years": 3},
                "analysis_primitives": [],
                "materiality_routes": {},
                "readiness_target": "research-grade",
            }
        )
    )
    (path / "source_manifest.json").write_text(
        json.dumps(
            {
                "as_of": "2020-01-31T00:00:00Z",
                "entity": "Example",
                "security": "EX",
                "sources": [
                    {
                        "source_id": "SRC-1",
                        "published_at": "2020-01-15T00:00:00Z",
                        "available_at": "2020-01-16T00:00:00Z",
                        "retrieved_at": "2020-01-17T00:00:00Z",
                        "location": "source://one",
                        "source_time_status": "eligible_pre_cutoff",
                        "forecast_permission": "eligible",
                        "as_of_valid": True,
                    }
                ],
                "conflicts": [],
            }
        )
    )
    (path / "claim_ledger.jsonl").write_text("{}\n")
    return path


def test_projection_is_current_shaped_and_excludes_training_authority(tmp_path):
    module = _module()
    workspace = _workspace(tmp_path / "case")
    output = tmp_path / "projection"

    result = module.project_view(
        workspace,
        output,
        "operating_model",
        boundary_validator=lambda _workspace: '{"passed": true}',
    )

    assert result["specialist_access"] == "projected_files_only"
    assert result["unrestricted_retrieval"] is False
    decision = json.loads((output / "decision_bundle.json").read_text())
    sources = json.loads((output / "source_records.json").read_text())
    assert "orchestrator_acceptance_ref" in decision
    assert "snapshot_at" in decision
    assert not ({"as_of", "run_mode", "training_iteration_id"} & set(decision))
    assert not (
        {"source_time_status", "forecast_permission", "as_of_valid", "cutoff"}
        & set(sources["sources"][0])
    )
    assert (output / "claim_ledger.jsonl").is_file()
    assert not (output / "mode_config.json").exists()
    assert not (output / "training_state.json").exists()


@pytest.mark.parametrize("poison", ["sealed", "actuals"])
def test_projection_refuses_reentry_after_outcome_channel_opens(tmp_path, poison):
    module = _module()
    workspace = _workspace(tmp_path / "case")
    if poison == "sealed":
        mode = json.loads((workspace / "mode_config.json").read_text())
        mode.update({"phase": "sealed", "actuals_retrieval_allowed": True})
        (workspace / "mode_config.json").write_text(json.dumps(mode))
        state = json.loads((workspace / "training_state.json").read_text())
        state["phase"] = "sealed"
        (workspace / "training_state.json").write_text(json.dumps(state))
        (workspace / "forecast_seal.json").write_text("{}")
    else:
        vault = workspace / "actuals_vault"
        vault.mkdir()
        (vault / "target.json").write_text('{"revenue": 999}')

    with pytest.raises(module.ProjectionError):
        module.project_view(
            workspace,
            tmp_path / "projection",
            "financial_forecast",
            boundary_validator=lambda _workspace: '{"passed": true}',
        )
