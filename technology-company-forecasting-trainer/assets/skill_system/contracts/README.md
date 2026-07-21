# Forecasting system contracts

This is the shared evidence and handoff kernel for the forecasting skills.  It
is deliberately **not a skill**: it stores no investment opinion and owns no
forecasting stage.

The kernel separates durable source/evidence records from case-specific use.
Skills consume only read-only handoffs carrying an
`orchestrator_acceptance_ref` and return candidate records or model artifacts;
an orchestrator validates and persists them through a storage adapter. A
candidate is not a downstream handoff until that acceptance reference exists.
No skill writes SQL, D1 or object storage directly.

`snapshot_at` identifies the exact accepted bundle for audit and versioning.
It never grants source access or changes evidence permissions. Those decisions
belong to the orchestrator and are represented by the accepted bundle, not by
the clock.

Start with `protocol_manifest.json`.  Use
`schemas/capability_handoff.schema.json` at every skill boundary.  The current
file-backed case workspace is the first adapter.  SQLite/D1/R2 adapters may be
added only after legacy mixed records are migrated without upgrading their
trust status.

The capability that first encounters a blocker authors its reason, affected
output and next evidence once and assigns a stable `blocker_id`. Downstream
bundles carry that ID in `input_refs`; they do not copy or subtly rewrite the
blocker. This keeps the machine lineage complete while allowing the human answer
to state the limitation once.
