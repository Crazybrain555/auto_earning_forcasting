import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL / "assets" / "templates"
SCHEMAS = SKILL / "assets" / "schemas"

# Exact live-contract fields that assign importance by analyst fiat.  This is
# intentionally not a substring ban: scenario probabilities, measured error
# scores and old files under assets/benchmarks remain valid contracts.
FORBIDDEN_FIELDS = {
    "mechanism_weights",
    "archetype_weights",
    "materiality_weight",
    "company_lenses",
    "independence_weight",
    "maximum_unsupported_materiality_ratio",
}


def object_field_paths(value, prefix=()):
    paths = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = prefix + (str(key),)
            paths.append(path)
            paths.extend(object_field_paths(child, path))
    elif isinstance(value, list):
        for child in value:
            paths.extend(object_field_paths(child, prefix + ("[]",)))
    return paths


def schema_field_paths(schema, prefix=()):
    paths = []
    if not isinstance(schema, dict):
        return paths
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            path = prefix + (name,)
            paths.append(path)
            paths.extend(schema_field_paths(child, path))
    items = schema.get("items")
    if isinstance(items, dict):
        paths.extend(schema_field_paths(items, prefix + ("[]",)))
    for combinator in ("allOf", "anyOf", "oneOf"):
        for child in schema.get(combinator, []):
            paths.extend(schema_field_paths(child, prefix))
    return paths


def forbidden(paths):
    return sorted(".".join(path) for path in paths if path and path[-1] in FORBIDDEN_FIELDS)


class LiveContractNoManualWeightsTest(unittest.TestCase):
    def test_active_live_templates_have_no_assigned_weight_fields(self):
        for name in ("forecast_snapshot_template.json", "run_manifest_template.json"):
            with self.subTest(template=name):
                data = json.loads((TEMPLATES / name).read_text(encoding="utf-8"))
                self.assertEqual(forbidden(object_field_paths(data)), [], name)

        for name in ("material_assumption_support_template.csv", "source_independence_map_template.csv"):
            with self.subTest(template=name):
                with (TEMPLATES / name).open(encoding="utf-8-sig", newline="") as fh:
                    header = next(csv.reader(fh))
                self.assertEqual(sorted(set(header) & FORBIDDEN_FIELDS), [], name)

    def test_active_live_schemas_do_not_publish_assigned_weight_fields(self):
        # forecast_case.schema.json is intentionally not scanned: it is the
        # legacy historical-benchmark migration contract, not a new delivery.
        for name in ("forecast_snapshot.schema.json", "run_manifest.schema.json"):
            with self.subTest(schema=name):
                schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
                self.assertEqual(forbidden(schema_field_paths(schema)), [], name)

    def test_scaffolded_live_workspace_has_no_assigned_weight_fields(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "run"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "scaffold_delivery.py"),
                    "--workspace",
                    str(workspace),
                    "--entity",
                    "TEST",
                    "--security",
                    "TEST",
                    "--as-of",
                    "2026-07-18",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            violations = []
            for path in workspace.glob("*.json"):
                data = json.loads(path.read_text(encoding="utf-8"))
                violations.extend(f"{path.name}:{field}" for field in forbidden(object_field_paths(data)))
            for path in workspace.glob("*.csv"):
                with path.open(encoding="utf-8-sig", newline="") as fh:
                    header = next(csv.reader(fh), [])
                violations.extend(f"{path.name}:{field}" for field in sorted(set(header) & FORBIDDEN_FIELDS))
            self.assertEqual(violations, [])

            # These are measured uncertainty contracts, not analyst-assigned
            # importance weights; an implementation must not remove them to
            # make the no-weight test pass.
            snapshot = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
            self.assertIn("scenario_probabilities", snapshot)
            self.assertIn("error_budget", snapshot)


if __name__ == "__main__":
    unittest.main()
