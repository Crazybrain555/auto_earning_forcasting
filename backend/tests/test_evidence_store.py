from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

from backend.app import evidence

# Without LC_ALL, PostgreSQL 18 on macOS aborts startup ("postmaster became
# multithreaded during startup") because CoreFoundation locale lookup spawns
# threads before the postmaster forks.
_PG_ENV = {**os.environ, "LC_ALL": "C"}


@pytest.fixture(scope="module")
def pg_dsn(tmp_path_factory):
    initdb = shutil.which("initdb")
    pg_ctl = shutil.which("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("postgres binaries not on PATH")
    root = tmp_path_factory.mktemp("pg")
    data = root / "data"
    # The pytest tmp tree exceeds the 103-byte unix-socket path limit on
    # macOS, so the socket lives in a short mkdtemp dir instead.
    import tempfile
    sock = Path(tempfile.mkdtemp(prefix="pgsock"))
    subprocess.run([initdb, "-D", str(data), "-A", "trust", "-U", "postgres",
                    "-E", "UTF8", "--no-locale"],
                   check=True, capture_output=True, env=_PG_ENV)
    subprocess.run(
        [pg_ctl, "-D", str(data), "-w", "-l", str(root / "pg.log"), "-o",
         f"-c listen_addresses= -c unix_socket_directories={sock}", "start"],
        check=True, capture_output=True, env=_PG_ENV)
    try:
        yield f"postgresql://postgres@/postgres?host={sock}"
    finally:
        subprocess.run([pg_ctl, "-D", str(data), "-m", "immediate", "stop"],
                       capture_output=True, env=_PG_ENV)
        shutil.rmtree(sock, ignore_errors=True)


@pytest.fixture()
def store(pg_dsn, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "_DSN", pg_dsn)
    monkeypatch.setattr(evidence, "_BLOBS_DIR", tmp_path / "blobs")
    with psycopg.connect(pg_dsn) as conn:
        conn.execute("DROP SCHEMA IF EXISTS evidence CASCADE")
        conn.commit()
    evidence.init()
    return evidence


def _fake_hash(seed: str) -> str:
    return "sha256:" + hashlib.sha256(seed.encode()).hexdigest()


def test_register_is_idempotent_by_content(store, tmp_path):
    doc = tmp_path / "sec_x_primary.htm"
    doc.write_text("<html>10-K body</html>")
    meta = {"source_uri": "https://www.sec.gov/x", "kind": "sec_filing",
            "tickers": ["mrvl"], "accession": "0001-23-000001",
            "published_at": "2026-01-31T00:00:00Z", "retrieved_at": "2026-07-21T00:00:00Z"}
    first = store.register_source_asset(dict(meta), src_path=doc)
    again = store.register_source_asset(dict(meta), src_path=doc)
    assert first["existed"] is False and again["existed"] is True
    assert first["id"] == again["id"]
    blob = store.blob_abspath(
        store.query_sources(tickers=["MRVL"])[0]["blob_path"])
    assert blob.exists() and blob.read_text() == "<html>10-K body</html>"


def test_training_cutoff_is_enforced_in_sql(store):
    early = {"content_hash": _fake_hash("early"), "source_uri": "u1", "kind": "sec_filing",
             "tickers": ["MU"], "available_at": "2026-06-01T00:00:00Z",
             "retrieved_at": "2026-07-21T00:00:00Z"}
    late = {"content_hash": _fake_hash("late"), "source_uri": "u2", "kind": "sec_filing",
            "tickers": ["MU"], "available_at": "2026-07-15T00:00:00Z",
            "retrieved_at": "2026-07-21T00:00:00Z"}
    store.register_source_asset(early)
    store.register_source_asset(late)
    sealed_view = store.query_sources(tickers=["MU"], as_of="2026-07-01T00:00:00Z")
    assert [r["source_uri"] for r in sealed_view] == ["u1"]
    live_view = store.query_sources(tickers=["MU"])
    assert {r["source_uri"] for r in live_view} == {"u1", "u2"}


def test_perishable_never_served_for_reuse(store):
    quote = {"content_hash": _fake_hash("quote"), "source_uri": "https://finance.yahoo.com/q",
             "kind": "quote", "tickers": ["MU"],
             "available_at": "2026-07-01T00:00:00Z", "retrieved_at": "2026-07-01T00:00:00Z"}
    store.register_source_asset(quote)
    assert store.query_sources(tickers=["MU"]) == []


def test_ingest_workspace_lifts_files_ledgers_and_binds(store, tmp_path):
    ws = tmp_path / "live" / "TEST@2026-07-21"
    raw = ws / "sources" / "raw" / "filings"
    raw.mkdir(parents=True)
    doc = raw / "sec_test_primary.htm"
    doc.write_text("<html>quarterly filing</html>")
    doc_hash = "sha256:" + hashlib.sha256(doc.read_bytes()).hexdigest()
    (ws / "source_manifest.json").write_text(json.dumps({"sources": [
        {"source_id": "S01", "content_hash": doc_hash, "kind": "sec_filing",
         "location": "https://www.sec.gov/Archives/test", "accession": "0001-23-000009",
         "published_at": "2026-05-27T00:00:00Z", "retrieved_at": "2026-07-21T08:00:00Z"},
        {"source_id": "S10", "content_hash": "unhashed:live_market_data",
         "kind": "market_data", "location": "https://finance.yahoo.com/quote/TEST"},
    ]}))
    (ws / "financial_fact_ledger.csv").write_text(
        "accession_or_filing_id,tag,period,unit,reported_value\n"
        "0001-23-000009,Revenues,FY2026Q1,USD,100.5\n"
        "TBD,Revenues,FY2026Q2,USD,\n")
    (ws / "data_series_register.csv").write_text(
        "series_id,period,vintage_id,value,unit\n"
        "nand_asp,2026Q2,v1,1.23,USD/GB\n")

    # Unsealed: raw sources lift, but conclusions (ledgers) must not seed the
    # shared tables.
    draft_counts = store.ingest_workspace(ws)
    assert draft_counts["assets_new"] == 1
    assert draft_counts["facts"] == 0 and draft_counts["series_points"] == 0

    (ws / "forecast_seal.json").write_text("{}")
    counts = store.ingest_workspace(ws)

    assert counts["assets_new"] == 0 and counts["assets_existing"] == 1
    assert counts["facts"] == 1 and counts["series_points"] == 1
    lifted = store.query_sources(tickers=["TEST"])[0]
    assert lifted["accession"] == "0001-23-000009"
    assert lifted["source_uri"] == "https://www.sec.gov/Archives/test"
    again = store.ingest_workspace(ws)
    assert again["assets_new"] == 0 and again["assets_existing"] == 1
    assert again["facts"] == 0 and again["series_points"] == 0
