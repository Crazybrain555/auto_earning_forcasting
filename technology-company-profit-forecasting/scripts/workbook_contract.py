#!/usr/bin/env python3
"""Inspect real workbook cells used by the causal profit model.

The contract deliberately does not reward workbook size, sheet count, or a
minimum number of formulas.  It distinguishes authored inputs from derived
outputs: an input binding may be a hardcoded cell, while every published
profit-chain output must bind to an existing formula cell.
"""

from __future__ import annotations

import posixpath
import re
import zipfile
import math
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_REFERENCE_RE = re.compile(
    r"^(?P<sheet>'(?:[^']|'')+'|[^!]+)!(?P<cell>\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)$"
)
FORMULA_REFERENCE_RE = re.compile(
    r"(?P<sheet>'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_. ]*)!"
    r"(?P<cell>\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)"
)


@dataclass(frozen=True)
class CellRecord:
    coordinate: str
    formula: str | None
    cached_value: str | None


@dataclass(frozen=True)
class WorksheetRecord:
    name: str
    cells: dict[str, CellRecord]


@dataclass(frozen=True)
class WorkbookRecord:
    sheets: dict[str, WorksheetRecord]
    cached_errors: dict[str, int]

    @property
    def formula_count(self) -> int:
        return sum(
            cell.formula is not None
            for sheet in self.sheets.values()
            for cell in sheet.cells.values()
        )

    def sheet(self, name: str) -> WorksheetRecord | None:
        return self.sheets.get(name.casefold())


def _relationship_target(target: str) -> str:
    normalized = target.lstrip("/")
    if normalized.startswith("xl/"):
        return posixpath.normpath(normalized)
    return posixpath.normpath(posixpath.join("xl", normalized))


def parse_cell_reference(value: object) -> tuple[str, str] | None:
    """Return normalized ``(sheet, coordinate)`` for an exact A1 binding."""

    text = str(value or "").strip()
    match = CELL_REFERENCE_RE.fullmatch(text)
    if not match:
        return None
    sheet = match.group("sheet").strip()
    if sheet.startswith("'") and sheet.endswith("'"):
        sheet = sheet[1:-1].replace("''", "'")
    coordinate = match.group("cell").replace("$", "").upper()
    return sheet, coordinate


def formula_references(value: object) -> list[tuple[str, str]]:
    text = str(value or "").strip()
    if text.startswith("="):
        text = text[1:]
    references: list[tuple[str, str]] = []
    for match in FORMULA_REFERENCE_RE.finditer(text):
        parsed = parse_cell_reference(f"{match.group('sheet')}!{match.group('cell')}")
        if parsed:
            references.append(parsed)
    return references


def parse_workbook(path: Path) -> WorkbookRecord:
    """Read workbook relationships and material cells without Excel/runtime deps."""

    cached_errors = {"#REF!": 0, "#NAME?": 0, "#DIV/0!": 0, "#VALUE!": 0}
    with zipfile.ZipFile(path) as archive:
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        relationship_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            node.attrib.get("Id", ""): _relationship_target(node.attrib.get("Target", ""))
            for node in relationship_root.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
            if node.attrib.get("Id") and node.attrib.get("Target")
        }
        worksheets: dict[str, WorksheetRecord] = {}
        for sheet_node in workbook_root.findall(f".//{{{MAIN_NS}}}sheet"):
            name = str(sheet_node.attrib.get("name") or "").strip()
            relationship_id = sheet_node.attrib.get(f"{{{OFFICE_REL_NS}}}id", "")
            target = relationship_targets.get(relationship_id)
            if not name or not target:
                continue
            worksheet_root = ET.fromstring(archive.read(target))
            cells: dict[str, CellRecord] = {}
            for cell_node in worksheet_root.findall(f".//{{{MAIN_NS}}}c"):
                coordinate = str(cell_node.attrib.get("r") or "").replace("$", "").upper()
                if not coordinate:
                    continue
                formula_node = cell_node.find(f"{{{MAIN_NS}}}f")
                value_node = cell_node.find(f"{{{MAIN_NS}}}v")
                formula = None if formula_node is None else (formula_node.text or "")
                cached_value = None if value_node is None else (value_node.text or "")
                cells[coordinate] = CellRecord(coordinate, formula, cached_value)
                if cached_value in cached_errors:
                    cached_errors[cached_value] += 1
            worksheets[name.casefold()] = WorksheetRecord(name=name, cells=cells)
    return WorkbookRecord(sheets=worksheets, cached_errors=cached_errors)


def _validate_binding(
    workbook: WorkbookRecord,
    value: object,
    *,
    label: str,
    require_formula: bool,
) -> list[str]:
    problems: list[str] = []
    reference = parse_cell_reference(value)
    if reference is None:
        if require_formula:
            return [f"{label}: must bind to one exact workbook formula cell"]
        references = formula_references(value)
        if not references:
            return [f"{label}: must bind to an exact workbook cell or formula with workbook references"]
    else:
        references = [reference]

    for sheet_name, coordinate in references:
        sheet = workbook.sheet(sheet_name)
        if sheet is None:
            problems.append(f"{label}: unknown sheet {sheet_name}")
            continue
        cell = sheet.cells.get(coordinate)
        if cell is None:
            problems.append(f"{label}: missing workbook cell {sheet.name}!{coordinate}")
            continue
        if require_formula and cell.formula is None:
            problems.append(f"{label}: {sheet.name}!{coordinate} must be a formula cell, not a hardcoded output")
    return problems


