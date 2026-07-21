# Evidence store and system slimming plan

> Date: 2026-07-21
> Scope: backend/ (store owner), forecasting-skills/ (scaffold/ingest touchpoints only), training-runs/ (unchanged shapes)
> Status: engine choice pending user decision (PG vs SQLite); everything else agreed direction per HANDOFF.md 使命裁定

## Objective

Stop re-fetching and re-discovering the same evidence on every run. One protocol, one shared store:
a case run consumes what the store already has, fetches only true gaps, and everything it fetched
lands back in the store for the next run. Measured motivation: fetch/search is 28–52% of each live
run; MRVL's 12 sources included 7–9 immutable SEC filings that were re-fetched from zero; TrendForce
and Micron IR material was independently re-fetched across MU/SNDK cases.

## What already exists (build on, don't replace)

- `forecasting-system-contracts/protocol_manifest.json` already defines the layering (source_asset
  append-only by content hash; evidence_record versioned; evidence_use per-case) and the ports
  (`register_source_asset`, `query_evidence`, `export_case_bundle`, ...). Zero implementations today.
  **The store is the host for these ports, not a new contract.**
- v10 live runs already produce per-case raw custody (`sources/raw/`, 123MB for MRVL) with real
  `sha256:` content hashes and a `source_manifest.json`. Identity keys exist at case level.
- `backend/app/db.py` is the in-repo precedent: backend-owned SQLite (WAL), append-only version rows
  keyed by content hash, soft delete, artifacts on disk + metadata in DB (MLflow-style split).

## Store design

**Owner and boundary (constitution #4).** The backend owns the store. Skills never touch SQL: the
scaffold pre-loads (回灌) matching store content into the case workspace; delivery ingest reads the
finished workspace back into the store. Agents interact with files in their workspace, exactly as today.

**Objects (v1 scope, smallest loop).**
1. `source_asset` — original bytes on disk under `backend/state/evidence/blobs/<sha256>` +
   metadata row: source_uri, content_hash, kind, publisher, published_at, available_at, retrieved_at,
   license note; SEC extras: accession, form, period. Append-only; same hash = same asset.
2. `financial_fact` — rows lifted from delivered `financial_fact_ledger.csv` keyed by
   (accession, taxonomy tag, dimensions, period); restatements insert new rows pointing at predecessors.
3. `data_series_point` — rows from `data_series_register.csv` keyed by (series_id, period, vintage_id).
Deliberately **not** stored shared: `evidence_use` permissions, conflict adjudications, claims —
re-judged per case (constitution #5); opinions/claims stay case-local in v1.

**Mutability classes drive freshness (external precedent: edgartools TTL tiers).**
- `immutable` (filed documents, transcripts): permanent, never re-fetch once stored.
- `revisable` (industry datasets, consensus): reuse allowed, staleness surfaced, new vintage appended.
- `perishable` (quotes, news pages): never reused across runs; always fetched live with retrieved_at.

**Point-in-time correctness (the hard red line).**
- live mode: query newest (`available_at ≤ now`).
- training mode: `available_at ≤ case cutoff` enforced in the query layer, not by agent discipline;
  plus a per-case frozen snapshot binding (set of content hashes actually served), mirroring
  `bound_bundle_hashes` — re-running a sealed case replays the bound set, never "current newest"
  (external precedent: ArcticDB named snapshots).

**Flow changes (two touchpoints only).**
- `scaffold_delivery.py`: after workspace creation, ask the backend for store hits for this
  company/industry (by CIK/tickers + declared research routes) and materialize them into
  `sources/raw/` + a pre-filled `source_manifest.json` section marked `origin: store`.
- delivery ingest (backend, alongside existing `db.scan`): on sealed/delivery-passed cases, register
  new source assets (copy bytes, verify hash), lift facts/series rows. Drafts are never ingested into
  the shared store (only the runs-version table keeps them, and after the 2026-07-21 fix they no
  longer surface as effective valuations).

## Engine decision (open): PostgreSQL vs SQLite+FTS5

User leans PG and authorized installation. Honest comparison for this workload
(single-node runner + local mirror, hundreds of cases, low-thousands of sources, blobs on filesystem):

| | SQLite + FTS5 + JSON1 | PostgreSQL |
|---|---|---|
| Ops | zero services; fits existing `sqlite3 .backup` replica bundle path | new service on runner **and** Mac; pg_dump wired into backup/replica scripts; migrations |
| Full-text search | FTS5 solid for this scale | richer (tsvector, trigram), better if corpus grows large |
| Unstructured/JSON | JSON1 adequate | jsonb + GIN indexes stronger |
| Concurrency | fine (WAL; backend is the single writer) | stronger, unneeded while backend is sole writer |
| Precedent | secfsdstools indexes 500k SEC reports in SQLite; db.py already SQLite | industry default for служб with many writers |
| Constitution #10 | smallest system that closes the loop | justified only if a demonstrated failure needs it |

**Decision (user, 2026-07-21): PostgreSQL now.** SQLite-first was recommended for ops simplicity;
user chose PG for stronger unstructured/jsonb + full-text support up front and authorized installs.
Consequences accepted into scope: PG service on the Mac (brew) and later on the runner (apt, done
during the deployment-alignment window, HANDOFF #6), `pg_dump` wired into the replica/backup path,
and a self-contained test fixture (scratch cluster via initdb/pg_ctl) so backend tests stay
deterministic. The port layer stays storage-neutral regardless.

## Slimming tie-in (fed by the 010e log forensics)

The store removes the "re-discover everything" load, but the biggest single block (model integration
+ validation loops, 1h44m in the killed MRVL run) is a construction problem: a 3,300-line monolithic
generator regenerating every artifact per fix, gates requiring artifacts the engine could not produce
without looping. SOP restructuring (statement-decomposition core per constitution #12, checks reduced
to bottom-line guards per #2) is tracked as HANDOFF #3 and gated on the log-forensics report
(`docs/2026-07-21-mrvl-run-log-forensics.md`) plus the comparative blind test (HANDOFF #7).

## Not in v1

No vector store, no knowledge graph, no event bus, no L1–L6 build-out beyond the three object types
above (the fuller architecture in `docs/plans/2026-07-20-value-investing-forecasting-system.md` and
the user's L1–L6 sketch remain the north star; v1 implements only the reuse loop that pays for itself).
No cross-company "insight" reuse: only sources, facts and series — judgments stay per-case.

## Acceptance

- Re-running a company a day later: immutable sources served from store, zero SEC re-downloads
  (verifiable in source_manifest `origin: store` counts + wall-clock delta).
- A sealed training case cannot receive any store row with `available_at > cutoff` (contract test).
- Replica bundle contains the store DB backup + blobs; local mirror can serve the same hits.
- Backend tests green; no skill reads SQL anywhere (grep gate stays clean).
