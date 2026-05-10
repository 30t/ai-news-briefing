from __future__ import annotations

import logging
import re
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Any

from utils import normalize_url, parse_datetime, utc_now


LEVEL_PRIORITY = {
    "official_confirmed": 4,
    "tech_community": 3,
    "early_signal": 2,
    "needs_verification": 1,
}


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = re.escape(keyword.lower())
    if re.search(r"[a-z0-9]", keyword.lower()):
        return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text) is not None
    return keyword.lower() in text


def _item_text(item: dict[str, Any], *, include_source_type: bool = False) -> str:
    parts = [
        item.get("title", ""),
        item.get("summary_or_excerpt", ""),
        item.get("source_name", ""),
    ]
    if include_source_type:
        parts.append(item.get("source_type", ""))
    return " ".join(str(part) for part in parts).lower()


def _match_keywords(item: dict[str, Any], keywords_config: dict[str, Any]) -> tuple[list[str], list[str]]:
    text = _item_text(item)
    matched: list[str] = []
    tags: list[str] = []
    for category in keywords_config.get("categories", {}).values():
        tag = category.get("tag")
        category_matched = False
        for keyword in category.get("keywords", []):
            if _contains_keyword(text, str(keyword)):
                matched.append(str(keyword))
                category_matched = True
        if category_matched and tag:
            tags.append(str(tag))
    return sorted(set(matched), key=str.lower), sorted(set(tags))


def _keyword_relevance(item: dict[str, Any], scoring_config: dict[str, Any]) -> int:
    """Estimate recall relevance only. This is not treated as editorial value."""
    text = _item_text(item, include_source_type=True)
    score = 0
    for rule in scoring_config.get("keyword_scores", {}).values():
        rule_score = int(rule.get("score", 0))
        for keyword in rule.get("keywords", []):
            if _contains_keyword(text, str(keyword)):
                score = max(score, rule_score)
                break
    return score


def _penalty(item: dict[str, Any], scoring_config: dict[str, Any]) -> int:
    text = f"{item.get('title', '')} {item.get('summary_or_excerpt', '')}".lower()
    penalty = 0
    for keyword, value in scoring_config.get("penalties", {}).items():
        if keyword == "duplicate url":
            continue
        if _contains_keyword(text, str(keyword)):
            penalty += int(value)
    return penalty


def score_items(
    items: list[dict[str, Any]],
    keywords_config: dict[str, Any],
    scoring_config: dict[str, Any],
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for item in items:
        matched, tags = _match_keywords(item, keywords_config)
        source_trust = int(scoring_config.get("source_level_scores", {}).get(item.get("source_level"), 0))
        keyword_relevance = _keyword_relevance(item, scoring_config)
        penalty = _penalty(item, scoring_config)
        item["matched_keywords"] = matched
        item["tags"] = tags
        item["source_trust_score"] = source_trust
        item["keyword_relevance_score"] = keyword_relevance
        item["rule_penalty"] = penalty
        item["rule_relevance_score"] = source_trust + keyword_relevance + penalty
        item["score"] = item["rule_relevance_score"]
        scored.append(item)
    return scored


def filter_by_lookback(items: list[dict[str, Any]], lookback_hours: int) -> list[dict[str, Any]]:
    cutoff = utc_now() - timedelta(hours=lookback_hours)
    kept: list[dict[str, Any]] = []
    for item in items:
        published_at = parse_datetime(item.get("published_at"))
        if published_at is None or published_at >= cutoff:
            kept.append(item)
    return kept


def _title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower().strip(), right.lower().strip()).ratio()


def _item_score(item: dict[str, Any]) -> int:
    return int(item.get("editorial_score", item.get("score", 0)))


def _is_better(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_level = LEVEL_PRIORITY.get(candidate.get("source_level"), 0)
    current_level = LEVEL_PRIORITY.get(current.get("source_level"), 0)
    if candidate_level != current_level:
        return candidate_level > current_level
    if _item_score(candidate) != _item_score(current):
        return _item_score(candidate) > _item_score(current)
    candidate_time = parse_datetime(candidate.get("published_at"))
    current_time = parse_datetime(current.get("published_at"))
    if candidate_time and current_time:
        return candidate_time > current_time
    return False


def dedupe_items(items: list[dict[str, Any]], scoring_config: dict[str, Any]) -> list[dict[str, Any]]:
    duplicate_penalty = int(scoring_config.get("penalties", {}).get("duplicate url", -30))
    by_url: dict[str, dict[str, Any]] = {}
    for item in items:
        url = normalize_url(item.get("url"))
        item["url"] = url
        if not url:
            continue
        existing = by_url.get(url)
        if existing is None:
            by_url[url] = item
            continue
        lower_score_item = existing if _is_better(item, existing) else item
        lower_score_item["score"] = int(lower_score_item.get("score", 0)) + duplicate_penalty
        if "editorial_score" in lower_score_item:
            lower_score_item["editorial_score"] = int(lower_score_item.get("editorial_score", 0)) + duplicate_penalty
        if _is_better(item, existing):
            by_url[url] = item

    threshold = float(scoring_config.get("title_similarity_threshold", 0.86))
    deduped: list[dict[str, Any]] = []
    for item in sorted(by_url.values(), key=_item_score, reverse=True):
        duplicate_index = None
        for index, kept in enumerate(deduped):
            if _title_similarity(item.get("title", ""), kept.get("title", "")) >= threshold:
                duplicate_index = index
                break
        if duplicate_index is None:
            deduped.append(item)
            continue
        kept = deduped[duplicate_index]
        if _is_better(item, kept):
            deduped[duplicate_index] = item
            logging.info("Replaced similar title with higher priority source: %s", item.get("title"))
    return deduped


def rank_items(items: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            _item_score(item),
            LEVEL_PRIORITY.get(item.get("source_level"), 0),
            parse_datetime(item.get("published_at")) or utc_now(),
        ),
        reverse=True,
    )[:max_items]
