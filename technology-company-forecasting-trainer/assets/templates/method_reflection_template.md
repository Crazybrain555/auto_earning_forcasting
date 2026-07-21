# Method reflection - round <round-id>

Overview: one section per proposed rule. Internal error attribution tells you
that the method missed; this record forces the outside check before the rule
is written. Sources are distinguished by original origin/method cluster, not
URL count. Category and originality labels are descriptive metadata, never a
machine-granted authority tier. A frozen independent reviewer decides whether
the sources are proposition-appropriate. See references/historical-training-loop.md
step 3b.

## Rule 1: <short name of the rule>

- `error_observed`: <case, horizon, direction, magnitude - the measured miss>
- `internal_attribution`: <taxonomy code + mechanism reasoning from the cases>
- `external_sources`:
  - `source_id`: <stable short id> | `category`: <academic_primary / official_guidance / practitioner_original / analyst_deep_dive / published_model / ...> | `independence_cluster`: <original author, institution, dataset, or method family> | `originality`: <original / primary / official / commentary> | `location`: <https://... / doi:10... / youtube:<video-id> / isbn:<n>> | `method_claim`: <the bounded method proposition this source supports> | `misuse_boundary`: <where the proposition should not be transferred>
  Add another source only when it contributes a distinct method, boundary or independent corroboration.
- `outside_view`: <what practitioners actually do about this failure mode>
- `agreement`: confirms | refines | contradicts
- `rule_adopted`: <the rule, with scope and failure condition>
- `support_status`: <provisional / externally_supported / externally_supported_method / validated_on_holdout / rejected / no_change; explain if useful>
- `validation_plan`: <untouched mechanisms, companies, lifecycle or cycle states; named pass/fail evidence and direct revenue, operating-profit, and GAAP-net-income outcomes>
- `why_not_alternatives`: <remedies considered and rejected, with reasons>
- `challenger_baselines`: <simpler rule or model that the proposal must beat>
- `generative_change`: <the SOP stage, shared primitive or authored-to-generated path corrected before adding a safety-net check>
- `assurance_angle`: <the one primary orthogonal failure angle; name any overlapping check retired or state why none exists>
- `complexity_delta`: <artifacts, authored fields, equations, validator branches and tests added/removed, plus ablation or retirement condition>
- `independent_review_plan`: <isolated reviewer, frozen inputs, decision questions and how unresolved disagreement limits promotion>
- `ablation_plan`: <optional: remove one component at a time when the proposal has multiple moving parts>
- `rollback_condition`: <optional: explicit reversal trigger if it is not already clear in the rule's failure condition>

The source record states the bounded proposition and misuse boundary; it does
not confer truth by prestige or category string. A podcast, analyst deep dive,
transcript, published model, paper, standard or book can contribute within its
actual authority scope. The independent reviewer judges authority, conflict
handling and validation-plan sufficiency. Keep optional fields only when they
improve falsifiability; do not invent ceremonial content.
