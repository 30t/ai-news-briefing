from __future__ import annotations

import logging
import json
import re
import urllib.parse
import urllib.request
from typing import Any

from utils import USER_AGENT, build_item, normalize_space, parse_datetime, strip_html


def _release_display_title(project_name: str, release: dict[str, Any]) -> str:
    version = release.get("name") or release.get("tag_name") or "new release"
    raw_body = release.get("body") or ""
    body = strip_html(raw_body)
    heading = ""
    for line in raw_body.splitlines():
        text = normalize_space(strip_html(re.sub(r"^#+\s*", "", line)))
        if not text or text.lower() in {"what's changed", "whats changed", "changes"}:
            continue
        heading = text
        break

    if "Claude Desktop" in body and "Claude Code" in body:
        return f"{project_name} {version}：支持 Claude Desktop 与 Claude Code 启动"
    if heading and heading != version:
        return f"{project_name} {version}：{heading[:90]}"
    return f"{project_name} 发布 {version}"


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
                if not html_url:
                    continue
                body = release.get("body") or ""
                items.append(
                    build_item(
                        title=_release_display_title(name, release),
                        url=html_url,
                        source_name=name,
                        source_type="github_release",
                        source_level=level,
                        published_at=parse_datetime(release.get("published_at") or release.get("created_at")),
                        summary_or_excerpt=body,
                        extra={"github_repo": repo, "release_version": release.get("tag_name") or release.get("name")},
                    )
                )
            logging.info("Fetched %s GitHub releases from %s", len(releases), repo)
        except Exception as exc:
            logging.warning("Failed to fetch GitHub releases for %s: %s", repo, exc)
    return items
