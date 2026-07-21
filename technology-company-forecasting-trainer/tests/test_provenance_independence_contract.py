"""Source independence must be a shared root-provenance contract, not labels."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
FORWARD_VALIDATOR = SKILL / "scripts/validate_forward_evidence_workspace.py"


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def test_forward_clusters_with_one_root_original_are_not_independent(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "run_manifest.json").write_text(json.dumps({
        "as_of": "2026-07-20T23:59:59Z",
        "forward_evidence_min_signals": 6,
        "forward_evidence_min_independent_clusters": 2,
        "technology_trend_min_signals": 2,
    }), encoding="utf-8")
    (workspace / "source_manifest.json").write_text(json.dumps({
        "sources": [
            {
                "source_id": "S1", "publisher": "Shared Publisher",
                "authors": ["Shared Team"], "root_original_source_id": "S1",
                "derived_from_source_id": None, "common_origin": False,
                "independence_cluster": "C1", "measurement_method_id": "shared-panel",
            },
            {
                "source_id": "S2", "publisher": "Shared Publisher",
                "authors": ["Shared Team"], "root_original_source_id": "S1",
                "derived_from_source_id": "S1", "common_origin": True,
                "independence_cluster": "C2", "measurement_method_id": "renamed-panel",
            },
        ]
    }), encoding="utf-8")
    signal_header = [
        "signal_id", "source_id", "publisher", "published_at", "source_family",
        "evidence_tier", "evidence_role", "independence_cluster", "allowed_use",
        "model_driver",
    ]
    _write_csv(workspace / "forward_signal_cards.csv", signal_header, [
        ["F1", "S1", "Shared Publisher", "2026-07-01", "measurement", "E1", "direct_measurement", "C1", "base_driver", "demand"],
        ["F2", "S2", "Shared Publisher", "2026-07-02", "industry-research", "E3", "cross_check", "C2", "base_driver", "demand"],
        ["F3", "S1", "Shared Publisher", "2026-07-03", "official-dialogue", "E1", "guidance", "C1", "monitor", "price"],
        ["F4", "S2", "Shared Publisher", "2026-07-04", "technical-paper-standard", "E2", "feasibility_bound", "C2", "scenario_only", "yield"],
        ["F5", "S1", "Shared Publisher", "2026-07-05", "technical-paper-standard", "E2", "failure_boundary", "C1", "scenario_only", "yield"],
        ["F6", "S2", "Shared Publisher", "2026-07-06", "news-event", "E4", "monitor_trigger", "C2", "monitor", "supply"],
    ])
    _write_csv(
        workspace / "historical_query_log.csv",
        ["query_id", "future_outcome_terms_used", "cutoff"],
        [[f"Q{i}", "false", "2026-07-20T23:59:59Z"] for i in range(1, 4)],
    )
    _write_csv(
        workspace / "source_independence_map.csv",
        [
            "source_id", "cluster_id", "root_original_source_id",
            "derived_from_source_id", "relationship", "common_origin", "publisher",
            "authors", "measurement_method_id", "independence_basis", "notes",
        ],
        [
            ["S1", "C1", "S1", "", "original", "false", "Shared Publisher", "Shared Team", "shared-panel", "root observation", ""],
            ["S2", "C2", "S1", "S1", "transformation", "true", "Shared Publisher", "Shared Team", "renamed-panel", "same measurement republished", ""],
        ],
    )
    (workspace / "report.md").write_text("Forward evidence review", encoding="utf-8")
    (workspace / "red_team.md").write_text(
        "Source independence and common origin reviewed", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(FORWARD_VALIDATOR), "--workspace", str(workspace), "--strict"],
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "root" in output or "common origin" in output or "derived" in output


def test_provenance_fields_ship_in_templates_schemas_and_live_package_contract() -> None:
    source_template = json.loads(
        (SKILL / "assets/templates/source_manifest_template.json").read_text(encoding="utf-8")
    )["sources"][0]
    source_schema = json.loads(
        (SKILL / "assets/schemas/source_record.schema.json").read_text(encoding="utf-8")
    )
    required = {
        "root_original_source_id", "derived_from_source_id", "common_origin",
        "independence_cluster", "authors", "measurement_method_id",
    }
    assert required <= set(source_template)
    assert required <= set(source_schema["required"])

    with (SKILL / "assets/templates/source_independence_map_template.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        map_header = set(next(csv.reader(handle)))
    assert {
        "source_id", "root_original_source_id", "derived_from_source_id",
        "common_origin", "publisher", "authors", "measurement_method_id",
    } <= map_header

    technical_schema = json.loads(
        (SKILL / "assets/schemas/technical_evidence_record.schema.json").read_text(
            encoding="utf-8"
        )
    )
    bridge_schema = technical_schema["properties"]["production_transfer_bridge"]
    assert bridge_schema.get("$ref") == "#/$defs/structuredNumericBridge"

    profile = json.loads((SKILL / "assets/profile.json").read_text(encoding="utf-8"))
    assert "provenance_contract.py" in profile["runtime_scripts"]


def test_method_forbids_cluster_renaming_and_narrative_numeric_bridges() -> None:
    data_method = (SKILL / "references/data-quality-and-triangulation.md").read_text(
        encoding="utf-8"
    ).lower()
    technical_method = (SKILL / "references/technology-commercialization-and-ip.md").read_text(
        encoding="utf-8"
    ).lower()
    for term in (
        "root_original_source_id", "derived_from_source_id", "common_origin",
        "structured numeric bridge", "narrative formula",
    ):
        assert term in data_method
    for term in (
        "root original", "experimental team", "measurement method",
        "production transfer bridge", "structured",
    ):
        assert term in technical_method
