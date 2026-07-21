#!/usr/bin/env python3
"""Canonical identities and validation for training-actuals receipts.

Source-packet validation remains in ``score_training_forecast.py`` because it
has access to the original official-source records.  This module owns the
receipt contract used both when the scorer emits a receipt and when promotion
later revalidates it, preventing those two stages from drifting into duplicate
implementations.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation


ACTUALS_SCHEMA_VERSION = "3.2"
ACTUALS_CONTRACT_VERSION = f"training_actuals/{ACTUALS_SCHEMA_VERSION}"
ACTUALS_LOCAL_TRUST_STATUS = "locally_consistent_untrusted"
FORECAST_SEAL_RECEIPT_STATUS_VERIFIED = "verified"
FORECAST_SEAL_RECEIPT_STATUS_LEGACY_MISSING = "legacy_missing_unverified"
OFFICIAL_SOURCE_ORIGIN_CLASSES = {
    "issuer_statutory_filing",
    "issuer_official_results",
    "regulator_filed_fact",
    "audited_financial_statements",
}
STATUTORY_ACCOUNTING_BASES = {
    "us-gaap": "US GAAP",
    "ifrs-iasb": "IFRS as issued by IASB",
    "prc-asbe": "PRC Accounting Standards for Business Enterprises",
    "hkfrs": "Hong Kong Financial Reporting Standards",
    "jgaap": "Japanese GAAP",
}
FACT_ORIGIN = "direct_official_reported_fact"
ZERO_VALUE_BASIS = "explicit_official_zero_or_reported_rounding"
REQUIRED_ACTUAL_METRICS = (
    "revenue",
    "operating_profit",
    "gaap_net_income_attributable",
)
BRIDGE_METRICS = (
    "pretax_income",
    "income_tax_expense",
    "consolidated_net_income",
    "noncontrolling_interest_net_income",
)
METRIC_SCOPE = {
    "revenue": "consolidated_revenue",
    "operating_profit": "consolidated_operating_profit",
    "gaap_net_income_attributable": "attributable_to_parent_shareholders",
    "pretax_income": "consolidated_pretax_income",
    "income_tax_expense": "consolidated_income_tax_expense",
    "consolidated_net_income": "consolidated_net_income_before_nci_attribution",
    "noncontrolling_interest_net_income": "net_income_attributable_to_noncontrolling_interests",
}
METRIC_SIGN_CONVENTION = {
    "revenue": "income_positive",
    "operating_profit": "income_positive",
    "gaap_net_income_attributable": "income_positive",
    "pretax_income": "income_positive",
    "income_tax_expense": "expense_positive",
    "consolidated_net_income": "income_positive",
    "noncontrolling_interest_net_income": "income_attributable_to_nci_positive",
}

_REPORTED_NUMERIC_LITERAL = re.compile(
    r"^[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$"
)


def meaningful(raw: object) -> bool:
    return (
        isinstance(raw, str)
        and raw.strip().lower()
        not in {"", "none", "n/a", "na", "tbd", "todo", "unknown", "example", "placeholder"}
    )


def aware_datetime(raw: object) -> dt.datetime | None:
    if not meaningful(raw):
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def iso_date(raw: object) -> dt.date | None:
    if not meaningful(raw):
        return None
    try:
        return dt.date.fromisoformat(str(raw))
    except ValueError:
        return None


def finite_number(raw: object) -> bool:
    return (
        isinstance(raw, (int, float))
        and not isinstance(raw, bool)
        and math.isfinite(float(raw))
    )


def parse_reported_numeric_literal(
    raw: object, *, label: str
) -> tuple[Decimal | None, Decimal | None, list[str]]:
    """Parse the exact numeric cell token copied from the official source.

    Units and scale belong in the typed ``unit`` field.  Restricting this field
    to a numeric token lets the receipt bind the validated value, explicit zero
    and displayed precision to source evidence instead of trusting three
    analyst-authored declarations that can contradict one another.
    """

    if not isinstance(raw, str) or not raw.strip():
        return None, None, [f"{label}.source_fact_value_text requires a direct numeric literal"]
    token = raw.strip().replace("−", "-")
    negative_parentheses = token.startswith("(") and token.endswith(")")
    if negative_parentheses:
        token = "-" + token[1:-1].strip()
    if not _REPORTED_NUMERIC_LITERAL.fullmatch(token):
        return None, None, [
            f"{label}.source_fact_value_text requires a direct numeric literal "
            "without narrative, unit text or an assumed dash"
        ]
    normalized = token.replace(",", "")
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None, None, [f"{label}.source_fact_value_text is not a valid numeric literal"]
    unsigned = normalized.lstrip("+-")
    decimal_places = len(unsigned.partition(".")[2]) if "." in unsigned else 0
    displayed_increment = Decimal(1).scaleb(-decimal_places)
    return value, displayed_increment, []


def validate_accounting_basis_pair(
    basis_id: object, basis_label: object, *, label: str
) -> list[str]:
    """Require the descriptive label to be a projection of the controlled ID."""

    expected = STATUTORY_ACCOUNTING_BASES.get(basis_id)
    if expected is None:
        return [f"{label}.accounting_basis_id must name a supported statutory GAAP/IFRS basis"]
    if basis_label != expected:
        return [
            f"{label}.accounting_basis must match canonical statutory basis label "
            f"{expected!r} for {basis_id}"
        ]
    return []


def validate_reported_precision(
    raw: object,
    *,
    label: str,
    displayed_increment: Decimal | None = None,
) -> tuple[float | None, list[str]]:
    """Return the reported-unit rounding increment, never an analyst tolerance."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, [f"{label}.reported_precision is required"]
    basis = raw.get("basis")
    increment = raw.get("rounding_increment_in_reported_unit")
    if basis not in {"exact", "rounded"}:
        errors.append(f"{label}.reported_precision.basis must be exact or rounded")
    if not finite_number(increment) or float(increment) < 0:
        errors.append(
            f"{label}.reported_precision.rounding_increment_in_reported_unit must be finite and non-negative"
        )
        return None, errors
    numeric = float(increment)
    if basis == "exact" and numeric != 0:
        errors.append(f"{label}.reported_precision exact facts require a zero rounding increment")
    if basis == "rounded" and numeric <= 0:
        errors.append(f"{label}.reported_precision rounded facts require a positive rounding increment")
    if basis == "rounded" and displayed_increment is not None:
        try:
            declared = Decimal(str(increment))
        except InvalidOperation:
            declared = None
        if declared != displayed_increment:
            errors.append(
                f"{label}.reported_precision rounding increment must equal displayed numeric "
                f"increment {displayed_increment} derived from source_fact_value_text"
            )
    return numeric, errors


