from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from utils import normalize_url, parse_datetime


def normalize_title_for_history(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r"https?://\S+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def load_recent_history(path: Path, *, today: date, days: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    entries = data.get("entries", data if isinstance(data, list) else [])
    cutoff = today - timedelta(days=days)
    recent: list[dict[str, Any]] = []
    for entry in entries:
        entry_date = _parse_history_date(entry.get("briefing_date"))
        if entry_date and entry_date >= cutoff:
            recent.append(entry)
    return recent


def filter_history_duplicates(
    items: list[dict[str, Any]],
    history_entries: list[dict[str, Any]],
    *,
    max_items: int,
    title_similarity_threshold: float = 0.9,
) -> tuple[list[dict[str, Any]], int]:
    kept: list[dict[str, Any]] = []
    skipped = 0
    for item in items:
        if _is_history_duplicate(item, history_entries, title_similarity_threshold):
            skipped += 1
            continue
        kept.append(item)
        if len(kept) >= max_items:
            break
    return kept, skipped


def build_history_entries(items: list[dict[str, Any]], *, briefing_date: date) -> list[dict[str, Any]]:
    entries = []
    for item in items:
        entries.append(
            {
                "normalized_url": normalize_url(item.get("url")),
                "normalized_title": normalize_title_for_history(item.get("title", "")),
                "title": item.get("title", ""),
                "source_name": item.get("source_name", ""),
                "source_level": item.get("source_level", ""),
                "published_at": item.get("published_at"),
                "briefing_date": briefing_date.isoformat(),
            }
        )
    return entries


def save_history(path: Path, existing: list[dict[str, Any]], new_entries: list[dict[str, Any]], *, today: date, days: int) -> None:
    cutoff = today - timedelta(days=days)
    merged = existing + new_entries
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in merged:
        entry_date = _parse_history_date(entry.get("briefing_date"))
        if entry_date and entry_date < cutoff:
            continue
        key = (entry.get("normalized_url") or "", entry.get("normalized_title") or "")
        deduped[key] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"entries": list(deduped.values())}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_history_duplicate(item: dict[str, Any], history_entries: list[dict[str, Any]], threshold: float) -> bool:
    current_url = normalize_url(item.get("url"))
    current_title = normalize_title_for_history(item.get("title", ""))
    current_level = item.get("source_level")
    for entry in history_entries:
        previous_url = entry.get("normalized_url") or ""
        previous_title = entry.get("normalized_title") or ""
        previous_level = entry.get("source_level") or ""
        if current_level == "official_confirmed" and previous_level != "official_confirmed":
            continue
        if current_url and current_url == previous_url:
            return True
        if current_title and previous_title and SequenceMatcher(None, current_title, previous_title).ratio() >= threshold:
            return True
    return False


def _parse_history_date(value: Any) -> date | None:
    if not value:
        return None
    parsed = parse_datetime(str(value))
    if parsed:
        return parsed.date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None
