"""Shared evidence store (PostgreSQL) - the reuse layer behind the ports in
forecasting-system-contracts/protocol_manifest.json.

Split follows db.py's MLflow convention: metadata, facts and search text live
in PostgreSQL; original bytes stay on disk under a content-addressed blobs
tree, the DB stores the relative path + sha256. Only the backend touches SQL -
skills keep consuming workspace files (scaffold pre-loads store hits, delivery
ingest lifts the finished workspace back in).

Reuse semantics by mutability class:
  immutable  - filed documents, transcripts, papers: reusable forever.
  revisable  - datasets, industry research, web material: reusable, new
               vintages append, staleness is the consumer's judgment.
  perishable - quotes/market data: never served from the store; always
               re-fetched live. Rows may exist for lineage but reuse queries
               exclude them unconditionally.

Point-in-time red line: a training-mode query passes as_of and the SQL filter
(available_at <= as_of) enforces the cutoff - agent discipline is not the
mechanism. Live mode reads newest. Case bindings record exactly which content
hashes a case consumed so sealed cases replay their bound set.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path

from .config import CONFIG

_DSN = (
    os.environ.get("FORECAST_EVIDENCE_DSN")
    or (CONFIG.get("evidence") or {}).get("dsn")
    or "postgresql:///forecast_evidence"
)
_BLOBS_DIR = Path(os.path.abspath(os.path.expanduser(
    os.environ.get("FORECAST_EVIDENCE_BLOBS")
    or (CONFIG.get("evidence") or {}).get("blobs_dir")
    or str(Path(CONFIG.get("_config_path", ".")).parent / "state" / "evidence" / "blobs")
)))

_SCHEMA = """
CREATE SCHEMA IF NOT EXISTS evidence;

CREATE TABLE IF NOT EXISTS evidence.source_asset (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  content_hash  TEXT NOT NULL UNIQUE,
  source_uri    TEXT NOT NULL,
  kind          TEXT NOT NULL,
  mutability    TEXT NOT NULL CHECK (mutability IN ('immutable','revisable','perishable')),
  publisher     TEXT,
  title         TEXT,
  tickers       TEXT[] NOT NULL DEFAULT '{}',
  accession     TEXT,
  form          TEXT,
  period        TEXT,
  published_at  TIMESTAMPTZ,
  available_at  TIMESTAMPTZ NOT NULL,
  retrieved_at  TIMESTAMPTZ NOT NULL,
  blob_path     TEXT,
  byte_size     BIGINT,
  text_excerpt  TEXT,
  meta          JSONB NOT NULL DEFAULT '{}'::jsonb,
  registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  search_tsv    tsvector GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(text_excerpt,''))
  ) STORED
);
CREATE INDEX IF NOT EXISTS source_asset_tickers_gin ON evidence.source_asset USING GIN (tickers);
CREATE INDEX IF NOT EXISTS source_asset_search_gin  ON evidence.source_asset USING GIN (search_tsv);
CREATE INDEX IF NOT EXISTS source_asset_available   ON evidence.source_asset (available_at);
CREATE INDEX IF NOT EXISTS source_asset_accession   ON evidence.source_asset (accession);

CREATE TABLE IF NOT EXISTS evidence.financial_fact (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  accession     TEXT NOT NULL,
  taxonomy_tag  TEXT NOT NULL,
  dimensions    JSONB NOT NULL DEFAULT '{}'::jsonb,
  dimensions_key TEXT NOT NULL,
  period        TEXT NOT NULL,
  unit          TEXT,
  reported_value    NUMERIC,
  normalized_value  NUMERIC,
  filed_at      TIMESTAMPTZ,
  source_hash   TEXT,
  predecessor_id BIGINT REFERENCES evidence.financial_fact(id),
  meta          JSONB NOT NULL DEFAULT '{}'::jsonb,
  registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (accession, taxonomy_tag, dimensions_key, period)
);

