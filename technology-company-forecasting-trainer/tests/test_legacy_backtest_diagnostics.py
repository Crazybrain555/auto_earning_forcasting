"""Legacy benchmark thresholds are observations, never release decisions."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.diagnostic_benchmark

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
HELPER_PATH = SKILL / "scripts/legacy_backtest_diagnostics.py"


CASES = (
    (
        "broad",
        "run_backtest.py",
        ("--benchmark", "new_value_chain_benchmark.csv", "--cases", "new_cases.json"),
    ),
    (
        "equipment",
        "run_equipment_backtest.py",
        ("--benchmark", "equipment_benchmark_v62.csv", "--cases", "equipment_cases_v62.json"),
    ),
    (
        "marvell",
        "run_marvell_backtest.py",
        ("--benchmark", "marvell_benchmark_v63.csv", "--cases", "marvell_cases_v63.json"),
    ),
    (
        "aws",
        "run_aws_backtest.py",
        ("--benchmark", "aws_benchmark_v71.csv", "--cases", "aws_cases_v71.json"),
    ),
    (
        "netflix",
        "run_netflix_backtest.py",
        ("--benchmark", "netflix_benchmark_v72.csv", "--cases", "netflix_cases_v72.json", "--name", "netflix"),
    ),
    (
        "nvidia",
        "run_nvidia_backtest.py",
        ("--benchmark", "nvidia_benchmark_v72.csv", "--cases", "nvidia_cases_v72.json", "--name", "nvidia"),
    ),
    (
        "amd-intel",
        "run_amd_intel_backtest.py",
        ("--cases", "amd_intel_cases_v75.json"),
    ),
    (
        "forward-evidence",
        "run_forward_evidence_backtest.py",
        ("--cases", "forward_evidence_cases_v74.json"),
    ),
)


def _command(script: str, raw_args: tuple[str, ...], output: Path) -> list[str]:
    command = [sys.executable, str(SKILL / "scripts" / script)]
    index = 0
    while index < len(raw_args):
        flag = raw_args[index]
        value = raw_args[index + 1]
        if flag in {"--benchmark", "--cases"}:
            value = str(SKILL / "assets/benchmarks" / value)
        command.extend((flag, value))
        index += 2
    command.extend(("--output-dir", str(output)))
    return command


@pytest.mark.parametrize(("case_name", "script", "raw_args"), CASES)
def test_legacy_backtest_emits_non_promotion_diagnostics(
    tmp_path: Path,
    case_name: str,
    script: str,
    raw_args: tuple[str, ...],
) -> None:
    output = tmp_path / case_name
    result = subprocess.run(
        _command(script, raw_args, output), capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr

    metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    diagnostic = json.loads((output / "diagnostics.json").read_text(encoding="utf-8"))
    assert metrics.get("metrics"), case_name
    assert "gate_results" not in metrics
    assert metrics["legacy_threshold_diagnostics"] == {
        "artifact": "diagnostics.json",
        "diagnostic_only": True,
        "promotion_authority": "none",
    }
    assert diagnostic["schema_version"] == "legacy-backtest-diagnostics/v1"
    assert diagnostic["diagnostic_only"] is True
    assert diagnostic["promotion_authority"] == "none"
    observations = diagnostic["threshold_observations"]
    assert observations and all(isinstance(value, bool) for value in observations.values())


def test_failed_legacy_threshold_is_preserved_without_becoming_a_failure(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("legacy_diagnostics_test", HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    result = {"model_version": "synthetic", "metrics": {"holdout": {"error": 0.99}}}
    module.write_legacy_backtest_diagnostics(
        tmp_path,
        result,
        {"historical_error_below_old_threshold": False},
    )

    diagnostic = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostic["threshold_observations"] == {
        "historical_error_below_old_threshold": False
    }
    assert diagnostic["diagnostic_only"] is True
    assert diagnostic["promotion_authority"] == "none"


def test_backtest_result_schema_links_diagnostics_instead_of_defining_a_gate() -> None:
    schema = json.loads(
        (SKILL / "assets/schemas/backtest_result.schema.json").read_text(encoding="utf-8")
    )
    assert "gate_results" not in schema["properties"]
    assert "legacy_threshold_diagnostics" in schema["required"]
