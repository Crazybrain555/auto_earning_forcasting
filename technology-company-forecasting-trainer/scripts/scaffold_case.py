#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--primitive")
    parser.add_argument("--mechanism", help="legacy CLI alias for --primitive")
    parser.add_argument("--calibration-pack", action="append", default=[])
    args = parser.parse_args()
    primitive = args.primitive or args.mechanism
    if not primitive:
        parser.error("--primitive is required")
    root = Path(__file__).resolve().parents[1]
    template = json.loads((root / "assets/templates/case_template.json").read_text(encoding="utf-8"))
    template["case_id"] = f"{args.entity.replace(' ', '-')}@{args.as_of}"
    template["entity"] = args.entity
    template["as_of"] = args.as_of + "T00:00:00Z" if "T" not in args.as_of else args.as_of
    template["analysis_primitives"] = [{"name": primitive, "validation_status": "check validated-coverage.md"}]
    template["optional_calibration_packs"] = args.calibration_pack
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
