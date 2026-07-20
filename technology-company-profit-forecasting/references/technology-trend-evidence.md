# Technology-trend evidence (papers, standards, patents)

Filings are backward-looking. Sell-side research lags. For a technology
company, the 2-5 year question - *which technology transition lands, when,
and who is positioned for it* - is answered in the technical literature
**before** it appears in revenue. A forecast that skips this layer is a
financial-mechanics exercise with a blind spot where the thesis lives.

This is where an AI analyst should exceed a human sell-side model, which
typically has no technology-literature layer at all.

## What counts as technology-trend evidence

| Lane | Examples | Typical lead time |
|---|---|---|
| Peer-reviewed / preprint | arXiv, IEEE Xplore, Nature Electronics | 1-4 years |
| Conference disclosure | ISSCC, IEDM, VLSI, Hot Chips, OFC, ECTC, SC | 0.5-3 years |
| Standards bodies | JEDEC (HBM/DDR), OIF, IEEE 802.3, PCI-SIG, CXL | 1-3 years |
| Patents | USPTO/EPO grants and applications by the company and its rivals | 2-5 years |
| Technical roadmaps | IRDS, SEMI, foundry PDK notes, OEM design guides | 1-5 years |

All are family `technical-paper-standard` in the signal taxonomy, except
vendor technical announcements which stay `official-product`.

## The three questions this layer must answer

1. **Which transition is assumed?** Name it concretely: HBM4 stacking,
   1.6T optics / 200G-per-lane SerDes, GAA transistors, glass core substrate,
   400-layer NAND, CXL memory pooling, liquid cooling at >100kW racks.
2. **Is it feasible, and when?** Cite the physical/engineering evidence:
   demonstrated parameters, yield/power/thermal limits, standard ratification
   dates, qualification cycles. State the timing distribution, not a point.
3. **What would falsify it?** The technical failure boundary: a parameter
   that must be achieved, a standard that must ratify, a qualification that
   must pass. This becomes a `failure_boundary` SignalCard and feeds the
   scenario tail.

## Permission rules (unchanged and enforced)

- Technical evidence **cannot** set a Base point value. Physics does not
  price a quarter. Allowed uses: `timing_signal`, `feasibility_bound`,
  `scenario_probability`, `failure_boundary`, `monitor_trigger`.
- What it *can* do: bound a driver parameter (e.g. "200G/lane demonstrated at
  X pJ/bit implies 1.6T optics cannot ramp before 20XX"), set transition
  timing distributions, and justify scenario weights.
- Every technical signal must name the **driver parameter it touches** in
  `model_driver`. A paper that does not attach to a number in the driver tree
  is decoration - reject it from the pack.

## Transmission into the driver tree

```
Paper/standard evidence  →  driver parameter  →  driver-tree leaf  →  revenue
  "HBM4 JEDEC ratified,      "HBM ASP uplift      "HBM segment:        segment
   1.4x bandwidth,            +25-40% vs HBM3E,    volume x ASP"        revenue
   qualification 2H26"        ramp from 2H26"
```

Record the transmission explicitly. If the chain cannot be written, the
technical claim is not usable in the model.

## Competitive-position reading

Papers and patents also answer *who wins*: read the author affiliations and
assignees. Sustained first-author presence at ISSCC/IEDM/OFC on the relevant
node, or a dense patent family around the enabling process step, is direct
evidence of technical position - and it is observable years before market
share moves. Where a company's rivals dominate the literature on the assumed
transition, that is a Base-case risk, not a footnote.

## Depth expectations

- Horizon FY+2 and beyond: at least **2** technical-lane signals, each with a
  named driver parameter and a stated falsification condition.
- A thesis whose main line IS a technology inflection (capacity_ramp or
  program_conversion basis): at least **3**, including one that examines the
  competitive literature position.
- If the technology lane genuinely does not apply (mature commodity, no
  pending transition), state that explicitly in the report with the reason -
  an empty lane must be an argued choice, never an omission.
