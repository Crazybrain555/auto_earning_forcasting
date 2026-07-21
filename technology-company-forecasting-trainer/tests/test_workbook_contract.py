"""Workbook assurance checks real output bindings, not formula-count proxies."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from workbook_contract import (  # noqa: E402
    parse_workbook,
    validate_model_check_bindings,
    validate_scenario_workbook_bindings,
)


CHAIN_FIELDS = (
    "revenue",
    "operating_costs_and_expenses",
    "operating_profit",
    "nonoperating_income_expense_net",
    "pretax_profit",
    "tax_expense",
    "net_income",
    "net_income_attributable_to_noncontrolling_interests",
    "net_income_attributable",
)


def _write_workbook(
    path: Path,
    *,
    hardcode_output: bool = False,
    balance_error: bool = False,
) -> None:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    workbook = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<workbook xmlns="{main_ns}" xmlns:r="{rel_ns}"><sheets>'
        '<sheet name="Drivers" sheetId="1" r:id="rId1"/>'
        '<sheet name="Scenario PnL" sheetId="2" r:id="rId2"/>'
        "</sheets></workbook>"
    )
    rels = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{package_rel_ns}">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/drivers.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/scenario.xml"/>'
        "</Relationships>"
    )
    drivers = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{main_ns}"><sheetData>'
        '<row r="2"><c r="B2"><v>150</v></c></row>'
        '<row r="3"><c r="B3"><v>60</v></c></row>'
        f'<row r="4"><c r="B4"><v>{80 if balance_error else 90}</v></c></row>'
        '</sheetData></worksheet>'
    )
    cells = []
    for column_index, column in enumerate("BCDEFGHIJ", 1):
        if hardcode_output and column == "B":
            cells.append(f'<c r="{column}12"><v>{column_index}</v></c>')
        else:
            cells.append(
                f'<c r="{column}12"><f>Drivers!$B$2+{column_index}</f><v>{100 + column_index}</v></c>'
            )
    scenario = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{main_ns}"><sheetData><row r="12">'
        + "".join(cells)
        + "</row></sheetData></worksheet>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/drivers.xml", drivers)
        archive.writestr("xl/worksheets/scenario.xml", scenario)


def _scenario(reference_sheet: str = "'Scenario PnL'") -> list[dict]:
    return [{
        "id": "base",
        "probability": 1.0,
        "shocks": [{
            "node_id": "demand",
            "model_cell_or_formula": "Drivers!$B$2",
        }],
        "profit_chain_periods": [{
            "period": "FY2027",
            "model_cells": {
                field: f"{reference_sheet}!${column}$12"
                for field, column in zip(CHAIN_FIELDS, "BCDEFGHIJ")
            },
        }],
    }]


def test_existing_formula_outputs_and_hardcoded_input_pass(tmp_path: Path) -> None:
    path = tmp_path / "model.xlsx"
    _write_workbook(path)
    workbook = parse_workbook(path)

    assert workbook.formula_count == len(CHAIN_FIELDS)
    assert validate_scenario_workbook_bindings(workbook, _scenario()) == []


def test_nonexistent_sheet_or_cell_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "model.xlsx"
    _write_workbook(path)

    problems = validate_scenario_workbook_bindings(
        parse_workbook(path),
        _scenario("Missing Sheet"),
    )

    assert any("unknown sheet" in problem for problem in problems)


def test_material_output_cannot_be_a_hardcoded_value(tmp_path: Path) -> None:
    path = tmp_path / "model.xlsx"
    _write_workbook(path, hardcode_output=True)

    problems = validate_scenario_workbook_bindings(parse_workbook(path), _scenario())

    assert any("base:FY2027:model_cells.revenue" in problem and "formula cell" in problem for problem in problems)


def _balance_check() -> list[dict]:
    return [{
        "id": "balance-sheet",
        "category": "balance_sheet",
        "calculation": {
            "operation": "signed_sum",
            "terms": [
                {"name": "assets", "coefficient": 1.0, "model_cell": "Drivers!B2"},
                {"name": "liabilities", "coefficient": -1.0, "model_cell": "Drivers!B3"},
                {"name": "equity", "coefficient": -1.0, "model_cell": "Drivers!B4"},
            ],
        },
        "value": 0.0,
        "tolerance": 0.0,
        "unit": "USD",
        "status": "passed",
    }]


def test_model_check_is_recomputed_from_bound_workbook_operands(tmp_path: Path) -> None:
    path = tmp_path / "model.xlsx"
    _write_workbook(path)

    assert validate_model_check_bindings(parse_workbook(path), _balance_check()) == []


def test_green_status_and_zero_declared_residual_cannot_hide_broken_identity(tmp_path: Path) -> None:
    path = tmp_path / "model.xlsx"
    _write_workbook(path, balance_error=True)

    problems = validate_model_check_bindings(parse_workbook(path), _balance_check())

    assert any("declared residual" in problem for problem in problems), problems
    assert any("workbook-recomputed residual" in problem and "exceeds" in problem for problem in problems), problems
