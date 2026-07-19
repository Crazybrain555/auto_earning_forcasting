"""Training curriculum view: the trainer skill's bundled case plan.

The curriculum CSV organizes cases as development/untouched_holdout pairs in
waves ("第一阶段/第二阶段…"); a default round draws two pairs (2+2).
"""
from __future__ import annotations

import csv
from pathlib import Path

from .config import CONFIG

CSV_PATH = (
    Path(CONFIG["skills_repo"])
    / "technology-company-forecasting-trainer"
    / "assets" / "benchmarks" / "training_curriculum_v80.csv"
)


def load_curriculum() -> list[dict]:
    if not CSV_PATH.is_file():
        return []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["case_key"] = f"{row.get('security', '').strip()}@{row.get('proposed_as_of', '').strip()}"
    return rows


def waves() -> list[dict]:
    """Group by wave -> pairs, ready for the planner UI."""
    by_wave: dict[str, dict] = {}
    for row in load_curriculum():
        wave = str(row.get("wave", "?")).strip()
        pair = str(row.get("pair_id", "?")).strip()
        wave_entry = by_wave.setdefault(wave, {"wave": wave, "pairs": {}})
        wave_entry["pairs"].setdefault(pair, []).append({
            "case_id": row.get("case_id"),
            "pair_id": pair,
            "company": row.get("company"),
            "security": row.get("security"),
            "proposed_as_of": row.get("proposed_as_of"),
            "role": row.get("role"),
            "mechanism": row.get("mechanism"),
            "research_focus": row.get("research_focus"),
            "notes": row.get("notes"),
            "case_key": row.get("case_key"),
        })
    result = []
    for wave in sorted(by_wave, key=lambda w: (len(w), w)):
        entry = by_wave[wave]
        result.append({
            "wave": wave,
            "pairs": [{"pair_id": p, "cases": entry["pairs"][p]} for p in sorted(entry["pairs"])],
        })
    return result
