"""Backend-owned UI state: the watchlist. Lives under backend/state/."""
from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path

from .config import CONFIG

STATE_DIR = Path(CONFIG.get("_config_path", ".")).parent / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
WATCHLIST_PATH = STATE_DIR / "watchlist.json"
_LOCK = threading.Lock()


def load_watchlist() -> list[dict]:
    if WATCHLIST_PATH.is_file():
        try:
            items = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return [i for i in items if isinstance(i, dict) and (i.get("security") or i.get("entity"))]
        except Exception:
            pass
    return []


def _save(items: list[dict]) -> None:
    WATCHLIST_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_watch(entity: str, security: str, note: str = "") -> list[dict]:
    entity = entity.strip()
    security = security.strip().upper() or entity.upper()
    if not entity:
        raise ValueError("entity is required")
    with _LOCK:
        items = load_watchlist()
        if any(str(i.get("security", "")).upper() == security for i in items):
            raise ValueError(f"{security} already on the watchlist")
        items.append({
            "entity": entity,
            "security": security,
            "note": note.strip(),
            "added_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        _save(items)
        return items


def remove_watch(security: str) -> list[dict]:
    security = security.strip().upper()
    with _LOCK:
        items = [i for i in load_watchlist() if str(i.get("security", "")).upper() != security]
        _save(items)
        return items


SUGGESTIONS_PATH = STATE_DIR / "watch_suggestions.json"


def load_suggestions() -> dict:
    if SUGGESTIONS_PATH.is_file():
        try:
            data = json.loads(SUGGESTIONS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("suggestions"), list):
                return data
        except Exception:
            pass
    return {"generated_at": None, "hint": "", "suggestions": []}


def clear_suggestions() -> None:
    if SUGGESTIONS_PATH.is_file():
        SUGGESTIONS_PATH.unlink()
