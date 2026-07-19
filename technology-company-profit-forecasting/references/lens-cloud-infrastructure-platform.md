# Lens: cloud infrastructure platforms

This lens configures the common platform-usage-adoption, contracts, perimeter/accounting, and cycle/regime modules. It is not a separate Skill.

## Required source fields

- segment revenue and segment operating income;
- qualitative or quantitative usage/workload growth;
- list-price reductions, committed-use discounts, and product mix;
- customer cost optimization / rightsizing commentary;
- regions, availability zones, data-center and service expansion;
- segment assets, property/equipment, net additions, depreciation, and leases where disclosed;
- RPO / remaining performance obligations and recognition duration;
- shared-cost allocation policy;
- disclosed useful-life changes for servers, networking, and buildings.

## Standard schedule

1. Usage/workload index.
2. Effective price index.
3. Compute/storage/database/networking/higher-layer mix.
4. Customer and region mix.
5. Customer state: migration, optimization, supply-constrained, regime break, mature.
6. Capacity and utilization bridge.
7. Reported and normalized operating-margin bridge.
8. RPO recognition schedule.
9. Human-required standalone FCF/ROIC allocation bridge.

## AWS validation findings

- Usage growth and price reductions must be separated.
- Cost optimization can slow revenue while underlying workloads continue to grow.
- Server/network useful-life changes can add billions of dollars to reported operating profit without equivalent current cash productivity.
- Segment property/equipment and depreciation support a reinvestment proxy, but not a complete standalone FCF.
- RPO is long-duration and usage-driven.
- AI acceleration is a discrete regime tail at early cutoffs, not a deterministic base.

## Readiness

- Segment revenue and segment operating income: retrospective `research-grade` for AWS-like economics.
- Standalone segment FCF, ROIC, and complete valuation: `screen-grade` and `human-required` until allocation bridges are documented.
