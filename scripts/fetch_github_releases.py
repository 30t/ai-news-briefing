from __future__ import annotations

import logging
import json
import urllib.parse
import urllib.request
from typing import Any

from utils import USER_AGENT, build_item, parse_datetime


def fetch_github_releases(repos: list[dict[str, Any]], per_repo: int = 5) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for source in repos:
        repo = source.get("repo")
        name = source.get("name") or repo or "GitHub Release"
        level = source.get("level", "official_confirmed")
        if not repo:
            logging.warning("Skipping GitHub release source without repo: %s", name)
            continue
        query = urllib.parse.urlencode({"per_page": per_repo})
        url = f"https://api.github.com/repos/{repo}/releases?{query}"
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(request, timeout=25) as response:
                releases = json.loads(response.read().decode("utf-8"))
            for release in releases:
                html_url = release.get("html_url")
                title = release.get("name") or release.get("tag_name")
                if not html_url or not title:
                    continue
                body = release.get("body") or ""
                items.append(
                    build_item(
                        title=f"{name}: {title}",
                        url=html_url,
                        source_name=name,
                        source_type="github_release",
                        source_level=level,
                        published_at=parse_datetime(release.get("published_at") or release.get("created_at")),
                        summary_or_excerpt=body,
                        extra={"github_repo": repo},
                    )
                )
            logging.info("Fetched %s GitHub releases from %s", len(releases), repo)
        except Exception as exc:
            logging.warning("Failed to fetch GitHub releases for %s: %s", repo, exc)
    return items
