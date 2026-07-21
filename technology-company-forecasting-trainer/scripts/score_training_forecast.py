#!/usr/bin/env python3
"""Score a SEALED training forecast against externally retrieved actuals.

Integrity rules (see _seal_core): the seal is fully re-verified before and
after scoring (forged seals, tampered files, and files added after sealing
all fail); actuals must come from outside the sealed area; outputs go only
to the seal-exempt evaluation/ subtree; nothing sealed is ever rewritten -
scoring leaves the sealed workspace bit-for-bit intact.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _seal_core as core
from _actuals_contract import (
    ACTUALS_CONTRACT_VERSION,
    ACTUALS_LOCAL_TRUST_STATUS,
    ACTUALS_SCHEMA_VERSION,
    BRIDGE_METRICS,
    FACT_ORIGIN,
    FORECAST_SEAL_RECEIPT_STATUS_LEGACY_MISSING,
    FORECAST_SEAL_RECEIPT_STATUS_VERIFIED,
    METRIC_SCOPE,
    METRIC_SIGN_CONVENTION,
    OFFICIAL_SOURCE_ORIGIN_CLASSES,
    REQUIRED_ACTUAL_METRICS,
    aware_datetime,
    canonical_payload_hash,
    derived_equation_tolerance,
    finite_number,
    iso_date,
    meaningful,
    valid_sha256,
    validate_accounting_basis_pair,
    validate_actuals_receipt,
    validate_fact_literal_and_precision,
)


def _aware_datetime(raw, *, label: str) -> dt.datetime:
    parsed = aware_datetime(raw)
    if parsed is None:
        raise SystemExit(f"{label} must be a timezone-aware ISO timestamp")
    return parsed


def _date(raw, *, label: str) -> dt.date:
    parsed = iso_date(raw)
    if parsed is None:
        raise SystemExit(f"{label} must be an ISO date")
    return parsed


def _finite_number(raw, *, label: str) -> float:
    if not finite_number(raw):
        raise SystemExit(f"{label} must be a finite reported value; missing disclosure is not zero")
    return float(raw)


def validate_actuals(actuals: object, *, seal: dict, actuals_path: Path) -> tuple[dict, dict]:
    """Validate reported facts before any forecast score is calculated.

    The observation is the unit of evidence.  A generic ``profit`` field or a
    consolidated ``net_income`` alias can therefore never be silently treated
    as income attributable to the parent's shareholders.
    """
    if not isinstance(actuals, dict) or actuals.get("schema_version") != ACTUALS_SCHEMA_VERSION:
        raise SystemExit(
            f"actuals must use schema_version {ACTUALS_SCHEMA_VERSION} and the "
            "source-bound official-fact observation contract"
        )
    if not meaningful(actuals.get("case_id")):
        raise SystemExit("actuals.case_id is required")
    entity = actuals.get("entity")
    if not isinstance(entity, dict):
        raise SystemExit("actuals.entity is required")
    for field in ("entity_id", "legal_name", "reporting_perimeter"):
        if not meaningful(entity.get(field)):
            raise SystemExit(f"actuals.entity.{field} is required")

    sealed_at = _aware_datetime(seal.get("sealed_at"), label="forecast seal.sealed_at")
    retrieved_at = _aware_datetime(actuals.get("retrieved_at"), label="actuals.retrieved_at")
    cutoff_at = _aware_datetime(
        actuals.get("information_cutoff_at"), label="actuals.information_cutoff_at"
    )
    if retrieved_at <= sealed_at:
        raise SystemExit("actuals.retrieved_at must be after the frozen forecast seal")
    if cutoff_at > retrieved_at:
        raise SystemExit("actuals.information_cutoff_at cannot be after retrieved_at")

    source_ids = actuals.get("official_source_ids")
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or any(not meaningful(item) for item in source_ids)
        or len(set(source_ids)) != len(source_ids)
    ):
        raise SystemExit("actuals.official_source_ids must contain unique meaningful official source IDs")
    sources = actuals.get("official_sources")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("actuals.official_sources is required")
    source_map: dict[str, dict] = {}
    for index, source in enumerate(sources):
        label = f"actuals.official_sources[{index}]"
        if not isinstance(source, dict):
            raise SystemExit(f"{label} must be an object")
        sid = source.get("source_id")
        if not meaningful(sid) or sid in source_map:
            raise SystemExit(f"{label}.source_id must be unique and meaningful")
        for field in ("issuer_or_regulator", "document_type", "title", "locator"):
            if not meaningful(source.get(field)):
                raise SystemExit(f"{label}.{field} is required")
        if not valid_sha256(source.get("content_sha256")):
            raise SystemExit(
                f"{label}.content_sha256 must content-address the retrieved official source"
            )
        if source.get("origin_class") not in OFFICIAL_SOURCE_ORIGIN_CLASSES:
            raise SystemExit(
                f"{label}.origin_class must identify an issuer/regulator official fact origin"
            )
        published_at = _aware_datetime(source.get("published_at"), label=f"{label}.published_at")
        if published_at > cutoff_at:
            raise SystemExit(f"{label}.published_at is after actuals.information_cutoff_at")
        source_map[str(sid)] = source
    if set(source_ids) != set(source_map):
        raise SystemExit("actuals.official_source_ids must exactly identify actuals.official_sources")

    if "reconciliation_tolerance" in actuals:
        raise SystemExit(
            "actuals.reconciliation_tolerance is analyst-supplied and prohibited; "
            "identity tolerance is derived from each fact's reported precision"
        )

    observations = actuals.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SystemExit("actuals.observations is required; missing disclosure is not zero")
    by_key: dict[tuple[str, str, str, str], dict] = {}
    observation_ids: set[str] = set()
    validated_receipts: list[dict] = []
    period_to_dates: dict[str, tuple[str, str]] = {}
    dates_to_period: dict[tuple[str, str], str] = {}
    for index, observation in enumerate(observations):
        label = f"actuals.observations[{index}]"
        if not isinstance(observation, dict):
            raise SystemExit(f"{label} must be an object")
        oid = observation.get("observation_id")
        if not meaningful(oid) or oid in observation_ids:
            raise SystemExit(f"{label}.observation_id must be unique and meaningful")
        observation_ids.add(str(oid))
        metric = observation.get("metric")
        if metric not in set(REQUIRED_ACTUAL_METRICS + BRIDGE_METRICS):
            raise SystemExit(
                f"{label}.metric is not canonical; generic profit/net_income aliases are prohibited"
            )
        if observation.get("entity_id") != entity["entity_id"]:
            raise SystemExit(f"{label}.entity_id does not match actuals.entity.entity_id")
        period = observation.get("period")
        if not meaningful(period):
            raise SystemExit(f"{label}.period is required")
        start = _date(observation.get("fiscal_period_start"), label=f"{label}.fiscal_period_start")
        end = _date(observation.get("fiscal_period_end"), label=f"{label}.fiscal_period_end")
        if end < start:
            raise SystemExit(f"{label} fiscal period ends before it starts")
        value = _finite_number(observation.get("value"), label=f"{label}.value")
        for field in (
            "currency", "unit", "accounting_basis", "consolidation_perimeter",
            "source_fact_label", "source_fact_anchor",
        ):
            if not meaningful(observation.get(field)):
                raise SystemExit(f"{label}.{field} is required")
        currency = str(observation["currency"])
        if len(currency) != 3 or not currency.isalpha() or currency.upper() != currency:
            raise SystemExit(f"{label}.currency must be a three-letter uppercase currency code")
        if observation["consolidation_perimeter"] != entity["reporting_perimeter"]:
            raise SystemExit(f"{label}.consolidation_perimeter does not match the entity perimeter")
        basis_errors = validate_accounting_basis_pair(
            observation.get("accounting_basis_id"),
            observation.get("accounting_basis"),
            label=label,
        )
        if basis_errors:
            raise SystemExit(basis_errors[0])
        if observation.get("fact_origin") != FACT_ORIGIN:
            raise SystemExit(f"{label}.fact_origin must be a direct official reported fact")
        _, fact_errors = validate_fact_literal_and_precision(observation, label=label)
        if fact_errors:
            raise SystemExit(fact_errors[0])
        if observation.get("fact_scope") != METRIC_SCOPE[metric]:
            raise SystemExit(f"{label}.fact_scope does not match canonical metric {metric}")
        if observation.get("sign_convention") != METRIC_SIGN_CONVENTION[metric]:
            raise SystemExit(f"{label}.sign_convention does not match canonical metric {metric}")
        obs_sources = observation.get("official_source_ids")
        if (
            not isinstance(obs_sources, list)
            or not obs_sources
            or any(not meaningful(item) or item not in source_map for item in obs_sources)
            or len(set(obs_sources)) != len(obs_sources)
        ):
            raise SystemExit(f"{label}.official_source_ids must bind the fact to declared official sources")
        for source_id in obs_sources:
            source_published = _aware_datetime(
                source_map[source_id].get("published_at"),
                label=f"actuals.official_sources[{source_id}].published_at",
            )
            if source_published.date() < end:
                raise SystemExit(
                    f"{label} cites source {source_id} published before fiscal_period_end"
                )
        date_key = (start.isoformat(), end.isoformat())
        prior_dates = period_to_dates.setdefault(str(period), date_key)
        if prior_dates != date_key:
            raise SystemExit(f"{label}.period maps to conflicting fiscal dates")
        prior_period = dates_to_period.setdefault(date_key, str(period))
        if prior_period != str(period):
            raise SystemExit(
                f"{label} reuses one fiscal period under multiple horizon labels"
            )
        key = (str(observation["entity_id"]), start.isoformat(), end.isoformat(), str(metric))
        if key in by_key:
            raise SystemExit(
                f"duplicate/conflicting actual observation for entity={key[0]} "
                f"fiscal_period={key[1]}/{key[2]} metric={key[3]}"
            )
        by_key[key] = observation
        validated_receipts.append(
            {
                "observation_id": oid,
                "entity_id": observation["entity_id"],
                "period": period,
                "fiscal_period_start": start.isoformat(),
                "fiscal_period_end": end.isoformat(),
                "metric": metric,
                "value": value,
                "currency": currency,
                "unit": observation["unit"],
                "accounting_basis": observation["accounting_basis"],
                "accounting_basis_id": observation["accounting_basis_id"],
                "consolidation_perimeter": observation["consolidation_perimeter"],
                "fact_scope": observation["fact_scope"],
                "sign_convention": observation["sign_convention"],
                "official_source_ids": list(obs_sources),
                "source_fact_label": observation["source_fact_label"],
                "source_fact_anchor": observation["source_fact_anchor"],
                "source_fact_value_text": observation["source_fact_value_text"],
                "fact_origin": observation["fact_origin"],
                "reported_precision": observation["reported_precision"],
                **(
                    {"zero_value_basis": observation["zero_value_basis"]}
                    if value == 0
                    else {}
                ),
                **(
                    {"attribution_method": observation.get("attribution_method")}
                    if metric == "gaap_net_income_attributable"
                    else {}
                ),
            }
        )

    entity_id = str(entity["entity_id"])
    fiscal_periods = sorted({(key[1], key[2]) for key in by_key})
    derived_tolerances_by_period: dict[str, dict[str, float]] = {}
    for start_text, end_text in fiscal_periods:
        period = dates_to_period[(start_text, end_text)]
        for metric in REQUIRED_ACTUAL_METRICS:
            if (entity_id, start_text, end_text, metric) not in by_key:
                raise SystemExit(
                    f"actuals {period} missing canonical {metric}; missing disclosure is not zero"
                )
        required_rows = [
            by_key[(entity_id, start_text, end_text, metric)]
            for metric in REQUIRED_ACTUAL_METRICS
        ]
        comparable_fields = (
            "currency", "unit", "accounting_basis", "accounting_basis_id",
            "consolidation_perimeter",
        )
        if any(
            row.get(field) != required_rows[0].get(field)
            for row in required_rows[1:]
            for field in comparable_fields
        ):
            raise SystemExit(f"actuals {period} required metrics use inconsistent bases or units")
        target = by_key[(entity_id, start_text, end_text, "gaap_net_income_attributable")]
        attribution_method = target.get("attribution_method")
        bridge_present = [
            metric for metric in BRIDGE_METRICS
            if (entity_id, start_text, end_text, metric) in by_key
        ]
        if attribution_method == "direct_official_attributable_fact":
            if bridge_present and len(bridge_present) != len(BRIDGE_METRICS):
                missing = [metric for metric in BRIDGE_METRICS if metric not in bridge_present]
                raise SystemExit(
                    f"actuals {period} contains a partial net-income bridge missing {', '.join(missing)}"
                )
        elif attribution_method == "derived_from_reported_bridge":
            missing = [
                metric for metric in BRIDGE_METRICS
                if (entity_id, start_text, end_text, metric) not in by_key
            ]
            if missing:
                raise SystemExit(
                    f"actuals {period} attributable net income bridge missing {', '.join(missing)}; "
                    "NCI or another undisclosed item cannot be assumed to be zero"
                )
        else:
            raise SystemExit(
                f"actuals {period} gaap_net_income_attributable requires a direct official attributable fact "
                "or a complete reported bridge"
            )
        if attribution_method == "derived_from_reported_bridge" or bridge_present:
            rows = {
                metric: by_key[(entity_id, start_text, end_text, metric)]
                for metric in BRIDGE_METRICS
            }
            if any(
                rows[metric].get(field) != target.get(field)
                for metric in BRIDGE_METRICS
                for field in comparable_fields
            ):
                raise SystemExit(f"actuals {period} attributable bridge uses inconsistent bases or units")
            pretax = float(rows["pretax_income"]["value"])
            tax = float(rows["income_tax_expense"]["value"])
            consolidated = float(rows["consolidated_net_income"]["value"])
            nci = float(rows["noncontrolling_interest_net_income"]["value"])
            attributable = float(target["value"])
            pretax_tolerance = derived_equation_tolerance([
                rows["pretax_income"], rows["income_tax_expense"], rows["consolidated_net_income"]
            ])
            nci_tolerance = derived_equation_tolerance([
                rows["consolidated_net_income"], rows["noncontrolling_interest_net_income"], target
            ])
            if pretax_tolerance is None or nci_tolerance is None:
                raise SystemExit(f"actuals {period} reported precision is incomplete")
            derived_tolerances_by_period[period] = {
                "pretax_tax_to_consolidated_net_income": pretax_tolerance,
                "consolidated_net_income_nci_to_attributable": nci_tolerance,
            }
            if abs((pretax - tax) - consolidated) > pretax_tolerance + 1e-12:
                raise SystemExit(f"actuals {period} pretax-tax does not reconcile to consolidated net income")
            if abs((consolidated - nci) - attributable) > nci_tolerance + 1e-12:
                raise SystemExit(f"actuals {period} consolidated net income-NCI does not reconcile to attributable net income")

    receipt_core = {
        "contract_version": ACTUALS_CONTRACT_VERSION,
        "status": ACTUALS_LOCAL_TRUST_STATUS,
        "case_id": actuals["case_id"],
        "entity_id": entity_id,
        "actuals_sha256": "sha256:" + hashlib.sha256(actuals_path.read_bytes()).hexdigest(),
        "sealed_at": seal["sealed_at"],
        "retrieved_at": actuals["retrieved_at"],
        "information_cutoff_at": actuals["information_cutoff_at"],
        "official_source_ids": sorted(source_ids),
        "official_sources": sorted(
            [
                {
                    "source_id": sid,
                    "issuer_or_regulator": source["issuer_or_regulator"],
                    "document_type": source["document_type"],
                    "title": source["title"],
                    "published_at": source["published_at"],
                    "locator": source["locator"],
                    "content_sha256": source["content_sha256"],
                    "origin_class": source["origin_class"],
                }
                for sid, source in source_map.items()
            ],
            key=lambda row: row["source_id"],
        ),
        "derived_reconciliation_tolerances": {
            "method": "sum_half_reported_rounding_increments",
            "by_period": derived_tolerances_by_period,
        },
        "validated_observations": sorted(
            validated_receipts,
            key=lambda row: (row["entity_id"], row["period"], row["metric"]),
        ),
    }
    receipt = {**receipt_core, "receipt_id": canonical_payload_hash(receipt_core)}
    scoring_by_period = {
        (entity_key, dates_to_period[(start_text, end_text)], metric): row
        for (entity_key, start_text, end_text, metric), row in by_key.items()
    }
    return scoring_by_period, receipt


def interval_score(actual, low, high, denom, alpha=0.2):
    width = high - low
    if actual < low:
        width += (2 / alpha) * (low - actual)
    elif actual > high:
        width += (2 / alpha) * (actual - high)
    return width / abs(denom)


def output_for(snapshot, period):
    if snapshot.get("historical_forecasts"):
        return next(x for x in snapshot["historical_forecasts"] if x.get("period") == period)
    key = {"FY+1": "year_1", "FY+2": "year_2", "FY+3": "year_3_distribution"}[period]
    return snapshot["outputs"][key]


def val(output, *names):
    for name in names:
        if name in output and output[name] is not None:
            return float(output[name])
    return None


def sign(value):
    """Return a stable three-way sign for crossing-zero profit checks."""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--actuals", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--receipt", default=None,
                        help="external seal receipt path (default <round>/seal_receipts/<case>.json)")
    parser.add_argument("--allow-missing-receipt", action="store_true",
                        help=(
                            "score a pre-receipt legacy workspace; recorded as "
                            "forecast_seal_receipt_status=legacy_missing_unverified"
                        ))
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    actuals_path = Path(args.actuals).resolve()

    try:
        seal = core.verify_seal(workspace)
        core.assert_outside_sealed_area(workspace, actuals_path)
    except core.SealError as exc:
        raise SystemExit(f"seal verification failed: {exc}")

    # External receipt check: the in-workspace seal alone cannot prove the
    # workspace was not wholly rebuilt after actuals exposure; the receipt was
    # recorded outside the workspace at freeze time and must match exactly.
    receipt_path = Path(args.receipt).resolve() if args.receipt else workspace.parent / "seal_receipts" / f"{workspace.name}.json"
    forecast_seal_receipt_status = FORECAST_SEAL_RECEIPT_STATUS_LEGACY_MISSING
    expected_case_id = workspace.name
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"seal receipt unreadable: {exc}")
        problems = []
        if receipt.get("pack_hash") != seal["pack_hash"]:
            problems.append("pack_hash mismatch - workspace was resealed or rebuilt after the receipt")
        if receipt.get("sealed_at") != seal.get("sealed_at"):
            problems.append("sealed_at mismatch")
        if receipt.get("recorded_before_actuals") is not True:
            problems.append("recorded_before_actuals is not true")
        if problems:
            raise SystemExit("seal receipt verification failed: " + "; ".join(problems))
        expected_case_id = str(receipt.get("case_id") or workspace.name)
        forecast_seal_receipt_status = FORECAST_SEAL_RECEIPT_STATUS_VERIFIED
    elif not args.allow_missing_receipt:
        raise SystemExit(
            f"no external seal receipt at {receipt_path} - freeze_training_forecast.py records one "
            "at seal time; for pre-receipt legacy workspaces pass --allow-missing-receipt")

    try:
        actuals = json.loads(actuals_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"actuals unreadable: {exc}") from None
    if actuals.get("case_id") != expected_case_id:
        raise SystemExit(
            f"actuals.case_id must match the frozen case identity {expected_case_id}"
        )
    actual_observations, actuals_validation_receipt = validate_actuals(
        actuals, seal=seal, actuals_path=actuals_path
    )

    snap = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    rows = []
    entity_id = actuals["entity"]["entity_id"]
    periods = sorted({period for entity, period, _ in actual_observations if entity == entity_id})
    for period in periods:
        try:
            o = output_for(snap, period)
        except (KeyError, StopIteration):
            raise SystemExit(f"forecast snapshot has no output matching actuals period {period}") from None
        rev = float(actual_observations[(entity_id, period, "revenue")]["value"])
        profit = float(
            actual_observations[(entity_id, period, "gaap_net_income_attributable")]["value"]
        )
        operating_profit = float(
            actual_observations[(entity_id, period, "operating_profit")]["value"]
        )
        pretax_row = actual_observations.get((entity_id, period, "pretax_income"))
        tax_row = actual_observations.get((entity_id, period, "income_tax_expense"))
        pretax_profit = float(pretax_row["value"]) if pretax_row is not None else None
        tax_expense = float(tax_row["value"]) if tax_row is not None else None
        rp = val(o, "revenue_point", "revenue", "revenue_base", "revenue_M", "revenue_base_M")
        rl = val(o, "revenue_low", "revenue_bear", "revenue_low_M", "revenue_bear_M")
        rh = val(o, "revenue_high", "revenue_bull", "revenue_high_M", "revenue_bull_M")
        opp = val(o, "operating_profit_point", "operating_income_point",
                  "operating_profit", "operating_income")
        opl = val(o, "operating_profit_low", "operating_income_low",
                  "operating_profit_bear", "operating_income_bear")
        oph = val(o, "operating_profit_high", "operating_income_high",
                  "operating_profit_bull", "operating_income_bull")
        # ``profit_*`` is the sealed snapshot's compatibility name for GAAP
        # income attributable to parent shareholders.  Generic net_income,
        # profit, base/bear/bull and unit-suffixed aliases are deliberately not
        # accepted by the scorer; they cannot establish attribution scope.
        pp = val(o, "gaap_net_income_attributable_point", "profit_point")
        pl = val(o, "gaap_net_income_attributable_low", "profit_low")
        ph = val(o, "gaap_net_income_attributable_high", "profit_high")
        point = bool(o.get("point_evaluable", period != "FY+3"))
        if rev == 0:
            raise SystemExit(f"actuals {period} revenue is zero; scaled score is not evaluable")
        if point and rp is None:
            raise SystemExit(f"forecast {period} missing revenue point")
        if point and opp is None:
            raise SystemExit(f"forecast {period} missing operating_profit/operating_income point")
        if point and pp is None:
            raise SystemExit(f"forecast {period} missing GAAP net income attributable point")
        if rl is None or rh is None:
            raise SystemExit(f"forecast {period} missing revenue interval low/high")
        if opl is None or oph is None:
            raise SystemExit(f"forecast {period} missing operating_profit interval low/high")
        if pl is None or ph is None:
            raise SystemExit(f"forecast {period} missing GAAP net income attributable interval low/high")
        alpha = val(o, "interval_alpha")
        if alpha is None or not 0 < alpha < 1:
            raise SystemExit(
                f"forecast {period} interval_alpha must be frozen between zero and one"
            )
        for metric_name, low, high in (
            ("revenue", rl, rh),
            ("operating_profit", opl, oph),
            ("GAAP net_income", pl, ph),
        ):
            if low > high:
                raise SystemExit(
                    f"forecast {period} {metric_name} interval is not ordered low <= high"
                )
        rec = {
            "period": period,
            "point_evaluable": point,
            "actual_revenue": rev,
            "forecast_revenue": rp,
            "actual_operating_profit": operating_profit,
            "forecast_operating_profit": opp,
            "actual_pretax_profit": pretax_profit,
            "actual_tax_expense": tax_expense,
            "actual_net_income": profit,
            "forecast_net_income": pp,
            "actual_gaap_net_income_attributable": profit,
            "forecast_gaap_net_income_attributable": pp,
            # Backward-compatible evaluation keys retained for existing readers.
            "actual_profit": profit,
            "forecast_profit": pp,
            "interval_alpha": alpha,
        }
        if point:
            rec["revenue_ape"] = abs(rp - rev) / abs(rev)
            rec["revenue_signed_error"] = (rp - rev) / abs(rev)
            rec["profit_margin_error_pp"] = abs(pp / rp - profit / rev) * 100
            rec["operating_profit_scaled_ae"] = abs(opp - operating_profit) / abs(rev)
            rec["operating_profit_signed_error"] = (opp - operating_profit) / abs(rev)
            rec["net_income_scaled_ae"] = abs(pp - profit) / abs(rev)
            rec["net_income_signed_error"] = (pp - profit) / abs(rev)
            rec["net_income_sign_hit"] = sign(pp) == sign(profit)

        # Coverage and proper interval scores evaluate both point horizons and
        # distribution-only horizons.  point_evaluable controls only point
        # errors; it must never silently remove FY+3 from calibration.
        rec["revenue_hit"] = rl <= rev <= rh
        rec["revenue_interval_score"] = interval_score(rev, rl, rh, rev, alpha)
        rec["operating_profit_hit"] = opl <= operating_profit <= oph
        rec["operating_profit_interval_score"] = interval_score(
            operating_profit, opl, oph, rev, alpha)
        rec["net_income_hit"] = pl <= profit <= ph
        rec["net_income_interval_score"] = interval_score(profit, pl, ph, rev, alpha)
        # Backward-compatible aliases retained for existing reports/readers.
        rec["profit_hit"] = rec["net_income_hit"]
        rec["profit_interval_score"] = rec["net_income_interval_score"]
        rows.append(rec)

    pts = [r for r in rows if r["point_evaluable"]]

    def mean(population, key):
        values = [r[key] for r in population if key in r]
        return sum(values) / len(values) if values else None

    metrics = {
        "revenue_mape": mean(pts, "revenue_ape"),
        "profit_margin_mae_pp": mean(pts, "profit_margin_error_pp"),
        "operating_profit_scaled_mae": mean(pts, "operating_profit_scaled_ae"),
        "net_income_scaled_mae": mean(pts, "net_income_scaled_ae"),
        "net_income_sign_hit": mean(pts, "net_income_sign_hit"),
        "revenue_signed_bias": mean(pts, "revenue_signed_error"),
        "operating_profit_signed_bias": mean(pts, "operating_profit_signed_error"),
        "net_income_signed_bias": mean(pts, "net_income_signed_error"),
        "revenue_coverage": mean(rows, "revenue_hit"),
        "operating_profit_coverage": mean(rows, "operating_profit_hit"),
        "net_income_coverage": mean(rows, "net_income_hit"),
        "profit_coverage": mean(rows, "profit_hit"),
        "revenue_interval_score": mean(rows, "revenue_interval_score"),
        "operating_profit_interval_score": mean(rows, "operating_profit_interval_score"),
        "net_income_interval_score": mean(rows, "net_income_interval_score"),
        "profit_interval_score": mean(rows, "profit_interval_score"),
    }
    point_metric_rows = {
        "revenue_mape": "revenue_ape",
        "profit_margin_mae_pp": "profit_margin_error_pp",
        "operating_profit_scaled_mae": "operating_profit_scaled_ae",
        "net_income_scaled_mae": "net_income_scaled_ae",
        "net_income_sign_hit": "net_income_sign_hit",
        "revenue_signed_bias": "revenue_signed_error",
        "operating_profit_signed_bias": "operating_profit_signed_error",
        "net_income_signed_bias": "net_income_signed_error",
    }
    interval_metric_rows = {
        "revenue_coverage": "revenue_hit",
        "operating_profit_coverage": "operating_profit_hit",
        "net_income_coverage": "net_income_hit",
        "profit_coverage": "profit_hit",
        "revenue_interval_score": "revenue_interval_score",
        "operating_profit_interval_score": "operating_profit_interval_score",
        "net_income_interval_score": "net_income_interval_score",
        "profit_interval_score": "profit_interval_score",
    }
    metric_observation_counts = {
        metric: sum(1 for row in pts if row_key in row)
        for metric, row_key in point_metric_rows.items()
    }
    metric_observation_counts.update({
        metric: sum(1 for row in rows if row_key in row)
        for metric, row_key in interval_metric_rows.items()
    })
    scored_at = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt_errors = validate_actuals_receipt(
        actuals_validation_receipt,
        expected_case=expected_case_id,
        scored_at=scored_at,
        label="scored evaluation",
    )
    if receipt_errors:
        raise SystemExit("generated actuals validation receipt is invalid: " + "; ".join(receipt_errors))
    result = {"case_id": actuals.get("case_id"), "seal_hash": seal["pack_hash"], "hash_verified": True,
              "forecast_seal_receipt_status": forecast_seal_receipt_status,
              "seal_reverified_after_scoring": False, "actuals_retrieved_after_seal": True,
              "actuals_validation_receipt": actuals_validation_receipt,
              "scored_at": scored_at, "metrics": metrics,
              "metric_observation_counts": metric_observation_counts,
              "metric_identity_definition": {
                  "net_income": (
                      "GAAP net income attributable to parent shareholders; actual input metric "
                      "gaap_net_income_attributable and no generic net_income/profit alias"
                  )
              },
              "signed_error_definition": {
                  "direction": "forecast_minus_actual",
                  "revenue_denominator": "abs(actual_revenue)",
                  "operating_profit_denominator": "abs(actual_revenue)",
                  "net_income_denominator": "abs(actual_revenue)",
                  "scope": "point_evaluable periods only",
              },
              "interval_score_definition": {
                  "rule": "normalized interval score",
                  "nominal_miscoverage": "forecast output interval_alpha",
                  "denominator": "abs(actual_revenue)",
                  "scope": "all scored horizons",
              },
              "scores": rows}

    out = Path(args.output).resolve() if args.output else workspace / "evaluation" / "evaluation.json"
    try:
        core.assert_outside_sealed_area(workspace, out)
    except core.SealError as exc:
        raise SystemExit(f"refusing to write into the sealed area: {exc}")
    out.parent.mkdir(parents=True, exist_ok=True)

    vault = workspace / "actuals_vault"
    vault.mkdir(exist_ok=True)
    if actuals_path.parent != vault:
        shutil.copy2(actuals_path, vault / "actuals.json")

    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    try:
        core.verify_seal(workspace)
    except core.SealError as exc:
        raise SystemExit(f"scoring broke the seal - investigate: {exc}")
    result["seal_reverified_after_scoring"] = True
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
