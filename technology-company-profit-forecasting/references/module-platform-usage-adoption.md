# Module: platform usage, adoption, pricing, infrastructure, and accounting

**Validation status:** retrospectively validated and `research-grade` for AWS-like segment revenue and segment operating income. Standalone segment FCF, ROIC, and full valuation remain `screen-grade` and `human-required` unless working capital, leases, cash taxes, shared assets, cash, and capital structure are explicitly bridged.

## Core revenue equation

```text
Revenue
= Workloads / consumed usage
× Effective price per workload unit
× Product / service mix
× Customer / region mix
× Recognition factor
```

Do not let usage growth equal revenue growth. Effective price includes list-price reductions, committed-use discounts, migrations to cheaper architectures, customer rightsizing, and higher-layer service mix.

## Required state variables

- migration / expansion;
- customer cost optimization and rightsizing;
- supply or infrastructure constraint;
- AI or other platform regime break;
- mature-scale normalization.

Use probability mixtures when more than one state is visible.

## Infrastructure and operating-profit bridge

```text
Capacity need = Workloads × Resource intensity ÷ Utilization efficiency

Reported operating profit
= Revenue
- allocated infrastructure depreciation and leases
- energy and network
- support and service delivery
- product development and sales
- shared-cost allocation
```

For asset-heavy platforms, show both:

1. reported operating margin; and
2. normalized operating margin after removing disclosed useful-life accounting benefits or charges and applying an explicit economic depreciation range.

Use segment assets, property/equipment, net additions, leases, and depreciation as a **reinvestment proxy**. Do not call a proxy standalone segment capex or FCF.

## RPO and committed contracts

RPO is a visibility schedule, not annual revenue, fixed effective price, or margin protection. Model:

```text
Recognized contract revenue
= committed amount
× actual consumed usage
× recognition timing
× execution / cancellation factor
```

Keep committed-use discounts in the effective-price bridge.

## Regime-tail rule

Upgrade AI or another platform regime tail only after at least two independent E0/E1 signals, such as material workload revenue, customer deployment/capex acceleration, constrained infrastructure commitments, or management disclosure of multi-product demand. A thematic TAM alone stays E3.

## Human-required items

For segments without standalone balance sheets or cash flows, document and obtain human approval for:

- accounts receivable, prepaid assets, contract liabilities, payables, and accrued-cost allocation;
- server, networking, data-center building, shared infrastructure, and finance-lease allocation;
- cash taxes, debt, cash, and cost of capital;
- economic useful lives for servers, networking, and buildings;
- usage and effective-price proxies by compute, storage, database, networking, and higher-layer services.

Until these bridges are complete, cap standalone FCF/ROIC/valuation at `screen-grade`.

## Failure modes

- usage growth directly equals revenue growth;
- RPO directly equals next-year revenue;
- group capex mechanically assigned to the segment;
- reported margin extrapolated without useful-life normalization;
- cost optimization interpreted as workload destruction;
- AI regime-break actuals backfilled into an earlier base case;
- standalone FCF claimed without working-capital, lease, tax, and capital-structure bridges.
