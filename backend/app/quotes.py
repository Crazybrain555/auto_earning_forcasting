"""Best-effort live quotes (Yahoo chart API, stdlib only, optional proxy).

Quotes are convenience data for the dashboard's collapsed rows; every failure
degrades gracefully to the snapshot's recorded research-time price. Configure
in config.json: {"quotes": {"enabled": true, "proxy": "http://127.0.0.1:10808",
"ttl_seconds": 300}} — proxy is optional but usually required on networks
where Yahoo is unreachable directly.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request

from .config import CONFIG

QCFG = CONFIG.get("quotes", {}) or {}
TTL = int(QCFG.get("ttl_seconds", 300))
_CACHE: dict[str, tuple[float, dict]] = {}
_LOCK = threading.Lock()

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d"
HEADERS = {"User-Agent": "Mozilla/5.0 (forecast-dashboard)"}


def _opener() -> urllib.request.OpenerDirector:
    proxy = QCFG.get("proxy")
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def _fetch(symbol: str) -> dict:
    request = urllib.request.Request(URL.format(sym=urllib.request.quote(symbol)), headers=HEADERS)
    with _opener().open(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    meta = payload["chart"]["result"][0]["meta"]
    return {
        "symbol": symbol,
        "price": meta.get("regularMarketPrice"),
        "currency": meta.get("currency"),
        "market_time": meta.get("regularMarketTime"),
        "previous_close": meta.get("chartPreviousClose"),
        "source": "yahoo",
    }


def get_quotes(symbols: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not QCFG.get("enabled", False):
        return {s: {"symbol": s, "error": "quotes disabled"} for s in symbols}
    now = time.time()
    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        with _LOCK:
            cached = _CACHE.get(symbol)
        if cached and now - cached[0] < TTL:
            result[symbol] = cached[1]
            continue
        try:
            quote = _fetch(symbol)
        except Exception as exc:
            quote = {"symbol": symbol, "error": str(exc)[:200]}
        with _LOCK:
            # cache errors briefly too, so a dead network doesn't stall every poll
            _CACHE[symbol] = (now if "error" not in quote else now - TTL + 60, quote)
        result[symbol] = quote
    return result


SEARCH_URL = ("https://query1.finance.yahoo.com/v1/finance/search"
              "?q={q}&quotesCount=8&newsCount=0&listsCount=0")
_SEARCH_CACHE: dict[str, tuple[float, list]] = {}
_SEARCH_TTL = 3600


def search_symbols(query: str) -> list[dict]:
    """Company-name -> ticker autocomplete via Yahoo search. Empty list on any failure."""
    query = (query or "").strip()
    if not query or not QCFG.get("enabled", False):
        return []
    key = query.lower()
    now = time.time()
    with _LOCK:
        cached = _SEARCH_CACHE.get(key)
        if cached and now - cached[0] < _SEARCH_TTL:
            return cached[1]
    items: list[dict] = []
    try:
        request = urllib.request.Request(SEARCH_URL.format(q=urllib.request.quote(query)), headers=HEADERS)
        with _opener().open(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for entry in payload.get("quotes", []):
            if entry.get("quoteType") != "EQUITY" or not entry.get("symbol"):
                continue
            items.append({
                "symbol": entry["symbol"],
                "name": entry.get("longname") or entry.get("shortname") or entry["symbol"],
                "exchange": entry.get("exchDisp") or entry.get("exchange") or "",
            })
    except Exception:
        return []
    with _LOCK:
        _SEARCH_CACHE[key] = (now, items)
    return items
