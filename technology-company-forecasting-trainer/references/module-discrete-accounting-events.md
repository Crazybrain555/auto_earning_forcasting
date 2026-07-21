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

This expected value is one distribution diagnostic, not automatically a
recurring point forecast. Base treatment follows the event-specific accounting
recognition criteria and proposition-appropriate evidence available at bundle
freeze. Otherwise retain the event as a named scenario or tail.

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

## Event-local distribution construction

When a named event is material, build its possible outcomes from the eligible
amount, event-specific states, timing and accounting recognition rules. Keep
three questions separate:

1. Is the economic event possible, and over what bounded amount?
2. Would the applicable accounting basis recognize it in this period and at
   what amount?
3. When, if ever, would cash move?

Record the observable enabling conditions, rival explanation, probability or
range rationale, and the evidence that would change treatment. Expected value
may summarize a distribution, but it neither defines interval width nor forces
the Base point. A modal Base, an expected-value decision model and a
standard-compliant reported forecast can legitimately differ; reconcile them
instead of applying a universal probability cutoff.

Do not model a purely generic risk with no event family or trigger as if it had
a measurable probability. If the eligible amount is unavailable, mark the
affected conclusion `human-required` or monitoring-only rather than inventing
a bound.

## Failure conditions

- using the DTA state sequence for unrelated events;
- unbounded event magnitude;
- probability without an observable trigger;
- treating a non-cash benefit as FCF;
- capitalizing a discrete gain into normalized valuation;
- global interval widening instead of event-local uncertainty.
