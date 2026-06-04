from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from utils import LOCAL_TIMEZONE, normalize_url


BACKLOG_FILENAME = "backlog.json"
DEFAULT_MAX_AGE_DAYS = 3
DEFAULT_MIN_SCORE = 35
DEFAULT_MAX_ITEMS = 80
DEFAULT_MAX_EARLY_SIGNAL_ITEMS = 20
DEFAULT_MAX_SOURCE_ITEMS = 15


def load_backlog(output_dir: Path) -> list[dict[str, Any]]:
    path = output_dir / BACKLOG_FILENAME
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - backlog should never break daily generation.
        logging.warning("Failed to read backlog %s: %s", path, exc)
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def save_backlog(output_dir: Path, items: list[dict[str, Any]]) -> None:
    path = output_dir / BACKLOG_FILENAME
    output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_backlog_with_today(
    today_items: list[dict[str, Any]],
    backlog_items: list[dict[str, Any]],
    *,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> list[dict[str, Any]]:
    fresh_backlog = _fresh_backlog_items(backlog_items, max_age_days=max_age_days)
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in today_items:
        key = _item_key(item)
        if not key or key in seen:
            continue
        cloned = dict(item)
        cloned["backlog_status"] = "today"
        merged.append(cloned)
        seen.add(key)

    for item in fresh_backlog:
        key = _item_key(item)
        if not key or key in seen:
            continue
        cloned = dict(item)
        cloned["backlog_status"] = "carried_over"
        cloned["score"] = int(cloned.get("score", 0)) + int(cloned.get("backlog_boost", 4))
        merged.append(cloned)
        seen.add(key)

    return sorted(merged, key=lambda entry: int(entry.get("score", 0)), reverse=True)


def update_backlog_after_model_selection(
    *,
    output_dir: Path,
    previous_backlog: list[dict[str, Any]],
    ranked_items: list[dict[str, Any]],
    selected_model_items: list[dict[str, Any]],
    min_score: int = DEFAULT_MIN_SCORE,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_early_signal_items: int = DEFAULT_MAX_EARLY_SIGNAL_ITEMS,
    max_source_items: int = DEFAULT_MAX_SOURCE_ITEMS,
) -> list[dict[str, Any]]:
    selected_keys = {_item_key(item) for item in selected_model_items if _item_key(item)}
    now = datetime.now(LOCAL_TIMEZONE)

    candidates: dict[str, dict[str, Any]] = {}
    for item in _fresh_backlog_items(previous_backlog, max_age_days=max_age_days):
        key = _item_key(item)
        if not key or key in selected_keys:
            continue
        candidates[key] = _normalize_backlog_item(item, now=now, source="backlog")

    for item in ranked_items:
        key = _item_key(item)
        if not key or key in selected_keys:
            continue
        if int(item.get("score", 0)) < min_score:
            continue
        candidates[key] = _normalize_backlog_item(item, now=now, source="today")

    sorted_candidates = sorted(
        candidates.values(),
        key=lambda entry: (int(entry.get("score", 0)), str(entry.get("first_seen_at", ""))),
        reverse=True,
    )
    new_backlog = _limit_backlog_concentration(
        sorted_candidates,
        max_items=max_items,
        max_early_signal_items=max_early_signal_items,
        max_source_items=max_source_items,
    )
    save_backlog(output_dir, new_backlog)
    return new_backlog


def _limit_backlog_concentration(
    items: list[dict[str, Any]],
    *,
    max_items: int,
    max_early_signal_items: int,
    max_source_items: int,
) -> list[dict[str, Any]]:
    limited: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    early_signal_count = 0

    for item in items:
        if len(limited) >= max_items:
            break
        source_level = str(item.get("source_level") or "")
        source_name = str(item.get("source_name") or "")
        if source_level == "early_signal" and early_signal_count >= max_early_signal_items:
            continue
        if source_name and source_counts.get(source_name, 0) >= max_source_items:
            continue

        limited.append(item)
        if source_level == "early_signal":
            early_signal_count += 1
        if source_name:
            source_counts[source_name] = source_counts.get(source_name, 0) + 1
    return limited


def _fresh_backlog_items(items: list[dict[str, Any]], *, max_age_days: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(LOCAL_TIMEZONE) - timedelta(days=max_age_days)
    fresh: list[dict[str, Any]] = []
    for item in items:
        first_seen = _parse_local_datetime(str(item.get("first_seen_at") or ""))
        if first_seen is None or first_seen >= cutoff:
            fresh.append(item)
    return fresh


def _normalize_backlog_item(item: dict[str, Any], *, now: datetime, source: str) -> dict[str, Any]:
    keep_keys = [
        "title",
        "url",
        "source_name",
        "source_type",
        "source_level",
        "published_at",
        "summary_or_excerpt",
        "matched_keywords",
        "tags",
        "score",
        "hn_score",
        "release_version",
    ]
    normalized = {key: item.get(key) for key in keep_keys if key in item}
    normalized["url"] = normalize_url(normalized.get("url"))
    normalized["score"] = int(normalized.get("score", 0))
    normalized["first_seen_at"] = item.get("first_seen_at") or now.isoformat()
    normalized["last_seen_at"] = now.isoformat()
    normalized["backlog_source"] = source
    normalized["backlog_boost"] = int(item.get("backlog_boost", 4))
    return normalized


def _item_key(item: dict[str, Any]) -> str:
    url = normalize_url(item.get("url"))
    if url:
        return url
    title = str(item.get("title") or "").strip().lower()
    source = str(item.get("source_name") or "").strip().lower()
    return f"{source}:{title}" if title else ""


def _parse_local_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=LOCAL_TIMEZONE)
    return parsed.astimezone(LOCAL_TIMEZONE)
