from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "ai-news-briefing-no-api/1.0 (+https://github.com/)"
LOCAL_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Singapore")
CORE_ITEM_FIELDS = {
    "title",
    "url",
    "source_name",
    "source_type",
    "source_level",
    "published_at",
    "summary_or_excerpt",
    "matched_keywords",
    "score",
    "tags",
}


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_yaml(path: Union[str, Path]) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        text = file.read()
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        return data
    except ModuleNotFoundError:
        return json.loads(text)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            try:
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                parsed = datetime.fromisoformat(text)
            except (TypeError, ValueError, OverflowError):
                return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_local_time(value: Optional[str]) -> str:
    parsed = parse_datetime(value)
    if parsed is None:
        return "未知"
    return parsed.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M")


def datetime_to_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return normalize_space(text)


def normalize_space(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def excerpt(value: Optional[str], limit: int = 1200) -> str:
    text = normalize_space(strip_html(value))
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def normalize_url(url: Optional[str]) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or parts.path
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def build_item(
    *,
    title: str,
    url: str,
    source_name: str,
    source_type: str,
    source_level: str,
    published_at: Optional[datetime],
    summary_or_excerpt: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    item = {
        "title": normalize_space(title),
        "url": normalize_url(url),
        "source_name": source_name,
        "source_type": source_type,
        "source_level": source_level,
        "published_at": datetime_to_iso(published_at),
        "summary_or_excerpt": excerpt(summary_or_excerpt),
        "matched_keywords": [],
        "score": 0,
        "tags": [],
    }
    if extra:
        metadata = {key: value for key, value in extra.items() if key not in CORE_ITEM_FIELDS}
        item.update(metadata)
    return item