def validate_fact_literal_and_precision(
    observation: object, *, label: str
) -> tuple[float | None, list[str]]:
    """Bind numeric value, explicit zero and rounding precision to one literal."""

    if not isinstance(observation, dict):
        return None, [f"{label} must be an observation object"]
    literal, displayed_increment, errors = parse_reported_numeric_literal(
        observation.get("source_fact_value_text"), label=label
    )
    raw_value = observation.get("value")
    if literal is not None and finite_number(raw_value):
        if Decimal(str(raw_value)) != literal:
            errors.append(
                f"{label}.source_fact_value_text numeric literal {literal} does not equal value {raw_value}"
            )
    increment, precision_errors = validate_reported_precision(
        observation.get("reported_precision"),
        label=label,
        displayed_increment=displayed_increment,
    )
    errors.extend(precision_errors)
    if finite_number(raw_value) and float(raw_value) == 0.0:
        if literal is None or literal != 0:
            errors.append(
                f"{label}.zero value requires the official source_fact_value_text to be a direct numeric zero"
            )
        if observation.get("zero_value_basis") != ZERO_VALUE_BASIS:
            errors.append(
                f"{label}.zero_value_basis must prove an explicit official zero; missing is never zero"
            )
    return increment, errors


def derived_equation_tolerance(rows: list[dict]) -> float | None:
    """Worst-case identity residual implied by declared display precision."""
    increments: list[float] = []
    for row in rows:
        increment, errors = validate_fact_literal_and_precision(row, label="fact")
        if errors or increment is None:
            return None
        increments.append(increment)
    return math.fsum(increment / 2.0 for increment in increments)


def canonical_payload_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def valid_sha256(raw: object) -> bool:
    if not isinstance(raw, str) or not raw.startswith("sha256:") or len(raw) != 71:
        return False
    return all(char in "0123456789abcdef" for char in raw[7:])