CREATE TABLE IF NOT EXISTS evidence.data_series_point (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  series_id     TEXT NOT NULL,
  period        TEXT NOT NULL,
  vintage_id    TEXT NOT NULL DEFAULT '',
  value         TEXT,
  unit          TEXT,
  available_at  TIMESTAMPTZ,
  source_hash   TEXT,
  meta          JSONB NOT NULL DEFAULT '{}'::jsonb,
  registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (series_id, period, vintage_id)
);

CREATE TABLE IF NOT EXISTS evidence.case_binding (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  case_key      TEXT NOT NULL,
  content_hash  TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'delivered_source',
  bound_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (case_key, content_hash)
);
"""

_IMMUTABLE_KINDS = {"sec_filing", "issuer_document", "transcript", "paper", "patent"}
_PERISHABLE_KINDS = {"market_data", "quote"}


def _connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(_DSN, row_factory=dict_row)


def init(conn=None) -> None:
    own = conn is None
    if own:
        conn = _connect()
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        if own:
            conn.close()


def classify_mutability(kind: str) -> str:
    if kind in _IMMUTABLE_KINDS:
        return "immutable"
    if kind in _PERISHABLE_KINDS:
        return "perishable"
    return "revisable"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _blob_dest(content_hash: str, suffix: str) -> Path:
    hexpart = content_hash.split(":", 1)[1]
    return _BLOBS_DIR / hexpart[:2] / (hexpart + suffix)


def register_source_asset(meta: dict, src_path: Path | None = None, conn=None) -> dict:
    """Idempotent append by content hash. Returns {id, content_hash, existed}."""
    content_hash = meta.get("content_hash")
    blob_path = None
    byte_size = None
    if src_path is not None:
        src_path = Path(src_path)
        content_hash = _sha256_file(src_path)
        dest = _blob_dest(content_hash, src_path.suffix.lower())
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest)
        blob_path = str(dest.relative_to(_BLOBS_DIR))
        byte_size = src_path.stat().st_size
    if not content_hash or not str(content_hash).startswith("sha256:"):
        raise ValueError("register_source_asset needs real bytes or a sha256: content_hash")
    kind = meta.get("kind") or "web_page"
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    own = conn is None
    if own:
        conn = _connect()
    try:
        row = conn.execute(
            """INSERT INTO evidence.source_asset
               (content_hash, source_uri, kind, mutability, publisher, title, tickers,
                accession, form, period, published_at, available_at, retrieved_at,
                blob_path, byte_size, text_excerpt, meta)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (content_hash) DO NOTHING
               RETURNING id""",
            (content_hash, meta.get("source_uri") or "", kind,
             meta.get("mutability") or classify_mutability(kind),
             meta.get("publisher"), meta.get("title"),
             [t.upper() for t in (meta.get("tickers") or [])],
             meta.get("accession"), meta.get("form"), meta.get("period"),
             meta.get("published_at"),
             meta.get("available_at") or meta.get("published_at") or meta.get("retrieved_at") or now,
             meta.get("retrieved_at") or now,
             blob_path, byte_size, (meta.get("text_excerpt") or "")[:20000] or None,
             json.dumps(meta.get("meta") or {}, ensure_ascii=False))).fetchone()
        conn.commit()
        if row is not None:
            return {"id": row["id"], "content_hash": content_hash, "existed": False}
        existing = conn.execute(
            "SELECT id FROM evidence.source_asset WHERE content_hash = %s", (content_hash,)).fetchone()
        return {"id": existing["id"], "content_hash": content_hash, "existed": True}
    finally:
        if own:
            conn.close()


def query_sources(tickers: list[str] | None = None, kinds: list[str] | None = None,
                  as_of: str | None = None, text: str | None = None,
                  limit: int = 50, conn=None) -> list[dict]:
    """Reuse query. Perishable rows are never returned - quotes are always
    fetched live. as_of (training mode) is enforced here, in SQL, not by the
    consumer's discipline."""
    clauses = ["mutability <> 'perishable'"]
    params: list = []
    if tickers:
        clauses.append("tickers && %s")
        params.append([t.upper() for t in tickers])
    if kinds:
        clauses.append("kind = ANY(%s)")
        params.append(list(kinds))
    if as_of:
        clauses.append("available_at <= %s")
        params.append(as_of)
    if text:
        clauses.append("search_tsv @@ plainto_tsquery('english', %s)")
        params.append(text)
    params.append(limit)
    own = conn is None
    if own:
        conn = _connect()
    try:
        rows = conn.execute(
            f"""SELECT id, content_hash, source_uri, kind, mutability, publisher, title,
                       tickers, accession, form, period, published_at, available_at,
                       retrieved_at, blob_path, byte_size
                FROM evidence.source_asset
                WHERE {' AND '.join(clauses)}
                ORDER BY available_at DESC, id DESC LIMIT %s""",
            params).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            conn.close()


