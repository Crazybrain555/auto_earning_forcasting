# Business quality and moat (the persistence question)

The driver tree says *what the numbers do*. This file says *why they should
keep doing it*. Every multi-year forecast contains an implicit claim that
today's economics persist; that claim is the least examined and most
expensive part of most models.

Sources studied: Michael Mauboussin's *Measuring the Moat* framework, the
Business Breakdowns ASML and Moody's episodes, and Li Lu's value-investing
lecture. Calibration notes at the end of this file.

## 1. The value-creation test comes before the growth story

**ROIC − WACC is the non-negotiable test.** A company can report record
profits and still destroy capital. Every delivery states, for the historical
period and the forecast horizon:

- ROIC (NOPAT ÷ invested capital), computed and shown, not asserted;
- the WACC or a stated hurdle rate, with its inputs;
- the **spread**, historically and forecast.

If the forecast implies an expanding spread, that expansion is a claim
requiring the same evidence discipline as a revenue driver. Growth on a
negative spread destroys value faster - say so plainly when it happens.

## 2. Fade is the default; persistence is the claim

High returns attract capital. Empirically, high-ROIC cohorts are dragged
toward the mean - economic gravity. Therefore:

- The Base case must state **an explicit fade assumption**: over the forecast
  horizon, does the spread hold, decay, or expand, and *why*.
- "It compounds because it has compounded" is not a reason. The reason must
  be a barrier that blocks the specific competitive response.
- Conversely, do not mechanically fade a company whose barrier is documented
  and strengthening (round-1 training found systematic under-forecasting of
  durable compounders - the discipline runs both ways: **argue the fade
  either way, never inherit it**).

## 3. Two-level analysis: industry first, then company

**Level 1 - profit pool.** Map the value chain and locate where economic
profit actually sits. Compute the value-creation spread for each link.
A structurally poor link cannot be rescued by good management; a structurally
rich link forgives a lot. Ask explicitly: *is this company positioned in the
profitable part of its chain, and is that position moving?*

For technology chains this is decisive - e.g. in lithography the equipment
vendor captures ~20-25% of wafer-fab equipment spend and a durable share of
the fab's economics, while several adjacent links earn their cost of capital
at best.

**Level 2 - barriers to entry.** Of Porter's five forces, the one that
matters most for a multi-year holder is the threat of new entry, because
barriers are what protect the incumbent's profit. State the barrier
concretely and test it against the actual competitive response:

| Barrier type | Evidence that it is real |
|---|---|
| Technology / know-how lead | rivals' demonstrated parameters lag by N years (see `technology-trend-evidence.md`) |
| Scale / cost position | unit cost gap computed, not assumed |
| Switching costs | customer requalification cost/time, contract structure, historical churn |
| Network / ecosystem | attach and retention data, third-party investment in the ecosystem |
| Regulatory / standards position | seat at the standards body, certification held |
| Customer co-investment | joint development programs, customer capital in the vendor's roadmap |

## 4. The value stick: how the moat converts to money

Profit is price minus cost, but a moat is about widening the **total value
created**: raising customers' willingness to pay, or lowering what suppliers
and employees will accept. Two clean strategies:

- **Differentiation** - better product, brand, network effects → price premium.
- **Cost leadership** - scale, process, unique assets → margin at market price.

State which one the company runs, and check the driver tree reflects it: a
differentiation claim should show up as ASP/mix, a cost-leadership claim as
unit cost. A moat claim that touches no line in the model is decoration.

**Pricing restraint is evidence, not weakness.** A dominant supplier that
does not extract maximum price (ASML's collaborative pricing across two
decades of dominance) is buying customer co-investment and roadmap lock-in -
that is moat maintenance, and it shows up as durability rather than as
near-term margin.

## 5. Quality of the earnings stream

Beyond level and durability of returns, characterise the stream:

- **Recurring share** - installed-base service, subscriptions, consumables:
  revenue that arrives without a new sale each period.
- **Customer concentration and their switching cost** - concentration is a
  risk only where the customer can actually leave.
- **Capital intensity and reinvestment runway** - can the company redeploy
  capital at similar returns, or does high ROIC come with nowhere to spend?
- **Cyclicality vs secular** - separate the two explicitly; a cycle peak
  mistaken for a new plateau is the classic technology-forecast error.

## 6. What this requires in the delivery

`company_quality_moat_register.csv` (already scaffolded) must carry, per
claim: the barrier type, the concrete evidence, the competitive response it
must survive, the model line it touches, and its falsification condition -
the observation that would prove the moat is eroding. A moat claim with no
falsification condition is a belief, not an analysis.

## Calibration notes

- **Mauboussin, *Measuring the Moat***: ROIC vs WACC as the value test;
  economic gravity and return fade; profit-pool mapping of the value chain;
  barriers to entry as the decisive force; the value stick (WTP up or
  supplier cost down) and the differentiation / cost-leadership split.
- **Business Breakdowns - ASML**: a technology barrier expressed as
  generational lead; share of WFE spend as the chain-position metric; margin
  expansion from leadership (mid-40s → ~50% GM over a decade); deliberate
  pricing restraint as moat maintenance.
- **Business Breakdowns - Moody's**: duopoly with regulatory and network
  position; pricing power tied to issuance necessity rather than to service
  cost; recurring surveillance revenue as stream quality.
- **Li Lu**: ownership mindset over paper-shuffling; a large margin of safety
  precisely *because* the analyst does not control the business; circle of
  competence - a career yields few genuine insights, and betting outside them
  is the unforgivable error; work the thesis to completion before sizing, and
  when the work disproves the thesis, take the loss and move on.