def validate_actuals_receipt(
    raw: object,
    *,
    expected_case: str,
    scored_at: object,
    label: str,
) -> list[str]:
    """Return all first-principles receipt errors without score thresholds."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return [f"{label}.actuals_validation_receipt is required"]
    if (
        raw.get("contract_version") != ACTUALS_CONTRACT_VERSION
        or raw.get("status") != ACTUALS_LOCAL_TRUST_STATUS
    ):
        errors.append(
            f"{label}.actuals_validation_receipt must be a "
            f"{ACTUALS_LOCAL_TRUST_STATUS} {ACTUALS_CONTRACT_VERSION} receipt; "
            "local consistency does not establish external truth"
        )
    if raw.get("case_id") != expected_case:
        errors.append(f"{label}.actuals_validation_receipt.case_id does not match {expected_case}")
    if not meaningful(raw.get("entity_id")):
        errors.append(f"{label}.actuals_validation_receipt.entity_id is required")
    if not valid_sha256(raw.get("actuals_sha256")):
        errors.append(f"{label}.actuals_validation_receipt.actuals_sha256 is invalid")
    receipt_core = {key: value for key, value in raw.items() if key != "receipt_id"}
    if raw.get("receipt_id") != canonical_payload_hash(receipt_core):
        errors.append(f"{label}.actuals_validation_receipt.receipt_id is not derived from its contents")

    sealed_at = aware_datetime(raw.get("sealed_at"))
    retrieved_at = aware_datetime(raw.get("retrieved_at"))
    cutoff_at = aware_datetime(raw.get("information_cutoff_at"))
    score_time = aware_datetime(scored_at)
    if any(value is None for value in (sealed_at, retrieved_at, cutoff_at, score_time)):
        errors.append(f"{label}.actuals_validation_receipt chronology must use timezone-aware timestamps")
    else:
        assert sealed_at is not None and retrieved_at is not None and cutoff_at is not None
        assert score_time is not None
        if retrieved_at <= sealed_at:
            errors.append(f"{label}.actuals_validation_receipt was not retrieved after the seal")
        if cutoff_at > retrieved_at:
            errors.append(f"{label}.actuals_validation_receipt cutoff is after retrieval")
        if score_time < retrieved_at:
            errors.append(f"{label}.scored_at predates actuals retrieval")

    official_source_ids = raw.get("official_source_ids")
    if (
        not isinstance(official_source_ids, list)
        or not official_source_ids
        or any(not meaningful(item) for item in official_source_ids)
        or len(set(official_source_ids)) != len(official_source_ids)
    ):
        errors.append(f"{label}.actuals_validation_receipt official_source_ids are not meaningful and unique")
        official_source_ids = []
    sources = raw.get("official_sources")
    source_map: dict[str, dict] = {}
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label}.actuals_validation_receipt official_sources are required")
    else:
        for index, source in enumerate(sources):
            source_label = f"{label}.actuals_validation_receipt.official_sources[{index}]"
            if not isinstance(source, dict):
                errors.append(f"{source_label} must be an object")
                continue
            source_id = source.get("source_id")
            if not meaningful(source_id) or source_id in source_map:
                errors.append(f"{source_label}.source_id must be unique and meaningful")
                continue
            for field in ("issuer_or_regulator", "document_type", "title", "locator"):
                if not meaningful(source.get(field)):
                    errors.append(f"{source_label}.{field} is required")
            if not valid_sha256(source.get("content_sha256")):
                errors.append(
                    f"{source_label}.content_sha256 must content-address the retrieved official source"
                )
            if source.get("origin_class") not in OFFICIAL_SOURCE_ORIGIN_CLASSES:
                errors.append(
                    f"{source_label}.origin_class must identify an issuer/regulator official fact origin"
                )
            published = aware_datetime(source.get("published_at"))
            if published is None:
                errors.append(f"{source_label}.published_at must be timezone-aware")
            elif cutoff_at is not None and published > cutoff_at:
                errors.append(f"{source_label}.published_at is after the information cutoff")
            source_map[str(source_id)] = source
    if set(official_source_ids) != set(source_map):
        errors.append(f"{label}.actuals_validation_receipt source IDs do not bind its official sources")

    tolerance = raw.get("derived_reconciliation_tolerances")
    if not isinstance(tolerance, dict) or tolerance.get("method") != "sum_half_reported_rounding_increments":
        errors.append(
            f"{label}.actuals_validation_receipt derived_reconciliation_tolerances must use reported precision"
        )
        tolerance = {}
    reported_tolerances = tolerance.get("by_period")
    if not isinstance(reported_tolerances, dict):
        errors.append(
            f"{label}.actuals_validation_receipt derived_reconciliation_tolerances.by_period is required"
        )
        reported_tolerances = {}

    observations = raw.get("validated_observations")
    by_key: dict[tuple[str, str, str, str], dict] = {}
    observation_ids: set[str] = set()
    period_to_dates: dict[str, tuple[str, str]] = {}
    dates_to_period: dict[tuple[str, str], str] = {}
    if not isinstance(observations, list) or not observations:
        errors.append(f"{label}.actuals_validation_receipt validated_observations are required")
        observations = []
    allowed_metrics = set(REQUIRED_ACTUAL_METRICS + BRIDGE_METRICS)
    for index, observation in enumerate(observations):
        obs_label = f"{label}.actuals_validation_receipt.validated_observations[{index}]"
        if not isinstance(observation, dict):
            errors.append(f"{obs_label} must be an object")
            continue
        observation_id = observation.get("observation_id")
        if not meaningful(observation_id) or observation_id in observation_ids:
            errors.append(f"{obs_label}.observation_id must be unique and meaningful")
        else:
            observation_ids.add(str(observation_id))
        entity_id = observation.get("entity_id")
        period = observation.get("period")
        metric = observation.get("metric")
        if entity_id != raw.get("entity_id") or not meaningful(period) or metric not in allowed_metrics:
            errors.append(f"{obs_label} has an invalid entity/period/canonical metric identity")
            continue
        start = iso_date(observation.get("fiscal_period_start"))
        end = iso_date(observation.get("fiscal_period_end"))
        if start is None:
            errors.append(f"{obs_label}.fiscal_period_start must be an ISO date")
        if end is None:
            errors.append(f"{obs_label}.fiscal_period_end must be an ISO date")
        if start is not None and end is not None and end < start:
            errors.append(f"{obs_label} fiscal period ends before it starts")
        start_text = start.isoformat() if start is not None else ""
        end_text = end.isoformat() if end is not None else ""
        date_key = (start_text, end_text)
        prior_dates = period_to_dates.setdefault(str(period), date_key)
        if prior_dates != date_key:
            errors.append(f"{obs_label}.period maps to conflicting fiscal dates")
        prior_period = dates_to_period.setdefault(date_key, str(period))
        if prior_period != str(period):
            errors.append(
                f"{obs_label} reuses one fiscal period under multiple horizon labels"
            )
        key = (str(entity_id), start_text, end_text, str(metric))
        if key in by_key:
            errors.append(f"{obs_label} duplicates/conflicts with entity-fiscal-period-metric {key}")
        else:
            by_key[key] = observation
        if not finite_number(observation.get("value")):
            errors.append(f"{obs_label}.value must be finite; missing disclosure is not zero")
        for field in (
            "currency",
            "unit",
            "accounting_basis",
            "consolidation_perimeter",
            "source_fact_label",
            "source_fact_anchor",
        ):
            if not meaningful(observation.get(field)):
                errors.append(f"{obs_label}.{field} is required")
        errors.extend(
            validate_accounting_basis_pair(
                observation.get("accounting_basis_id"),
                observation.get("accounting_basis"),
                label=obs_label,
            )
        )
        if observation.get("fact_origin") != FACT_ORIGIN:
            errors.append(f"{obs_label}.fact_origin must be a direct official reported fact")
        _, fact_errors = validate_fact_literal_and_precision(observation, label=obs_label)
        errors.extend(fact_errors)
        currency = observation.get("currency")
        if (
            not isinstance(currency, str)
            or len(currency) != 3
            or not currency.isalpha()
            or currency.upper() != currency
        ):
            errors.append(f"{obs_label}.currency must be a three-letter uppercase code")
        if observation.get("fact_scope") != METRIC_SCOPE.get(metric):
            errors.append(f"{obs_label}.fact_scope does not match {metric}")
        if observation.get("sign_convention") != METRIC_SIGN_CONVENTION.get(metric):
            errors.append(f"{obs_label}.sign_convention does not match {metric}")
        obs_source_ids = observation.get("official_source_ids")
        if (
            not isinstance(obs_source_ids, list)
            or not obs_source_ids
            or any(not meaningful(item) or item not in source_map for item in obs_source_ids)
            or len(set(obs_source_ids)) != len(obs_source_ids)
        ):
            errors.append(f"{obs_label}.official_source_ids do not bind an official source")
        elif end is not None:
            for source_id in obs_source_ids:
                source_published = aware_datetime(source_map[source_id].get("published_at"))
                if source_published is not None and source_published.date() < end:
                    errors.append(
                        f"{obs_label} cites source {source_id} published before fiscal_period_end"
                    )

    entity_id = str(raw.get("entity_id") or "")
    fiscal_periods = sorted({(start, end) for entity, start, end, _ in by_key if entity == entity_id})
    expected_tolerances_by_period: dict[str, dict[str, float | None]] = {}
    if not fiscal_periods:
        errors.append(f"{label}.actuals_validation_receipt contains no scored periods")
    for start, end in fiscal_periods:
        period = dates_to_period.get((start, end), f"{start}/{end}")
        missing = [
            metric for metric in REQUIRED_ACTUAL_METRICS
            if (entity_id, start, end, metric) not in by_key
        ]
        if missing:
            errors.append(
                f"{label}.actuals_validation_receipt {period} missing canonical observations: "
                + ", ".join(sorted(missing))
            )
            continue
        required_rows = [by_key[(entity_id, start, end, metric)] for metric in REQUIRED_ACTUAL_METRICS]
        common_fields = (
            "currency", "unit", "accounting_basis", "accounting_basis_id",
            "consolidation_perimeter",
        )
        if any(
            row.get(field) != required_rows[0].get(field)
            for row in required_rows[1:]
            for field in common_fields
        ):
            errors.append(
                f"{label}.actuals_validation_receipt {period} required metrics use inconsistent bases or units"
            )
        target = by_key[(entity_id, start, end, "gaap_net_income_attributable")]
        method = target.get("attribution_method")
        bridge_present = [
            metric for metric in BRIDGE_METRICS
            if (entity_id, start, end, metric) in by_key
        ]
        if method == "direct_official_attributable_fact":
            if bridge_present and len(bridge_present) != len(BRIDGE_METRICS):
                errors.append(
                    f"{label}.actuals_validation_receipt {period} contains a partial net-income bridge"
                )
                continue
            if not bridge_present:
                continue
        elif method != "derived_from_reported_bridge":
            errors.append(
                f"{label}.actuals_validation_receipt {period} lacks attributable-NI provenance"
            )
            continue
        bridge_missing = [
            metric for metric in BRIDGE_METRICS
            if (entity_id, start, end, metric) not in by_key
        ]
        if bridge_missing:
            errors.append(
                f"{label}.actuals_validation_receipt {period} bridge missing "
                + ", ".join(sorted(bridge_missing))
            )
            continue
        bridge = {metric: by_key[(entity_id, start, end, metric)] for metric in BRIDGE_METRICS}
        if any(
            bridge[metric].get(field) != target.get(field)
            for metric in BRIDGE_METRICS
            for field in common_fields
        ):
            errors.append(f"{label}.actuals_validation_receipt {period} bridge bases are inconsistent")
        pretax = bridge["pretax_income"].get("value")
        tax = bridge["income_tax_expense"].get("value")
        consolidated = bridge["consolidated_net_income"].get("value")
        nci = bridge["noncontrolling_interest_net_income"].get("value")
        attributable = target.get("value")
        pretax_tolerance = derived_equation_tolerance([
            bridge["pretax_income"], bridge["income_tax_expense"], bridge["consolidated_net_income"]
        ])
        nci_tolerance = derived_equation_tolerance([
            bridge["consolidated_net_income"], bridge["noncontrolling_interest_net_income"], target
        ])
        derived_tolerances = {
            "pretax_tax_to_consolidated_net_income": pretax_tolerance,
            "consolidated_net_income_nci_to_attributable": nci_tolerance,
        }
        expected_tolerances_by_period[period] = derived_tolerances
        if all(finite_number(item) for item in (pretax, tax, consolidated, nci, attributable)):
            if pretax_tolerance is not None and abs((float(pretax) - float(tax)) - float(consolidated)) > pretax_tolerance + 1e-12:
                errors.append(f"{label}.actuals_validation_receipt {period} pretax/tax bridge is inconsistent")
            if nci_tolerance is not None and abs((float(consolidated) - float(nci)) - float(attributable)) > nci_tolerance + 1e-12:
                errors.append(f"{label}.actuals_validation_receipt {period} NCI bridge is inconsistent")
    if reported_tolerances != expected_tolerances_by_period:
        errors.append(
            f"{label}.actuals_validation_receipt reconciliation tolerances are not precision-derived"
        )
    return errors
