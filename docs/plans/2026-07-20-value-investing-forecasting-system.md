# Value-investing forecasting system rewrite plan

> Date: 2026-07-20
> Scope: `forecasting-skills/`, local backend/webapp, and Codex-only hosted Site

## Objective

Replace the remaining weighted-mechanism framework with one shared Claude/Codex method that turns point-in-time evidence into a falsifiable causal model, integrated financial statements, value-creation analysis, and market-implied valuation. Huatai and Goldman workbooks are calibration examples, not normative templates.

## Non-negotiable design rules

1. Facts, management claims, technical boundaries, leading indicators, and analyst assumptions remain separate.
2. Subjective judgement selects the main causal question, scenarios, required return, and margin of safety; it must not alter historical facts, accounting identities, or model checks.
3. No weighted evidence score or mechanism-weight blend may determine the forecast.
4. Every material forecast must trace through evidence -> causal link -> operating driver -> accounting line -> cash flow/value -> falsification trigger.
5. The model must cover the income statement, balance sheet, cash flow statement, capital intensity, working capital, ROIC, reinvestment, and fade.
6. Papers, patents, roadmaps, TRL, MRL, qualification, capacity, yield, adoption, and revenue recognition are distinct gates.
7. Industry lenses become optional calibration packs. The core is composed from economic/accounting equation primitives, not company labels.
8. Claude and Codex use one canonical skill tree, schema set, validator suite, and tests; only their execution adapters may differ.

## Work plan

### 1. Baseline and RED tests

- Snapshot the current canonical skill outside the nested skills repository for before/after evaluation.
- Add a method-system benchmark with at least three prompts: capacity-ramp hardware, recurring/platform economics, and paper/patent-to-commercialization.
- Update `test_research_completeness.py` to the current sensitivity-based CSV contract and prove the old weight-based validator fails.
- Add contract tests that reject `mechanism_weights` in new snapshots and require investment logic, causal lineage, three-statement closure, value creation, reverse-implied expectations, and falsification.
- Add architecture tests proving `lens-*` files are optional calibrations rather than core requirements.
- Add live-release parity tests so generated production assets cannot diverge from Trainer assets.

### 2. Canonical method architecture

- Add `analysis-kernel.md`: decision question, as-of boundary, data normalization, causal graph, model, valuation, red team, monitoring.
- Add `industry-economics-and-cycle.md`: value chain, profit pool, competitive response, supply/demand, price, capacity and inventory states.
- Add `technology-commercialization-and-ip.md`: paper, patent, standard, TRL, MRL, qualification and commercialization permissions.
- Add `valuation-and-market-expectations.md`: ROIC, incremental ROIC, reinvestment, fundamental growth, fade, DCF, residual income, earnings power and reverse DCF.
- Add `multi-skill-system-architecture.md`: future responsibility-based skills and the current single-skill orchestration boundary.
- Add `methodological-foundations.md`: authoritative research and implementation standards, with scope and misuse warnings.
- Rewrite `driver-tree-modeling.md`, `mechanism-router.md`, evidence, moat, integrity, completeness and valuation references around the new kernel.
- Demote existing `lens-*` documents to optional sector calibrations and remove them from required-package routing.

### 3. Artifacts, schemas and validators

- Replace the one-dimensional evidence grade with orthogonal authority, independence, directness, role, as-of and scope fields while retaining legacy read compatibility.
- Add causal-chain, segment-history bridge, industry-profit-pool, operating-cycle, technology-commercialization, value-creation and valuation-reconciliation templates.
- Redesign `forecast_snapshot` around `investment_case`, `driver_tree`, `integrated_model`, `value_creation`, `valuation`, `market_implied_expectations`, and `monitoring`.
- Remove `mechanism_weights` from all new templates and strict requirements; keep a read-only legacy adapter only where historical artifacts need it.
- Change material-assumption completeness from weights summing to one to computed revenue/profit/value sensitivity and explicit support status.
- Add validator gates for segment roll-up, dimensions, causal lineage, first forecast bridge, three statements, cash/PPE/debt/working-capital roll-forwards, ROIC/reinvestment/growth consistency, terminal-value constraints, DCF/RI reconciliation, reverse-implied variables, technology permissions, and red-team attacks.
- Keep old historical training cases readable, but require migration for any newly frozen forecast.

### 4. Trainer and live skill parity

- Rewrite Trainer `SKILL.md` routing and training loop around measured causal/model errors rather than mechanism weights.
- Migrate or retire trainer-only case/mechanism scoring contracts that still force weights.
- Build the production skill through `build_live_release.py`; do not hand-maintain a second method.
- Verify `.claude/skills/technology-company-*` and `.agents/skills/technology-company-*` resolve to the same canonical repository.
- Deprecate the legacy Codex `ai-hardware-forecasting` trigger after the canonical Codex port passes all tests, without deleting user case data.

### 5. Local backend and webapp

- Update the method API map to show the causal-value system rather than a list of mechanism and sector files.
- Replace visible “机制权重” UI with profit-driver chain, thesis carriers, causal evidence, value creation, market-implied expectations, falsification and monitoring.
- Preserve legacy artifact rendering so historical runs remain inspectable.
- Add backend and frontend contract tests for every interactive route and action touched.

### 6. Evaluation and verification

- Run focused RED/GREEN tests during implementation.
- Run the complete nested skill test suite, package self-tests, schema tests, live-release reproducibility test and representative scaffold/validate flows.
- Evaluate the old and new skill on the same prompts; grade causal completeness, evidence permissions, model closure, value-creation logic, falsifiability and actionability.
- Generate the static skill-review viewer and inspect it.
- Run root backend/webapp tests and a local browser interaction pass.

### 7. Git and Site deployment

- Commit and push only the validated nested `forecasting-skills` changes.
- Commit root method/backend/webapp changes without staging unrelated user or runtime files.
- Sync the Codex-only Site branch from the local tested UI, build, test, deploy a new Site version, and verify production pages and bridge freshness.

## Success criteria

- New strict deliveries cannot contain or depend on `mechanism_weights`.
- One canonical Skill produces identical professional behavior for Claude and Codex.
- A forecast can be audited from source vintage to valuation conclusion and back.
- Papers and patents cannot directly authorize revenue; technical, manufacturing, qualification and commercial gates are independently visible.
- Every material thesis has a competitor response, a value impact, and an observable falsification trigger.
- Financial statements close, valuation methods reconcile, and market-implied assumptions are explicit.
- Local UI and hosted Site expose the same functional method and remain clickable.
