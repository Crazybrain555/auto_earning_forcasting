# SanDisk Financial Model Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an auditable FY2026E–FY2030E SanDisk operating model and current valuation as of 2026-07-17 12:23 ET (intraday).

**Architecture:** Freeze primary-source facts in a source manifest, normalize SanDisk's post-separation perimeter, and forecast NAND revenue from bit shipments, price/mix, cost per bit, utilization, and end-market mix. Generate bear/base/bull scenarios and value both current-cycle and normalized earnings without capitalizing peak margins indefinitely.

**Tech Stack:** Python 3, openpyxl, LibreOffice recalculation, CSV/JSON source records, SEC/IR primary documents, project-local arXiv and EdgarTools MCPs where useful.

---

### Task 1: Freeze the research contract and source pack

**Files:**
- Create: `research/sandisk/source_manifest.csv`
- Create: `research/sandisk/research_contract.json`

1. Fix entity `SanDisk Corporation`, security `NASDAQ:SNDK`, USD, SanDisk fiscal years, and cutoff `2026-07-17T12:23:00-04:00`; do not describe the intraday price as a closing price.
2. Retrieve SEC filings, earnings materials, investor presentations, current market price, and industry supply/demand evidence published by the cutoff.
3. Record publication date, retrieval time, evidence tier, metric/period, stable URL, and limitations for every load-bearing fact.
4. Preserve conflicts and avoid treating market forecasts as company-reported facts.

### Task 2: Normalize historicals and separation perimeter

**Files:**
- Create: `research/sandisk/model_inputs.json`
- Create: `research/sandisk/assumption_register.csv`

1. Reconcile FY2023–FY2025 and FY2026 year-to-date revenue, gross profit, operating expenses, operating income, net income, cash, debt, and diluted shares.
2. Document the Western Digital separation, retained/transferred liabilities, transition items, and differences between GAAP and non-GAAP results.
3. Split revenue by end market where disclosed and label all inferred allocation or NAND price/bit assumptions.
4. Classify SanDisk as commodity memory/storage with a smaller enterprise-SSD regime-break option.

### Task 3: Specify workbook tests before implementation

**Files:**
- Create: `tests/test_sandisk_model.py`

1. Assert the workbook contains `Summary`, `Historicals`, `Drivers`, `Forecast`, `Scenarios`, `Valuation`, `Assumptions`, and `Sources` sheets.
2. Assert FY2026E–FY2030E revenue and net income are formulas, not hardcoded values.
3. Assert scenario probabilities sum to 100%, valuation formulas reference forecast outputs, and no external workbook links exist.
4. Run the test before creating the workbook and confirm it fails because the output does not exist.

### Task 4: Build the dynamic Excel model

**Files:**
- Create: `research/sandisk/build_model.py`
- Create: `research/sandisk/SanDisk_financial_model_2026-07-17.xlsx`

1. Create source-linked historical statements and driver schedules.
2. Model revenue as prior-period base × bit growth × price/mix change, with explicit utilization and enterprise-mix assumptions.
3. Build gross profit from gross margin assumptions linked to pricing, cost per bit, and utilization; bridge to GAAP operating and net income.
4. Add quarterly FY2027 estimates, annual FY2026E–FY2030E forecasts, 80% intervals, and bear/base/bull probabilities.
5. Add market capitalization, enterprise value, P/E, EV/sales, EV/EBITDA, and normalized-cycle valuation sensitivities.
6. Apply financial-model color conventions, comments, units, zero/negative formats, and source notes.

### Task 5: Write the investor read-through and freeze outputs

**Files:**
- Create: `research/sandisk/REPORT_zh.md`
- Create: `research/sandisk/forecast_snapshot.json`

1. State base/bear/bull operating paths, valuation ranges, current-price implications, and key uncertainty bands.
2. Separate facts, model assumptions, and unverified hypotheses.
3. Identify the first failure points, monitoring triggers, and evidence that would upgrade or kill the thesis.
4. Freeze the source and model hashes in an immutable snapshot.

### Task 6: Recalculate and verify

**Files:**
- Test: `tests/test_sandisk_model.py`
- Verify: `research/sandisk/SanDisk_financial_model_2026-07-17.xlsx`

1. Recalculate the workbook with LibreOffice.
2. Scan every formula cell for `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, and `#NAME?`.
3. Run workbook tests and cross-check selected formulas against independently calculated values.
4. Run the Skill package self-test and report any evidence gaps honestly.
