from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any

from utils import USER_AGENT, normalize_space


class ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._capture_tag: str | None = None
        self._current: list[str] = []
        self.blocks: list[str] = []
        self.meta_description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}:
            self._skip_depth += 1
            return
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            name = attrs_dict.get("name", "").lower() or attrs_dict.get("property", "").lower()
            if name in {"description", "og:description", "twitter:description"} and not self.meta_description:
                self.meta_description = normalize_space(attrs_dict.get("content", ""))
        if self._skip_depth:
            return
        if tag in {"p", "li", "h1", "h2", "h3"}:
            self._flush()
            self._capture_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == self._capture_tag:
            self._flush()
            self._capture_tag = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not self._capture_tag:
            return
        self._current.append(data)

    def _flush(self) -> None:
        text = normalize_space(" ".join(self._current))
        self._current = []
        if _is_useful_block(text):
            self.blocks.append(text)


def enrich_items_with_article_text(items: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("fetch_article_text", True):
        return items
    max_items = int(config.get("max_items_for_llm", 20))
    timeout = int(config.get("article_fetch_timeout_seconds", 12))
    limit = int(config.get("article_text_limit", 5000))
    enriched: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if index >= max_items:
            enriched.append(item)
            continue
        enriched.append(_enrich_one(item, timeout, limit))
    return enriched


def _enrich_one(item: dict[str, Any], timeout: int, limit: int) -> dict[str, Any]:
    url = item.get("url") or ""
    if not _should_fetch(url, item):
        return item
    try:
        article_text = fetch_article_text(url, timeout=timeout, limit=limit)
    except Exception as exc:  # noqa: BLE001 - article fetch should never block the briefing.
        logging.warning("Failed to fetch article text for %s: %s", item.get("title", "untitled"), exc)
        return item
    if not article_text:
        return item
    updated = dict(item)
    updated["article_text"] = article_text
    updated["article_text_source"] = "original_url"
    return updated


def fetch_article_text(url: str, *, timeout: int, limit: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured news source URL.
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return ""
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    encoding = response.headers.get_content_charset() or "utf-8"
    html = raw.decode(encoding, errors="replace")
    parser = ArticleTextParser()
    parser.feed(html)
    candidates = _dedupe_blocks(([parser.meta_description] if parser.meta_description else []) + parser.blocks)
    text = normalize_space("\n".join(candidates))
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _should_fetch(url: str, item: dict[str, Any]) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    if item.get("source_type") == "github_release":
        return False
    if re.search(r"\.(pdf|zip|tar|gz|png|jpg|jpeg|gif|webp)(\?|$)", url, flags=re.IGNORECASE):
        return False
    return True


def _is_useful_block(text: str) -> bool:
    if len(text) < 35:
        return False
    lower = text.lower()
    noisy_prefixes = (
        "cookie",
        "sign up",
        "subscribe",
        "advertisement",
        "comments",
        "submitted by",
        "all rights reserved",
    )
    if lower.startswith(noisy_prefixes):
        return False
    if len(re.findall(r"https?://", text)) >= 2:
        return False
    return True


def _dedupe_blocks(blocks: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for block in blocks:
        key = normalize_space(block).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(block)
    return deduped