def blob_abspath(blob_path: str) -> Path:
    return _BLOBS_DIR / blob_path


def bind_case(case_key: str, content_hashes: list[str], role: str = "delivered_source",
              conn=None) -> int:
    own = conn is None
    if own:
        conn = _connect()
    try:
        n = 0
        for h in content_hashes:
            cur = conn.execute(
                """INSERT INTO evidence.case_binding (case_key, content_hash, role)
                   VALUES (%s,%s,%s) ON CONFLICT (case_key, content_hash) DO NOTHING""",
                (case_key, h, role))
            n += cur.rowcount
        conn.commit()
        return n
    finally:
        if own:
            conn.close()


def _kind_for_raw(relpath: Path) -> str:
    top = relpath.parts[0] if relpath.parts else ""
    name = relpath.name.lower()
    if top == "filings" or "sec_" in name:
        return "sec_filing" if name.startswith("sec_") else "issuer_document"
    if top in ("transcripts", "calls"):
        return "transcript"
    if top in ("papers", "patents"):
        return "paper"
    return "report"


def ingest_workspace(workspace: Path, conn=None) -> dict:
    """Lift a case workspace into the store: every file under sources/raw/**
    becomes a source_asset (manifest entries enrich by matching content_hash),
    ledger CSVs become fact/series rows, and the case gets a binding for
    replay. Perishable sources (quotes) are recorded in the manifest only and
    are deliberately not lifted.

    Ledgers are lifted only from sealed workspaces: raw originals are safe to
    reuse from any run (hash-verified bytes), but fact/series rows are that
    run's conclusions and an unfinished run must not seed the shared tables."""
    workspace = Path(workspace)
    sealed = (workspace / "forecast_seal.json").exists()
    case_key = f"{workspace.parent.name}/{workspace.name}"
    manifest = {}
    mpath = workspace / "source_manifest.json"
    if mpath.exists():
        try:
            data = json.loads(mpath.read_text())
            entries = data if isinstance(data, list) else data.get("sources") or []
            manifest = {e.get("content_hash"): e for e in entries if isinstance(e, dict)}
        except Exception:
            manifest = {}
    own = conn is None
    if own:
        conn = _connect()
    counts = {"assets_new": 0, "assets_existing": 0, "facts": 0, "series_points": 0, "bound": 0}
    hashes: list[str] = []
    try:
        raw_root = workspace / "sources" / "raw"
        if raw_root.is_dir():
            for path in sorted(p for p in raw_root.rglob("*") if p.is_file()):
                rel = path.relative_to(raw_root)
                content_hash = _sha256_file(path)
                entry = manifest.get(content_hash) or {}
                kind = entry.get("kind") or _kind_for_raw(rel)
                meta = {
                    "content_hash": content_hash,
                    "source_uri": entry.get("location") or f"workspace://{case_key}/sources/raw/{rel}",
                    "kind": kind,
                    "publisher": entry.get("publisher"),
                    "title": entry.get("title") or rel.name,
                    "tickers": _case_tickers(workspace),
                    "accession": entry.get("accession"),
                    "form": entry.get("form"),
                    "period": entry.get("period_scope") or entry.get("period"),
                    "published_at": entry.get("published_at"),
                    "available_at": entry.get("available_at") or entry.get("published_at")
                                    or entry.get("retrieved_at"),
                    "retrieved_at": entry.get("retrieved_at"),
                    "meta": {"case": case_key, "raw_path": str(rel),
                             "source_id": entry.get("source_id")},
                }
                res = register_source_asset(meta, src_path=path, conn=conn)
                hashes.append(res["content_hash"])
                counts["assets_existing" if res["existed"] else "assets_new"] += 1
        if sealed:
            counts["facts"] = _ingest_fact_ledger(workspace / "financial_fact_ledger.csv", conn)
            counts["series_points"] = _ingest_series_register(workspace / "data_series_register.csv", conn)
        if hashes:
            counts["bound"] = bind_case(case_key, hashes, conn=conn)
        return counts
    finally:
        if own:
            conn.close()


