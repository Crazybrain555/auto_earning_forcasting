# Module: discrete accounting-event distribution and cash bridge

Use when a bounded, non-recurring accounting event can materially change reported GAAP profit, balance sheet or cash flow. Examples include deferred-tax valuation allowances, impairments, restructuring, acquisition accounting, litigation, useful-life changes and uncertain tax positions.

This is a generic event schema. Do not apply one event family's state machine to every accounting event.

## Event record

For each material event record:

- `event_id` and event family;
- accounting/legal basis and affected entity or jurisdiction;
- maximum eligible amount and source;
- observable enabling conditions and recognition trigger;
- event-specific states and transition evidence;
- probability by period and recognition fraction;
- P&L, tax, balance-sheet and cash-flow lines affected;
- cash/non-cash classification and payment timing;
- reversibility, recurrence and normalized-profit treatment;
- Base/tail permission and falsification trigger.

## Distribution equation

```text
Expected discrete GAAP effect_t
= sum over events [eligible amount_e
  × probability(recognition state_e,t)
  × recognition fraction_e,t
  × sign_e]
```

This expected value is a distribution component, not automatically a recurring point forecast. Include it in Base only when event-family accounting criteria and E0/E1 evidence support probable recognition. Otherwise retain it as a named scenario or tail.

## Cash and valuation integrity

- Non-cash GAAP benefits are reversed in the cash-flow bridge.
- Cash costs follow payment timing rather than P&L recognition timing.
- Discrete gains do not raise normalized earnings, terminal margins or recurring multiples.
- Do not count the same event in operating margin, tax, cash flow and valuation twice.

## Event-family routing

- Deferred-tax assets and valuation allowances: read `submodule-dta-valuation-allowance.md`.
- Impairment: use asset-specific carrying value, impairment trigger, recoverability/fair-value evidence and non-cash treatment.
- Restructuring: separate announced plan, liability recognition, cash payments, savings ramp and recurrence.
- Acquisition accounting: separate purchase-price allocation, inventory step-up, amortization, integration and contingent consideration.
- Litigation: separate legal probability threshold, range of loss, insurance/indemnity and payment timing.

## Distribution-width floor for identified events

When a discrete accounting event is identified as a named possibility at `as_of` with a quantifiable eligible amount, the forecast distribution must reflect the event's expected value even when the event is excluded from the Base point estimate. Omitting an identified event from both the point estimate and the distribution width systematically under-forecasts profit variance and produces intervals that cannot cover the actual.

**Applicability.** All three conditions must hold:

1. The event is named and its family identified (DTA release, impairment, restructuring, litigation, etc.) — not a generic "accounting risk" placeholder.
2. The eligible amount is quantifiable from E0/E1 sources at `as_of` (e.g., gross DTA on the balance sheet, asset carrying value, announced restructuring charge range, disclosed litigation exposure).
3. At least one enabling condition for recognition is observable at `as_of` (e.g., cumulative profitability trend for DTA release, declining asset returns for impairment, announced plan for restructuring).

**Rule.** When the event is not included in the Base point estimate:

- The Bull case (or upside tail for beneficial events) or Bear case (for adverse events) must include the probability-weighted expected value of the event: `eligible_amount × probability × recognition_fraction`.
- The minimum distribution width attributable to the event equals the expected value. This is additive to operating uncertainty — do not offset it by narrowing operating intervals.
- Record the event in the assumption register with its eligible amount, estimated probability, and the specific enabling conditions observed at `as_of`. State why it is excluded from Base (e.g., "probable" threshold not met under ASC 740) and what evidence would move it into Base.

When the event has probability above 50% based on observable enabling conditions at `as_of` and the accounting standard's recognition criteria are substantially met, include its expected value in the Base point estimate, not only in the distribution tail.

**Failure conditions — do not apply when:**

- the event is purely speculative with no observable enabling conditions;
- the eligible amount cannot be bounded from disclosed data;
- the event family has no defined recognition trigger (use monitoring-only treatment).

## Failure conditions

- using the DTA state sequence for unrelated events;
- unbounded event magnitude;
- probability without an observable trigger;
- treating a non-cash benefit as FCF;
- capitalizing a discrete gain into normalized valuation;
- global interval widening instead of event-local uncertainty.
