#!/usr/bin/env python3
"""Gate the training loop's external-method reflection.

Internal error attribution says only that the method missed. A rule inferred
from a two-case sample without checking outside practice is an overfit
waiting to happen. This validates training-runs/<round>/method_reflection.md:
every proposed rule must record the measured error, the internal attribution,
the external sources consulted, and whether outside practice agrees.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "error_observed": ["error_observed", "误差观察"],
    "internal_attribution": ["internal_attribution", "内部归因"],
    "external_sources": ["external_sources", "外部来源"],
    "outside_view": ["outside_view", "外部视角"],
    "agreement": ["agreement", "一致性"],
    "rule_adopted": ["rule_adopted", "采纳规则"],
}
URL_RE = re.compile(r"https?://\S+|youtube:\S+|isbn:\S+", re.I)
MIN_SOURCES = 2


def blocks(text: str) -> list[tuple[str, str]]:
    """Split on level-2/3 headings; each becomes one rule block."""
    parts = re.split(r"^#{2,3}\s+(.+)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reflection", required=True)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    path = Path(args.reflection)
    if not path.is_file():
        print(f"FAIL: {path} not found - every round records its external-method reflection "
              "(see references/historical-training-loop.md step 3b)")
        return 2

    text = path.read_text(encoding="utf-8")
    rule_blocks = [(t, b) for t, b in blocks(text) if not t.lower().startswith(("overview", "summary", "概述"))]
    errors: list[str] = []
    if not rule_blocks:
        errors.append("no rule sections found - one heading per proposed rule")

    for title, body in rule_blocks:
        low = body.lower()
        for field, aliases in REQUIRED_FIELDS.items():
            if not any(a.lower() in low for a in aliases):
                errors.append(f"[{title}] missing field: {field}")
        sources = URL_RE.findall(body)
        if len(sources) < MIN_SOURCES:
            errors.append(f"[{title}] only {len(sources)} external source reference(s); "
                          f"need >={MIN_SOURCES} (links, youtube:<id>, or isbn:<n>) - "
                          "a rule from a two-case sample must be checked against outside practice")
        if re.search(r"agreement`?\s*[:：]\s*\**\s*(contradict|disagree|矛盾)", low) and \
           not any(k in low for k in ["why_not_alternatives", "context differs", "语境不同", "为何不采用"]):
            errors.append(f"[{title}] outside practice contradicts the internal reading but no argument "
                          "is given for why this context differs - drop the rule or argue it")

    if errors:
        print("FAIL: method reflection incomplete")
        for e in errors:
            print("  - " + e)
        return 2 if args.strict else 1
    print(f"PASS: method reflection covers {len(rule_blocks)} rule(s) with external corroboration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
