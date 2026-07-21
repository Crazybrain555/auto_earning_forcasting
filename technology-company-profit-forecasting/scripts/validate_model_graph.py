#!/usr/bin/env python3
"""Validate the typed causal graph behind a forecast.

The graph is deliberately small and declarative.  It is not a second
spreadsheet engine; it proves that material outputs have one producer, that
the declared equations are dimensionally coherent, and that the investment
thesis can be traced to profit or free cash flow.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from equation_contract import explicit_boolean


ALLOWED_KINDS = {
    "actual", "observable", "input", "assumption", "state", "flow",
    "derived", "output", "check", "falsification", "competitor_response",
}
ADD_OPS = {"add", "sum", "subtract", "difference", "min", "max"}
MULTIPLY_OPS = {"multiply", "product"}
DIVIDE_OPS = {"divide", "ratio"}
PASSTHROUGH_OPS = {"lag", "lookup", "piecewise", "identity"}
ALLOWED_OPS = ADD_OPS | MULTIPLY_OPS | DIVIDE_OPS | PASSTHROUGH_OPS
FINANCIAL_CHAIN_ROLES = (
    "revenue",
    "operating_profit",
    "pretax_profit",
    "tax_expense",
    "noncontrolling_interest_net_income",
    "gaap_net_income_attributable",
)
ALLOWED_FINANCIAL_ROLES = set(FINANCIAL_CHAIN_ROLES) | {
    "noncontrolling_interest_net_income",
    "free_cash_flow",
}


def _error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def _unit_dimensions(raw: object) -> Counter[str] | None:
    """Parse simple multiplicative units into signed dimensions.

    Examples: ``unit * USD/unit -> USD`` and ``USD / unit -> USD*unit^-1``.
    Complex conversions belong in an explicit conversion node rather than in
    a hidden constant.
    """
    text = str(raw or "").strip().replace(" ", "")
    if not text:
        return None
    if text.lower() in {"1", "dimensionless", "ratio", "%", "percent"}:
        return Counter()
    dimensions: Counter[str] = Counter()
    numerator, *denominators = text.split("/")
    for token in filter(None, numerator.split("*")):
        dimensions[token] += 1
    for denominator in denominators:
        for token in filter(None, denominator.split("*")):
            dimensions[token] -= 1
    return Counter({key: value for key, value in dimensions.items() if value})


def _combined_unit(operation: str, inputs: list[Counter[str]]) -> Counter[str] | None:
    if not inputs:
        return None
    if operation in ADD_OPS:
        return inputs[0] if all(item == inputs[0] for item in inputs[1:]) else None
    if operation in MULTIPLY_OPS:
        result: Counter[str] = Counter()
        for item in inputs:
            result.update(item)
        return Counter({key: value for key, value in result.items() if value})
    if operation in DIVIDE_OPS:
        result = Counter(inputs[0])
        for item in inputs[1:]:
            result.subtract(item)
        return Counter({key: value for key, value in result.items() if value})
    if operation in PASSTHROUGH_OPS:
        return inputs[0]
    return None


def validate(graph: dict[str, Any], strict: bool = False) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    version = str(graph.get("schema_version") or "")
    if not version.startswith("2"):
        _error(errors, "schema_version", "model_graph.schema_version must be a v2 contract")
    if not str(graph.get("graph_id") or "").strip():
        _error(errors, "graph_id", "model_graph.graph_id is required")
    if not str(graph.get("as_of") or "").strip():
        _error(errors, "as_of", "model_graph.as_of is required")

    raw_nodes = graph.get("nodes")
    raw_equations = graph.get("equations")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        _error(errors, "nodes", "model_graph.nodes must be a non-empty array")
        raw_nodes = []
    if not isinstance(raw_equations, list) or not raw_equations:
        _error(errors, "equations", "model_graph.equations must be a non-empty array")
        raw_equations = []

    nodes: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            _error(errors, "node", f"node[{index}] must be an object")
            continue
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            _error(errors, "node_id", f"node[{index}] has no stable id")
            continue
        if node_id in nodes:
            _error(errors, "duplicate_node", f"duplicate node id {node_id}")
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in ALLOWED_KINDS:
            _error(errors, "node_kind", f"node {node_id} has unsupported kind {kind or '<blank>'}")
        if _unit_dimensions(node.get("unit")) is None:
            _error(errors, "node_unit", f"node {node_id} must declare a unit")
        financial_role = str(node.get("financial_role") or "").strip().lower()
        if financial_role and financial_role not in ALLOWED_FINANCIAL_ROLES:
            _error(
                errors,
                "financial_role",
                f"node {node_id} has unsupported financial_role {financial_role}; "
                "generic profit is not a typed statement destination",
            )
        nodes[node_id] = node

    producers: dict[str, list[str]] = defaultdict(list)
    adjacency: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {node_id: 0 for node_id in nodes}
    equation_ids: set[str] = set()

    for index, equation in enumerate(raw_equations):
        if not isinstance(equation, dict):
            _error(errors, "equation", f"equation[{index}] must be an object")
            continue
        equation_id = str(equation.get("id") or "").strip()
        if not equation_id:
            _error(errors, "equation_id", f"equation[{index}] has no stable id")
            equation_id = f"equation[{index}]"
        elif equation_id in equation_ids:
            _error(errors, "duplicate_equation", f"duplicate equation id {equation_id}")
        equation_ids.add(equation_id)

        operation = str(equation.get("operation") or "").strip()
        if operation not in ALLOWED_OPS:
            _error(errors, "operation", f"equation {equation_id} has unsupported operation {operation or '<blank>'}")
        output = str(equation.get("output") or "").strip()
        inputs = equation.get("inputs")
        if output not in nodes:
            _error(errors, "unknown_output", f"equation {equation_id} output {output or '<blank>'} is not a node")
        if not isinstance(inputs, list) or not inputs:
            _error(errors, "equation_inputs", f"equation {equation_id} needs input node ids")
            inputs = []
        unknown = [str(item) for item in inputs if str(item) not in nodes]
        if unknown:
            _error(errors, "unknown_input", f"equation {equation_id} references unknown inputs: {', '.join(unknown)}")
        if output in nodes:
            producers[output].append(equation_id)

        partition = equation.get("partition")
        if partition is not None:
            if not isinstance(partition, dict):
                _error(errors, "partition", f"equation {equation_id} partition must be an object")
            else:
                if not str(partition.get("partition_id") or "").strip():
                    _error(errors, "partition", f"equation {equation_id} partition_id is required")
                if not str(partition.get("dimension") or "").strip():
                    _error(errors, "partition", f"equation {equation_id} partition dimension is required")
                exhaustive = explicit_boolean(partition.get("exhaustive"))
                mutually_exclusive = explicit_boolean(partition.get("mutually_exclusive"))
                reconciles = explicit_boolean(partition.get("reconciles_to_parent"))
                if exhaustive is None or mutually_exclusive is None or reconciles is None:
                    _error(
                        errors,
                        "partition",
                        f"equation {equation_id} partition booleans must be explicitly declared",
                    )
                elif reconciles and not (exhaustive and mutually_exclusive):
                    _error(
                        errors,
                        "partition",
                        f"equation {equation_id} cannot reconcile a partial or overlapping partition to its parent",
                    )

        known_inputs = [str(item) for item in inputs if str(item) in nodes]
        if output in nodes and known_inputs and operation in ALLOWED_OPS:
            input_units = [_unit_dimensions(nodes[item].get("unit")) for item in known_inputs]
            expected = _combined_unit(operation, [item for item in input_units if item is not None])
            actual = _unit_dimensions(nodes[output].get("unit"))
            if expected is None or actual != expected:
                _error(
                    errors,
                    "unit_mismatch",
                    f"equation {equation_id}: {operation}({', '.join(nodes[item].get('unit', '') for item in known_inputs)}) "
                    f"cannot produce {nodes[output].get('unit', '')}",
                )

        if output in nodes:
            for source in known_inputs:
                if output not in adjacency[source]:
                    adjacency[source].add(output)
                    indegree[output] = indegree.get(output, 0) + 1

    for node_id, equation_ids_for_node in producers.items():
        if len(equation_ids_for_node) > 1:
            _error(
                errors,
                "multiple_producers",
                f"node {node_id} has multiple producers: {', '.join(equation_ids_for_node)}",
            )
    for node_id, node in nodes.items():
        if node.get("kind") in {"derived", "output", "check"} and not producers.get(node_id):
            _error(errors, "missing_producer", f"{node.get('kind')} node {node_id} has no producer equation")

    # Kahn's algorithm proves the equation graph is acyclic.
    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    indegree_work = dict(indegree)
    while queue:
        source = queue.popleft()
        visited += 1
        for target in adjacency.get(source, set()):
            indegree_work[target] -= 1
            if indegree_work[target] == 0:
                queue.append(target)
    if nodes and visited != len(nodes):
        _error(errors, "cycle", "equation graph contains a causal cycle")

    main_line = graph.get("main_line")
    if not isinstance(main_line, dict):
        _error(errors, "main_line", "model_graph.main_line is required")
        main_line = {}
    carriers = [str(item) for item in (main_line.get("carrier_node_ids") or [])]
    targets = [str(item) for item in (main_line.get("target_node_ids") or [])]
    if not carriers:
        _error(errors, "main_line_carriers", "main line must name its material carrier nodes")
    unknown_carriers = [item for item in carriers if item not in nodes]
    unknown_targets = [item for item in targets if item not in nodes]
    if unknown_carriers or unknown_targets:
        _error(errors, "main_line_reference", "main line references unknown carrier or target nodes")

    valid_targets = [
        item for item in targets
        if item in nodes
        and str(nodes[item].get("financial_role") or "").lower()
        == "gaap_net_income_attributable"
    ]
    if not valid_targets:
        _error(
            errors,
            "main_line_financial_chain",
            "main line must terminate at typed GAAP net income attributable; a generic profit/FCF node "
            "cannot replace the reported profit chain",
        )

    def reaches(source: str, targets_to_find: set[str]) -> bool:
        pending = [source]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current in targets_to_find:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(adjacency.get(current, set()) - seen)
        return False

    if valid_targets and carriers and not all(
        carrier in nodes and reaches(carrier, set(valid_targets)) for carrier in carriers
    ):
        _error(errors, "main_line_unreachable", "every carrier must have a causal path to GAAP net income attributable")

    role_nodes = {
        role: {
            node_id
            for node_id, node in nodes.items()
            if str(node.get("financial_role") or "").strip().lower() == role
        }
        for role in FINANCIAL_CHAIN_ROLES
    }
    missing_roles = [role for role in FINANCIAL_CHAIN_ROLES if not role_nodes[role]]
    if missing_roles:
        _error(
            errors,
            "main_line_financial_chain",
            "typed statement chain missing financial roles: " + ", ".join(missing_roles),
        )
    elif valid_targets:
        coherent_chain = False
        for net_income_target in valid_targets:
            pretax_to_target = {
                node_id
                for node_id in role_nodes["pretax_profit"]
                if reaches(node_id, {net_income_target})
            }
            operating_to_target = {
                node_id
                for node_id in role_nodes["operating_profit"]
                if pretax_to_target and reaches(node_id, pretax_to_target)
            }
            revenue_to_target = {
                node_id
                for node_id in role_nodes["revenue"]
                if operating_to_target and reaches(node_id, operating_to_target)
            }
            tax_reaches_target = any(
                reaches(node_id, {net_income_target})
                for node_id in role_nodes["tax_expense"]
            )
            nci_reaches_target = any(
                reaches(node_id, {net_income_target})
                for node_id in role_nodes["noncontrolling_interest_net_income"]
            )
            if revenue_to_target and tax_reaches_target and nci_reaches_target:
                coherent_chain = True
                break
        if not coherent_chain:
            _error(
                errors,
                "main_line_financial_chain",
                "one coherent typed path must connect revenue -> operating_profit -> pretax_profit, "
                "with tax_expense and noncontrolling_interest_net_income feeding the same declared "
                "gaap_net_income_attributable target",
            )

    falsification_ids = [str(item) for item in (main_line.get("falsification_ids") or [])]
    if not falsification_ids or any(
        item not in nodes or nodes[item].get("kind") != "falsification" for item in falsification_ids
    ):
        _error(errors, "main_line_falsification", "main line must name observable falsification nodes")
    competitor_ids = [str(item) for item in (main_line.get("competitor_response_node_ids") or [])]
    if not competitor_ids or any(
        item not in nodes or nodes[item].get("kind") != "competitor_response" for item in competitor_ids
    ):
        _error(errors, "main_line_competitor_response", "main line must model a competitor-response node")

    return {
        "valid": not errors,
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "nodes": len(nodes),
            "equations": len(raw_equations),
            "main_line_carriers": len(carriers),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a v2 typed causal model graph.")
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.graph.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("root must be an object")
        result = validate(payload, strict=args.strict)
    except Exception as exc:
        result = {"valid": False, "strict": args.strict, "errors": [{"code": "invalid_json", "detail": str(exc)}], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
