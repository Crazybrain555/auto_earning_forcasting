#!/usr/bin/env python3
"""Write historical benchmark observations without granting release authority."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


SCHEMA_VERSION = "legacy-backtest-diagnostics/v1"


def write_legacy_backtest_diagnostics(
    output_dir: Path,
    result: dict,
    threshold_observations: Mapping[str, bool],
) -> None:
    """Persist metrics and old threshold comparisons as separate diagnostics.

    These retrospective fixtures are useful for regression archaeology and
    ablation.  They are not clean promotion evidence, so a false observation
    is preserved rather than converted into a process exit code.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    observations = {str(key): bool(value) for key, value in threshold_observations.items()}
    diagnostic = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_only": True,
        "promotion_authority": "none",
        "metrics_artifact": "metrics.json",
        "threshold_observations": observations,
        "interpretation": (
            "Historical thresholds are retained for reproducibility only; "
            "they neither pass nor fail a method release."
        ),
    }
    result.pop("gate_results", None)
    result["legacy_threshold_diagnostics"] = {
        "artifact": "diagnostics.json",
        "diagnostic_only": True,
        "promotion_authority": "none",
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "diagnostics.json").write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
