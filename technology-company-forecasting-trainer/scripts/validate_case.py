#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

REQUIRED = ["case_id", "entity", "as_of", "currency", "fiscal_calendar", "horizons", "source_ids", "assumptions", "forecast"]


def validate(obj: dict) -> list[str]:
    errors = [f"missing required field: {key}" for key in REQUIRED if key not in obj]
    if errors:
        return errors
    try:
        datetime.fromisoformat(str(obj["as_of"]).replace("Z", "+00:00"))
    except Exception:
        errors.append("as_of must be ISO-8601")

    primitives = obj.get("analysis_primitives")
    if not isinstance(primitives, list) or not primitives:
        # Historical v1 cases remain readable, but weight values have no
        # modeling meaning and are never checked or blended.
        legacy = obj.get("mechanisms") or obj.get("archetypes") or []
        if not legacy:
            errors.append("analysis_primitives must not be empty")
    else:
        for primitive in primitives:
            if not isinstance(primitive, dict) or not str(primitive.get("name") or "").strip():
                errors.append("each analysis primitive needs a name")
    main_line = obj.get("main_line")
    if str(obj.get("contract_version") or "").startswith("2") and not isinstance(main_line, dict):
        errors.append("v2 case needs a main_line object")
    if not obj.get("horizons"):
        errors.append("horizons must not be empty")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    obj = json.loads(args.case.read_text(encoding="utf-8"))
    errors = validate(obj)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
