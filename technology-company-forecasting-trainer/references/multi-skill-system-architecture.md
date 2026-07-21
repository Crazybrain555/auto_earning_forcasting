# Multi-Skill System Architecture

The system has five invokable skills and one non-skill contract kernel.  This
is the minimum split that gives each specialist an independent handoff and
training failure without creating parallel methods.

## Skills

| Owner | Responsibility | Input → output |
|---|---|---|
| `technology-company-profit-forecasting` | live decision, orchestration, joint scenarios, independent red team, readiness and immutable publication | user request + specialist bundles → snapshot |
| `company-evidence-research` | point-in-time source custody, observations, financial facts, claims, conflicts and permissions | decision/request → evidence bundle |
| `company-operating-modeling` | industry boundary, causal graph, cycle, commercialization and operating equations | decision + evidence → operating-model bundle |
| `company-financial-forecasting` | comparable history, integrated statements, attributable profit, earnings power and valuation | evidence + operating model → financial-forecast bundle |
| `technology-company-forecasting-trainer` | seal, post-seal Actuals, error attribution, method reflection, cross-company validation and atomic release | frozen cases + Actuals → evaluation/change/release |

The same three specialists serve current forecasts and historical cases without
Trainer-specific copies.  In a current forecast they receive ordinary accepted
bundles.  In a historical case the Trainer constructs a **projection view**:
the decision contract, eligible source/evidence content, accounting basis,
horizons and normal handoff metadata needed for the specialist output.  The
view omits cutoff controls, seal receipts, post-seal Actuals, outcome evaluation,
error attribution and candidate/challenger judgments.  Specialists neither
query the training vault nor implement their own time sandbox; they return the
same storage-neutral bundles under the same professional contract.

The Trainer alone owns the historical cutoff, projection-view construction,
seal, Actuals retrieval and validation, realized-outcome evaluation, error
attribution, independent promotion evidence and release decision.  It locates
the earliest failing handoff and normally revises one primary owner; a
shared-contract change requires a demonstrated cross-capability failure.

`assets/method_system.json` remains the only stage registry.
`assets/skill_system/manifest.json` maps those stage IDs to owners but does not
declare a second order.  Sector lenses, mechanism modules, validators and
reviewer roles are not skills.

## Shared evidence kernel

`forecasting-system-contracts` is generated from
`assets/skill_system/contracts/`.  It is deliberately not invokable and not a
database implementation.  It defines six records with independent lifecycles:

- `source_asset`: original identity, bytes/location, publisher, dates and hash;
- `evidence_record`: numeric observation, financial fact, source claim or
  derived claim with raw/normalized values and direct inputs;
- `evidence_use`: case/as-of/proposition permission, conflict and review;
- `action_log`: producer, versions, direct inputs/outputs and execution state;
- `evidence_request`: a forecast gap with budget, stop condition and status;
- `forecast_snapshot`: append-only published output and bound bundle hashes.

Direct references are recorded once; recursive lineage is reconstructed only
for audit.  A source is stored once, but its use is reconsidered for each case.
New evidence never changes a published forecast without a new reasoning action
and snapshot.

Skills consume and emit storage-neutral bundles.  They never call SQL, D1 or
R2 directly.  The file workspace remains the first adapter; later SQLite and
D1/R2 adapters must implement the same ports.  Do not migrate old `unhashed:`
records as trusted evidence merely because they enter a database.

## What stays out

Do not add industry skills, a full-text knowledge graph, a vector store as
truth, a global confidence score, an event bus or automatic forecast mutation
without a demonstrated forecasting failure and an independent lifecycle.  A
new top-level object or skill must improve a material revenue, operating-profit
or attributable-net-income inference, distinguish a rival, or prevent a proven
data/accounting error.

## Release

Specialist and contract sources live inside the trainer tree, so promotion
evidence binds them.  `scripts/build_skill_system.py` deterministically creates
the live coordinator, three specialists and shared contracts.  Generated
directories are never hand-edited and are committed atomically with the
trainer after the full structural suite and independent review pass.
