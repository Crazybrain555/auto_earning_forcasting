---
name: company-evidence-research
description: Build and audit dated, versioned evidence bundles for public-company forecasts: original source custody, financial facts, numeric observations, bounded claims, normalization, conflicts, independence, research gaps, and permitted uses. Use whenever a forecast needs filings, management statements, expert or analyst views, datasets, papers, patents, web research, or reusable evidence extraction. Do not build operating equations or a final financial forecast.
---

# Company Evidence Research

Produce a reusable, dated evidence bundle that another capability can
reason from.  The objective is not more sources; it is fewer unsupported or
misdefined inputs to future revenue, operating profit and attributable net
income.

## System contract

Read `../forecasting-system-contracts/protocol_manifest.json` and
`../forecasting-system-contracts/schemas/capability_handoff.schema.json`.
Apply the kernel's `proposition_fidelity`, `conditional_analysis_routing` and
`minimum_sufficient_presentation` invariants before any source-specific
template. They are semantic permissions, not completeness scores.

Accept only a `decision_bundle` and, when present, an
`evidence_request_bundle` carrying an `orchestrator_acceptance_ref`. The
orchestrator resolves source eligibility and use permissions before handoff;
the bundle's `snapshot_at` is audit identity, not permission. Follow only the
method, reference, source-adapter and validator routes named in the accepted
bundle. Return one candidate `evidence_bundle` to the orchestrator for
validation and acceptance. Never open a parallel input channel or publish a
forecast snapshot.

## Work from forecast uncertainty

1. Translate the decision, main hypothesis, rival and uncertain driver nodes
   into bounded evidence requests with stop conditions.  Broad browsing without
   a forecast question is discovery, not completed research.
2. Obtain source assets only through an evidence request and source adapter
   authorized by the accepted bundle. Register the original source asset once.
   Preserve original bytes or a
   stable locator, publisher/origin, publication and actual availability times,
   content hash and raw location.  Repackaged copies share one origin.
3. Extract only high-value observations, financial facts and bounded claims.
   Each keeps an original anchor, definition, unit, period, scope, vintage and
   revision identity.  Treat the source proposition as a closed tuple: a
   normalized claim may restate only direction, magnitude, period, scope and
   causal relation actually entailed by the anchored text or value.  Leave an
   omitted dimension unknown.  Empty extraction is valid when a source adds no
   useful evidence.
4. Preserve raw and minimally normalized values side by side.  Deterministic
   unit, period or taxonomy transforms may change representation; they cannot
   add content, turn ambiguity into a sign, invent a comparison basis or
   overwrite raw.  A useful label or expected schema field never authorizes
   completing a source's missing proposition.
5. Keep source identity separate from case use.  Record whether a proposition
   may inform history, a causal input, a rival, context only, or nothing.  The
   same document may have different permissions in another case or bundle
   snapshot.
6. Reconcile official disclosures and accounting identities first.  Management
   statements are primary evidence of what management stated and often the
   best source for company-specific operating facts; they are not automatic
   proof of future outcomes.  Preserve fraud, incentive, definition and scope
   exceptions as explicit conflicts.
7. Treat expert, analyst, blog, podcast and caption evidence as interpretation
   unless it binds an independently measured observation.  Corroboration needs
   a different root and, for numeric claims, a compatible construct and method.
8. A stated conflict proves only that a conflict was reported.  Record each
   side's direction, magnitude, period and scope only when its own source anchor
   supplies them; do not manufacture symmetric bullish/bearish positions, a
   midpoint, probability or scenario.  Scenario authorship belongs downstream.
9. Return unresolved conflicts and missing measurements as blockers or new
   evidence requests.  Missing is never zero and narrative similarity is never
   a numeric bridge.

## Capability routes

When the accepted bundle routes this capability into a compatible coordinator
installation, use only the minimum needed subset of:

- `references/core-source-and-evidence.md`
- `references/data-quality-and-triangulation.md`
- `references/research-lanes-and-corroboration.md`
- `references/forward-evidence-and-signal-validation.md`
- `references/technology-trend-evidence.md` when technical material matters
- `scripts/validate_research_completeness.py`
- `scripts/validate_data_series.py`
- `scripts/validate_technical_evidence.py` when routed

The file workspace is currently the storage adapter.  Do not write SQL, D1 or
object storage directly.  Return candidate records and direct references; the
orchestrator validates and persists them.

## Boundary

Do not choose the final causal graph, forecast a margin, value the equity or
silently update a published forecast.  When downstream reasoning exposes a
data gap, accept a new evidence request and version the bundle rather than
editing the previous one in place.  Persist the complete machine handoff, but
keep the human response to the source propositions, permissions and gaps that
answer the request.  Author each blocker at its earliest failing handoff and
reference that blocker downstream instead of repeating it in every table and
conclusion.