def _case_tickers(workspace: Path) -> list[str]:
    sec = workspace.name.split("@", 1)[0]
    return [sec.upper()] if sec and len(sec) <= 6 else []


def _placeholder(v: str | None) -> bool:
    return not v or str(v).strip().upper() in ("TBD", "PENDING", "NA", "N/A", "")


def _ingest_fact_ledger(path: Path, conn) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            accession = row.get("accession_or_filing_id") or row.get("accession")
            tag = row.get("tag") or row.get("taxonomy_tag")
            period = row.get("period") or row.get("period_scope")
            if _placeholder(accession) or _placeholder(tag) or _placeholder(period):
                continue
            dims = row.get("dimensions") or ""
            cur = conn.execute(
                """INSERT INTO evidence.financial_fact
                   (accession, taxonomy_tag, dimensions, dimensions_key, period, unit,
                    reported_value, normalized_value, filed_at, source_hash, meta)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (accession, taxonomy_tag, dimensions_key, period) DO NOTHING""",
                (accession, tag, json.dumps({"raw": dims}), hashlib.sha256(dims.encode()).hexdigest()[:16],
                 period, row.get("unit"), _num(row.get("reported_value")),
                 _num(row.get("normalized_value")), row.get("filed_at") or None,
                 row.get("source_id") or None, json.dumps(row, ensure_ascii=False)))
            n += cur.rowcount
    conn.commit()
    return n


def _ingest_series_register(path: Path, conn) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            series_id = row.get("series_id")
            period = row.get("period") or row.get("period_scope")
            if _placeholder(series_id) or _placeholder(period):
                continue
            cur = conn.execute(
                """INSERT INTO evidence.data_series_point
                   (series_id, period, vintage_id, value, unit, available_at, source_hash, meta)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (series_id, period, vintage_id) DO NOTHING""",
                (series_id, period, row.get("vintage_id") or "",
                 row.get("value") or row.get("reported_value"), row.get("unit"),
                 row.get("available_at") or None, row.get("source_id") or None,
                 json.dumps(row, ensure_ascii=False)))
            n += cur.rowcount
    conn.commit()
    return n


def _num(v):
    try:
        return float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError:
        return None


def stats(conn=None) -> dict:
    own = conn is None
    if own:
        conn = _connect()
    try:
        out = {}
        for name, table in (("source_assets", "evidence.source_asset"),
                            ("financial_facts", "evidence.financial_fact"),
                            ("data_series_points", "evidence.data_series_point"),
                            ("case_bindings", "evidence.case_binding")):
            out[name] = conn.execute(f"SELECT count(*) AS c FROM {table}").fetchone()["c"]
        return out
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Evidence store operations")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("workspaces", nargs="+")
    sub.add_parser("stats")
    args = ap.parse_args()
    if args.cmd == "init":
        init()
        print("schema ready:", _DSN)
    elif args.cmd == "stats":
        print(json.dumps(stats(), indent=2))
    else:
        init()
        for ws in args.workspaces:
            print(ws, json.dumps(ingest_workspace(Path(ws))))
