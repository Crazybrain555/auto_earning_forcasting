#!/usr/bin/env python3
"""Validate and resolve the forecast-delivery artifact registry."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = SKILL_ROOT / "assets" / "artifact_registry.json"

SCHEMA_VERSION = "artifact-registry/v2"
VALID_REQUIREMENTS = {"core", "conditional"}
VALID_ARTIFACT_ROLES = {"input", "derived", "publication", "receipt"}
VALID_STAGES = {
    "decision_contract",
    "evidence_system",
    "causal_graph",
    "operating_model",
    "integrated_statements",
    "value_creation",
    "valuation",
    "scenarios_and_red_team",
    "validation_and_readiness",
    "publish_monitor_version",
}
VALID_FORMATS = {"json", "jsonl", "csv", "markdown", "xlsx"}

_TOP_LEVEL_FIELDS = {"schema_version", "publication_bundles", "materiality_routes", "artifacts"}
_PUBLICATION_BUNDLE_FIELDS = {"id", "stages"}
_ROUTE_FIELDS = {"id", "description"}
_ARTIFACT_FIELDS = {
    "id",
    "path",
    "requirement",
    "artifact_role",
    "stage",
    "format",
    "profiles",
    "template",
    "scaffold",
    "activation",
    "description",
}
_ACTIVATION_FIELDS = {"route_any"}
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
_ACTIVE_WORDS = {
    "active",
    "applicable",
    "accepted",
    "enabled",
    "include",
    "included",
    "material",
    "required",
    "true",
    "yes",
}
_INACTIVE_WORDS = {
    "disabled",
    "excluded",
    "false",
    "immaterial",
    "inactive",
    "no",
    "not-applicable",
    "not-material",
}
_ROUTE_STATUS_FIELDS = {"active", "applicable", "required", "status", "materiality"}
_ROUTE_METADATA_FIELDS = {"reason", "notes"}


def load_registry(path: Path | str | None = None) -> dict[str, Any]:
    """Load a registry document without mutating or resolving it."""

    registry_path = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("artifact registry must be a JSON object")
    return payload


def _normalise(value: object) -> str:
    return str(value).strip().lower().replace("_", "-")


def _is_safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def _validate_string_list(
    value: object,
    *,
    label: str,
    artifact_id: str,
    problems: list[str],
) -> list[str]:
    if not isinstance(value, list) or not value:
        problems.append(f"artifact {artifact_id}: {label} must be a non-empty list")
        return []
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            problems.append(f"artifact {artifact_id}: {label} values must be non-empty strings")
            continue
        strings.append(item)
    if len({_normalise(item) for item in strings}) != len(strings):
        problems.append(f"artifact {artifact_id}: {label} contains duplicate values")
    return strings


def validate_registry(registry: object, *, skill_root: Path | str) -> list[str]:
    """Return declaration errors; an empty list means the registry is usable."""

    problems: list[str] = []
    if not isinstance(registry, dict):
        return ["artifact registry must be an object"]

    unknown_top = sorted(set(registry) - _TOP_LEVEL_FIELDS)
    for field in unknown_top:
        problems.append(f"unknown registry field: {field}")
    if registry.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")

    publication_bundles = registry.get("publication_bundles")
    required_bundle_ids = {
        "evidence_bundle",
        "operating_model_bundle",
        "financial_forecast_bundle",
    }
    seen_bundle_ids: set[str] = set()
    assigned_bundle_stages: set[str] = set()
    if not isinstance(publication_bundles, list):
        problems.append("publication_bundles must be an array")
        publication_bundles = []
    for index, bundle in enumerate(publication_bundles):
        if not isinstance(bundle, dict):
            problems.append(f"publication bundle {index}: declaration must be an object")
            continue
        for field in sorted(set(bundle) - _PUBLICATION_BUNDLE_FIELDS):
            problems.append(f"publication bundle {index}: unknown field {field}")
        bundle_id = bundle.get("id")
        if not isinstance(bundle_id, str) or not _IDENTIFIER.fullmatch(bundle_id):
            problems.append(f"publication bundle {index}: invalid id")
            continue
        if bundle_id in seen_bundle_ids:
            problems.append(f"duplicate publication bundle id: {bundle_id}")
        seen_bundle_ids.add(bundle_id)
        stages = bundle.get("stages")
        if not isinstance(stages, list) or not stages or any(stage not in VALID_STAGES for stage in stages):
            problems.append(f"publication bundle {bundle_id}: stages must be known non-empty stage IDs")
            continue
        if len(stages) != len(set(stages)):
            problems.append(f"publication bundle {bundle_id}: duplicate stages")
        overlap = assigned_bundle_stages.intersection(stages)
        if overlap:
            problems.append(f"publication bundle {bundle_id}: stages overlap another bundle: {sorted(overlap)}")
        assigned_bundle_stages.update(stages)
    if seen_bundle_ids != required_bundle_ids:
        problems.append("publication_bundles must define the three capability bundles exactly once")

    routes = registry.get("materiality_routes")
    declared_routes: set[str] = set()
    if not isinstance(routes, list) or not routes:
        problems.append("materiality_routes must be a non-empty list")
        routes = []
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            problems.append(f"materiality route {index}: declaration must be an object")
            continue
        for field in sorted(set(route) - _ROUTE_FIELDS):
            problems.append(f"materiality route {index}: unknown declaration field {field}")
        route_id = route.get("id")
        if not isinstance(route_id, str) or not _IDENTIFIER.fullmatch(route_id):
            problems.append(f"materiality route {index}: id must be a lower-snake-case identifier")
        else:
            canonical_route = _normalise(route_id)
            if canonical_route in declared_routes:
                problems.append(f"duplicate materiality route id: {route_id}")
            declared_routes.add(canonical_route)
        if not isinstance(route.get("description"), str) or not route["description"].strip():
            problems.append(f"materiality route {route_id or index}: description must be non-empty")

    artifacts = registry.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        problems.append("artifacts must be a non-empty list")
        return problems

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    root = Path(skill_root).resolve()
    required_fields = {
        "id",
        "path",
        "requirement",
        "artifact_role",
        "stage",
        "format",
        "scaffold",
    }

    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            problems.append(f"artifact {index}: declaration must be an object")
            continue
        artifact_id = artifact.get("id")
        label = artifact_id if isinstance(artifact_id, str) and artifact_id else str(index)

        for field in sorted(set(artifact) - _ARTIFACT_FIELDS):
            problems.append(f"artifact {label}: unknown declaration field {field}")
        for field in sorted(required_fields - set(artifact)):
            problems.append(f"artifact {label}: missing declaration field {field}")

        if not isinstance(artifact_id, str) or not _IDENTIFIER.fullmatch(artifact_id):
            problems.append(f"artifact {label}: id must be a lower-snake-case identifier")
        else:
            canonical_id = _normalise(artifact_id)
            if canonical_id in seen_ids:
                problems.append(f"duplicate artifact id: {artifact_id}")
            seen_ids.add(canonical_id)

        path = artifact.get("path")
        if not _is_safe_relative_path(path):
            problems.append(f"artifact {label}: path must be a safe relative path")
        elif path in seen_paths:
            problems.append(f"duplicate artifact path: {path}")
        else:
            seen_paths.add(path)

        requirement = artifact.get("requirement")
        if requirement not in VALID_REQUIREMENTS:
            problems.append(f"artifact {label}: requirement must be core or conditional")
        role = artifact.get("artifact_role")
        if role not in VALID_ARTIFACT_ROLES:
            problems.append(f"artifact {label}: invalid artifact_role {role!r}")
        stage = artifact.get("stage")
        if stage not in VALID_STAGES:
            problems.append(f"artifact {label}: invalid stage {stage!r}")
        artifact_format = artifact.get("format")
        if artifact_format not in VALID_FORMATS:
            problems.append(f"artifact {label}: invalid format {artifact_format!r}")

        if "profiles" in artifact:
            _validate_string_list(
                artifact.get("profiles"),
                label="profiles",
                artifact_id=label,
                problems=problems,
            )

        scaffold = artifact.get("scaffold")
        if not isinstance(scaffold, bool):
            problems.append(f"artifact {label}: scaffold must be boolean")
        template = artifact.get("template")
        if template is not None:
            if not _is_safe_relative_path(template):
                problems.append(f"artifact {label}: template must be a safe relative path")
            else:
                template_path = (root / template).resolve()
                try:
                    template_path.relative_to(root)
                except ValueError:
                    problems.append(f"artifact {label}: template must remain inside skill root")
                else:
                    if not template_path.is_file():
                        problems.append(f"artifact {label}: template does not exist: {template}")
        elif scaffold is True:
            problems.append(f"artifact {label}: scaffolded artifact requires a template")

        if "description" in artifact and (
            not isinstance(artifact["description"], str) or not artifact["description"].strip()
        ):
            problems.append(f"artifact {label}: description must be non-empty")

        activation = artifact.get("activation")
        if requirement == "core" and activation is not None:
            problems.append(f"artifact {label}: core artifact cannot declare activation")
        if requirement == "conditional":
            if not isinstance(activation, dict) or not activation:
                problems.append(f"artifact {label}: conditional artifact requires activation")
                continue
            for field in sorted(set(activation) - _ACTIVATION_FIELDS):
                problems.append(f"artifact {label}: unknown activation field {field}")
            activation_count = 0
            if "route_any" in activation:
                route_values = _validate_string_list(
                    activation["route_any"],
                    label="activation.route_any",
                    artifact_id=label,
                    problems=problems,
                )
                activation_count += len(route_values)
                for route_id in route_values:
                    if _normalise(route_id) not in declared_routes:
                        problems.append(
                            f"artifact {label}: unknown materiality route {route_id!r}"
                        )
            if activation_count == 0:
                problems.append(f"artifact {label}: conditional artifact requires activation")

    return problems


def _is_active_declaration(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _normalise(value) in _ACTIVE_WORDS
    if isinstance(value, Mapping):
        for key in ("active", "applicable", "required", "status", "materiality"):
            if key in value:
                return _is_active_declaration(value[key])
        return True
    return False


def _status_problem(value: object, *, label: str) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and _normalise(value) in (_ACTIVE_WORDS | _INACTIVE_WORDS):
        return None
    return f"{label}: invalid materiality route status {value!r}"


def validate_manifest_routes(
    registry: Mapping[str, Any], manifest: Mapping[str, Any] | object
) -> list[str]:
    """Validate case-selected routes against the registry-owned vocabulary."""

    if not isinstance(manifest, Mapping):
        return ["manifest must be an object before materiality routes can be resolved"]
    known_routes = {
        _normalise(route.get("id"))
        for route in registry.get("materiality_routes", [])
        if isinstance(route, Mapping) and isinstance(route.get("id"), str)
    }
    declaration = manifest.get("materiality_routes", manifest.get("materiality_route", {}))
    problems: list[str] = []
    seen: set[str] = set()

    def validate_route(route_id: object, status: object = True, *, label: str) -> None:
        if not isinstance(route_id, str) or not route_id.strip():
            problems.append(f"{label}: materiality route id must be a non-empty string")
            return
        normalised_id = _normalise(route_id)
        if normalised_id in seen:
            problems.append(f"duplicate materiality route declaration: {route_id}")
        seen.add(normalised_id)
        if normalised_id not in known_routes:
            problems.append(f"unknown materiality route: {route_id}")

        if isinstance(status, Mapping):
            unknown_fields = set(status) - (_ROUTE_STATUS_FIELDS | _ROUTE_METADATA_FIELDS)
            for field in sorted(unknown_fields):
                problems.append(f"{label}: unknown materiality route declaration field {field}")
            status_fields = [field for field in _ROUTE_STATUS_FIELDS if field in status]
            if not status_fields:
                problems.append(f"{label}: materiality route status is required")
                return
            if len(status_fields) > 1:
                problems.append(
                    f"{label}: materiality route must use one status field, found {sorted(status_fields)}"
                )
            for field in status_fields:
                problem = _status_problem(status[field], label=f"{label}.{field}")
                if problem:
                    problems.append(problem)
            return
        problem = _status_problem(status, label=label)
        if problem:
            problems.append(problem)

    if isinstance(declaration, str):
        validate_route(declaration, True, label="materiality_routes")
    elif isinstance(declaration, list):
        for index, item in enumerate(declaration):
            label = f"materiality_routes[{index}]"
            if isinstance(item, str):
                validate_route(item, True, label=label)
            elif isinstance(item, Mapping):
                route_id = item.get("id", item.get("route_id"))
                status_payload = {
                    key: value
                    for key, value in item.items()
                    if key not in {"id", "route_id"}
                }
                if not status_payload:
                    status_payload = {"active": True}
                validate_route(route_id, status_payload, label=label)
            else:
                problems.append(f"{label}: route declaration must be a string or object")
    elif isinstance(declaration, Mapping):
        for route_id, status in declaration.items():
            validate_route(route_id, status, label=f"materiality_routes.{route_id}")
    else:
        problems.append("materiality_routes must be an object, array, or string")
    return problems


def _active_materiality_routes(manifest: Mapping[str, Any]) -> set[str]:
    declaration = manifest.get("materiality_routes", manifest.get("materiality_route", []))
    active: set[str] = set()
    if isinstance(declaration, str):
        active.add(_normalise(declaration))
    elif isinstance(declaration, list):
        for item in declaration:
            if isinstance(item, str):
                active.add(_normalise(item))
            elif isinstance(item, Mapping):
                route_id = item.get("id", item.get("route_id"))
                if isinstance(route_id, str) and _is_active_declaration(item):
                    active.add(_normalise(route_id))
    elif isinstance(declaration, Mapping):
        for route_id, status in declaration.items():
            if isinstance(route_id, str) and _is_active_declaration(status):
                active.add(_normalise(route_id))
    return active


def _declared_profiles(registry: Mapping[str, Any]) -> set[str]:
    """Return profile identifiers without assigning runtime meaning to them."""

    declared: set[str] = set()
    for artifact in registry.get("artifacts", []):
        if not isinstance(artifact, Mapping) or "profiles" not in artifact:
            continue
        profiles = artifact.get("profiles")
        if not isinstance(profiles, list):
            continue
        declared.update(
            item.strip()
            for item in profiles
            if isinstance(item, str) and item.strip()
        )
    return declared


def _resolve_profile(registry: Mapping[str, Any], profile: str | None) -> str | None:
    """Select a declared profile without inferring one from a run mode.

    An unprofiled registry is a complete inventory and needs no selector.  A
    one-profile registry is unambiguous.  A registry that declares multiple
    views requires the caller that owns the policy boundary to name one.
    """

    declared = _declared_profiles(registry)
    if not declared:
        return None
    if profile is None:
        if len(declared) > 1:
            raise ValueError(
                "artifact registry declares multiple artifact profiles; caller must pass profile explicitly"
            )
        return next(iter(declared))
    selected = str(profile).strip()
    if not selected or selected not in declared:
        raise ValueError(f"unknown artifact profile: {selected or '<blank>'}")
    return selected


def resolve_active_artifacts(
    registry: Mapping[str, Any],
    manifest: Mapping[str, Any] | None,
    *,
    profile: str | None = None,
) -> list[dict[str, Any]]:
    """Resolve core plus materiality-routed artifacts in declaration order."""

    manifest = manifest or {}
    route_problems = validate_manifest_routes(registry, manifest)
    if route_problems:
        raise ValueError("; ".join(route_problems))
    selected_profile = _resolve_profile(registry, profile)
    routes = _active_materiality_routes(manifest)
    active: list[dict[str, Any]] = []

    for artifact in registry.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        artifact_profiles = artifact.get("profiles")
        if (
            selected_profile is not None
            and artifact_profiles is not None
            and selected_profile not in artifact_profiles
        ):
            continue
        if artifact.get("requirement") == "core":
            active.append(artifact)
            continue
        if artifact.get("requirement") != "conditional":
            continue
        activation = artifact.get("activation") or {}
        route_match = bool(
            routes & {_normalise(item) for item in activation.get("route_any", [])}
        )
        if route_match:
            active.append(artifact)

    return active


def resolve_active_paths(
    registry: Mapping[str, Any],
    manifest: Mapping[str, Any] | None,
    *,
    profile: str | None = None,
) -> list[str]:
    """Return paths for :func:`resolve_active_artifacts`."""

    return [
        artifact["path"]
        for artifact in resolve_active_artifacts(registry, manifest, profile=profile)
    ]


def required_artifact_view_diagnostics(
    registry: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    profile: str | None = None,
) -> list[str]:
    """Describe drift in the non-authoritative manifest artifact view."""

    route_problems = validate_manifest_routes(registry, manifest)
    if route_problems:
        return route_problems
    expected = resolve_active_paths(registry, manifest, profile=profile)
    declared = manifest.get("required_artifacts")
    if not isinstance(declared, list):
        return ["required_artifacts generated view must be an array"]
    if any(not isinstance(item, str) or not item for item in declared):
        return ["required_artifacts generated view must contain non-empty strings"]

    diagnostics: list[str] = []
    duplicates = sorted({item for item in declared if declared.count(item) > 1})
    if duplicates:
        diagnostics.append("duplicate required_artifacts: " + ", ".join(duplicates))
    if set(declared) != set(expected):
        missing = [item for item in expected if item not in declared]
        extra = [item for item in declared if item not in expected]
        detail: list[str] = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("inactive/unknown " + ", ".join(extra))
        diagnostics.append("stale generated view: " + "; ".join(detail))
    return diagnostics
