from __future__ import annotations

import logging
import urllib.request
from datetime import datetime
from typing import Any, Optional
from xml.etree import ElementTree

from utils import USER_AGENT, build_item, parse_datetime, strip_html


def _text(element: ElementTree.Element, names: tuple[str, ...]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return found.text.strip()
    for child in element:
        local_name = child.tag.split("}", 1)[-1]
        if local_name in names and child.text:
            return child.text.strip()
    return ""


def _link(element: ElementTree.Element) -> str:
    for child in element:
        local_name = child.tag.split("}", 1)[-1]
        if local_name == "link":
            href = child.attrib.get("href")
            if href:
                return href
            if child.text:
                return child.text.strip()
    return ""


def _entry_datetime(entry: ElementTree.Element) -> Optional[datetime]:
    for key in ("published", "updated", "pubDate", "created"):
        value = _text(entry, (key,))
        parsed = parse_datetime(value)
        if parsed is not None:
            return parsed
    return None


def _entries(root: ElementTree.Element) -> list[ElementTree.Element]:
    result = []
    for element in root.iter():
        local_name = element.tag.split("}", 1)[-1]
        if local_name in {"item", "entry"}:
            result.append(element)
    return result


def fetch_rss_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in sources:
        name = source.get("name", "Unknown RSS")
        url = source.get("url")
        level = source.get("level", "needs_verification")
        if not url:
            logging.warning("Skipping RSS source without url: %s", name)
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=25) as response:
                root = ElementTree.fromstring(response.read())
            entries = _entries(root)
            for entry in entries:
                link = _link(entry) or _text(entry, ("id", "guid"))
                title = _text(entry, ("title",))
                if not link or not title:
                    continue
                summary = _text(entry, ("summary", "description", "subtitle", "content"))
                items.append(
                    build_item(
                        title=strip_html(title),
                        url=link,
                        source_name=name,
                        source_type="rss",
                        source_level=level,
                        published_at=_entry_datetime(entry),
                        summary_or_excerpt=summary,
                    )
                )
            logging.info("Fetched %s RSS items from %s", len(entries), name)
        except Exception as exc:
            logging.warning("Failed to fetch RSS source %s: %s", name, exc)
    return items