def validate_scenario_workbook_bindings(
    workbook: WorkbookRecord,
    scenarios: list[dict],
) -> list[str]:
    """Validate authored shock inputs and derived reported-profit outputs."""

    problems: list[str] = []
    for scenario_index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, dict):
            continue
        scenario_id = str(scenario.get("id") or "").strip() or f"scenario-{scenario_index}"
        for shock_index, shock in enumerate(scenario.get("shocks") or [], 1):
            if not isinstance(shock, dict):
                continue
            problems.extend(_validate_binding(
                workbook,
                shock.get("model_cell_or_formula"),
                label=f"{scenario_id}:shock-{shock_index}",
                require_formula=False,
            ))
        for period_index, row in enumerate(scenario.get("profit_chain_periods") or [], 1):
            if not isinstance(row, dict):
                continue
            period = str(row.get("period") or "").strip() or f"period-{period_index}"
            model_cells = row.get("model_cells")
            if not isinstance(model_cells, dict):
                continue
            for field, binding in model_cells.items():
                problems.extend(_validate_binding(
                    workbook,
                    binding,
                    label=f"{scenario_id}:{period}:model_cells.{field}",
                    require_formula=True,
                ))
    return problems


def _finite_cached_number(value: object) -> float | None:
    """Parse a finite cached workbook value without treating blanks as zero."""

    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _bound_cached_number(
    workbook: WorkbookRecord,
    value: object,
    *,
    label: str,
) -> tuple[float | None, list[str]]:
    """Resolve one exact workbook binding to its cached numeric value."""

    reference = parse_cell_reference(value)
    if reference is None:
        return None, [f"{label}: must bind to one exact workbook cell"]
    sheet_name, coordinate = reference
    sheet = workbook.sheet(sheet_name)
    if sheet is None:
        return None, [f"{label}: unknown sheet {sheet_name}"]
    cell = sheet.cells.get(coordinate)
    if cell is None:
        return None, [f"{label}: missing workbook cell {sheet.name}!{coordinate}"]
    number = _finite_cached_number(cell.cached_value)
    if number is None:
        return None, [f"{label}: {sheet.name}!{coordinate} has no finite cached numeric value"]
    return number, []


def validate_model_check_bindings(
    workbook: WorkbookRecord,
    checks: list[dict],
) -> list[str]:
    """Recompute zero-valued accounting checks from bound workbook operands.

    ``model_checks.json`` is an assurance view, not an authority.  A green
    status and a typed residual therefore cannot prove closure by themselves.
    Each check supplies a signed list of workbook cells; this function reads
    those operands and recomputes the residual independently.  Signed sums
    cover statement, roll-forward and consolidation identities without
    imposing a company-specific formula or a minimum number of checks.
    """

    problems: list[str] = []
    for index, row in enumerate(checks, 1):
        if not isinstance(row, dict):
            problems.append(f"model-check[{index}]: check must be an object")
            continue
        check_id = str(row.get("id") or "").strip() or f"model-check[{index}]"
        calculation = row.get("calculation")
        if not isinstance(calculation, dict):
            problems.append(f"{check_id}: structured calculation missing")
            continue
        if str(calculation.get("operation") or "").strip() != "signed_sum":
            problems.append(f"{check_id}: calculation.operation must be signed_sum")
            continue
        terms = calculation.get("terms")
        if not isinstance(terms, list) or not terms:
            problems.append(f"{check_id}: calculation.terms must contain bound operands")
            continue

        computed = 0.0
        term_error = False
        for term_index, term in enumerate(terms, 1):
            term_label = f"{check_id}:term-{term_index}"
            if not isinstance(term, dict):
                problems.append(f"{term_label}: term must be an object")
                term_error = True
                continue
            coefficient = _finite_cached_number(term.get("coefficient"))
            if coefficient is None:
                problems.append(f"{term_label}: coefficient must be finite")
                term_error = True
                continue
            number, binding_problems = _bound_cached_number(
                workbook,
                term.get("model_cell"),
                label=term_label,
            )
            if binding_problems:
                problems.extend(binding_problems)
                term_error = True
                continue
            assert number is not None
            computed += coefficient * number
        if term_error:
            continue

        declared = _finite_cached_number(row.get("value"))
        tolerance = _finite_cached_number(row.get("tolerance"))
        if declared is None:
            problems.append(f"{check_id}: declared residual must be finite")
            continue
        if tolerance is None or tolerance < 0:
            problems.append(f"{check_id}: tolerance must be a non-negative finite number")
            continue
        comparison_tolerance = max(1e-9, tolerance * 1e-9)
        if not math.isclose(declared, computed, rel_tol=1e-9, abs_tol=comparison_tolerance):
            problems.append(
                f"{check_id}: declared residual {declared:g} does not equal "
                f"workbook-recomputed residual {computed:g}"
            )
        if abs(computed) > tolerance + 1e-9:
            problems.append(
                f"{check_id}: workbook-recomputed residual {computed:g} exceeds tolerance {tolerance:g}"
            )
    return problems
