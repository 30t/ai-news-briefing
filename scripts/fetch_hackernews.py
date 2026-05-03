from __future__ import annotations

import logging
import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

from utils import USER_AGENT, build_item


HN_BASE = "https://hacker-news.firebaseio.com/v0"


def fetch_hackernews(config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("enabled", True):
        return []

    max_stories = int(config.get("max_stories", 100))
    min_points = int(config.get("min_points", 0))
    level = config.get("level", "tech_community")
    items: list[dict[str, Any]] = []

    try:
        request = urllib.request.Request(f"{HN_BASE}/topstories.json", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=25) as response:
            story_ids = json.loads(response.read().decode("utf-8"))[:max_stories]
    except Exception as exc:
        logging.warning("Failed to fetch Hacker News top stories: %s", exc)
        return items

    for story_id in story_ids:
        try:
            request = urllib.request.Request(f"{HN_BASE}/item/{story_id}.json", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=15) as response:
                story = json.loads(response.read().decode("utf-8")) or {}
            points = int(story.get("score") or 0)
            if story.get("type") != "story" or points < min_points:
                continue
            title = story.get("title")
            url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            if not title:
                continue
            published_at = datetime.fromtimestamp(int(story.get("time") or 0), timezone.utc)
            comments_url = f"https://news.ycombinator.com/item?id={story_id}"
            items.append(
                build_item(
                    title=title,
                    url=url,
                    source_name="Hacker News",
                    source_type="hackernews",
                    source_level=level,
                    published_at=published_at,
                    summary_or_excerpt=f"HN points: {points}. Comments: {comments_url}",
                    extra={"hn_score": points, "hn_comments_url": comments_url},
                )
            )
        except Exception as exc:
            logging.warning("Failed to fetch Hacker News story %s: %s", story_id, exc)
    logging.info("Fetched %s Hacker News stories", len(items))
    return items
