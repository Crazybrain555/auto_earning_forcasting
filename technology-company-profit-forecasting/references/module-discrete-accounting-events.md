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

## Failure conditions

- using the DTA state sequence for unrelated events;
- unbounded event magnitude;
- probability without an observable trigger;
- treating a non-cash benefit as FCF;
- capitalizing a discrete gain into normalized valuation;
- global interval widening instead of event-local uncertainty.
