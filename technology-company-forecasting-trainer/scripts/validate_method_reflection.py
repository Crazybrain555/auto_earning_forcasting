#!/usr/bin/env python3
"""Gate the training loop's external-method reflection.

Internal error attribution says only that the method missed. A rule inferred
from a two-case sample without checking outside practice is an overfit
waiting to happen. This validates training-runs/<round>/method_reflection.md:
every proposed rule must record the measured error, structured external method
sources and their declared origin, the permission and misuse boundary of those
sources, and a support state plus a validation plan.
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
    "support_status": ["support_status", "支持状态"],
    "validation_plan": ["validation_plan", "验证计划"],
    "challenger_baselines": ["challenger_baselines", "challenger_baseline", "挑战基准"],
    "generative_change": ["generative_change", "生成路径修正"],
    "assurance_angle": ["assurance_angle", "保障角度"],
    "complexity_delta": ["complexity_delta", "复杂度变化"],
    "independent_review_plan": ["independent_review_plan", "独立审查计划"],
}
SOURCE_FIELDS = {
    "source_id": ["source_id", "来源id", "来源_id"],
    "category": ["category", "source_type", "类别", "来源类型"],
    "independence_cluster": ["independence_cluster", "independent_cluster", "独立簇"],
    "originality": ["originality", "原创性", "来源原创性"],
    "location": ["location", "url", "doi", "出处", "位置"],
    "method_claim": ["method_claim", "方法命题", "方法主张"],
    "misuse_boundary": ["misuse_boundary", "误用边界", "适用边界"],
}
LOCATION_RE = re.compile(r"https?://\S+|youtube:\S+|isbn:\S+|doi:\s*10\.\S+", re.I)
SOURCE_PAIR_RE = re.compile(
    r"`?([A-Za-z_][\w-]*)`?\s*[:：]\s*(.*?)"
    r"(?=\s*\|\s*`?[A-Za-z_][\w-]*`?\s*[:：]|\Z)",
    re.S,
)
PLACEHOLDERS = {"", "-", "none", "n/a", "na", "tbd", "unknown", "unclear", "待补充", "无"}
SUPPORT_STATUSES = {
    "provisional",
    "externally_supported",
    "externally_supported_method",
    "validated_on_holdout",
    "rejected",
    "no_change",
}


def blocks(text: str) -> list[tuple[str, str]]:
    """Split on level-2/3 headings; each becomes one rule block."""
    parts = re.split(r"^#{2,3}\s+(.+)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


def clean_key(value: str) -> str:
    return value.strip().strip("`").strip().lower()


def clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().strip("|").strip()


def meaningful(value: str) -> bool:
    cleaned = clean_value(value).strip("<>").strip().lower()
    return cleaned not in PLACEHOLDERS


def top_level_fields(body: str) -> dict[str, str]:
    """Parse top-level Markdown bullets without consuming nested source bullets."""
    out: dict[str, str] = {}
    for chunk in re.split(r"(?m)^[ \t]{0,1}-\s+", body)[1:]:
        match = re.match(r"`?([^`:\n]+)`?\s*[:：]\s*(.*)\Z", chunk, flags=re.S)
        if match:
            out[clean_key(match.group(1))] = match.group(2).strip()
    return out


def field_value(fields: dict[str, str], aliases: list[str]) -> str:
    for alias in aliases:
        value = fields.get(clean_key(alias))
        if value is not None:
            return value
    return ""


def structured_sources(raw: str) -> list[dict[str, str]]:
    """Parse the indented source bullets and their pipe-separated fields."""
    sources: list[dict[str, str]] = []
    # ``top_level_fields`` strips the leading whitespace from the first nested
    # source while preserving it on later sources.  Accept either shape so the
    # parser treats the first and subsequent source records identically.
    items = re.split(r"(?m)^[ \t]*-\s+", raw)[1:]
    for item in items:
        collapsed = clean_value(item)
        parsed = {clean_key(k): clean_value(v) for k, v in SOURCE_PAIR_RE.findall(collapsed)}
        sources.append(parsed)
    return sources


def source_value(source: dict[str, str], aliases: list[str]) -> str:
    for alias in aliases:
        value = source.get(clean_key(alias))
        if value is not None:
            return value
    return ""


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
        fields = top_level_fields(body)
        for field, aliases in REQUIRED_FIELDS.items():
            if not meaningful(field_value(fields, aliases)):
                errors.append(f"[{title}] missing field: {field}")

        source_section = field_value(fields, REQUIRED_FIELDS["external_sources"])
        sources = structured_sources(source_section)
        if not sources:
            errors.append(
                f"[{title}] external_sources needs at least one substantive structured method source"
            )

        source_ids: list[str] = []
        for index, source in enumerate(sources, start=1):
            label = source_value(source, SOURCE_FIELDS["source_id"]) or f"source-{index}"
            for field, aliases in SOURCE_FIELDS.items():
                value = source_value(source, aliases)
                if not meaningful(value):
                    errors.append(f"[{title}] external source {label} missing or placeholder field: {field}")
            source_id = source_value(source, SOURCE_FIELDS["source_id"]).strip().casefold()
            if source_id:
                source_ids.append(source_id)
            location = source_value(source, SOURCE_FIELDS["location"])
            if meaningful(location) and not LOCATION_RE.search(location):
                errors.append(f"[{title}] external source {label} location needs a URL, doi:, "
                              "youtube:, or isbn: reference")

        if len(source_ids) != len(set(source_ids)):
            errors.append(f"[{title}] external source_id values must be unique")

        support_status = clean_value(field_value(fields, REQUIRED_FIELDS["support_status"])).lower()
        support_code = re.split(r"[;；—]", support_status, maxsplit=1)[0].strip()
        if meaningful(support_status) and support_code not in SUPPORT_STATUSES:
            errors.append(
                f"[{title}] support_status must be one of {', '.join(sorted(SUPPORT_STATUSES))}; "
                "external reading cannot be labeled as permanent proof"
            )

    if errors:
        print("FAIL: method reflection incomplete")
        for e in errors:
            print("  - " + e)
        return 2 if args.strict else 1
    print(
        f"PASS: method reflection covers {len(rule_blocks)} rule(s) with structured "
        "external method evidence and process-first change records"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
