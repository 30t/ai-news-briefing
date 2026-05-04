from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fetch_github_releases import fetch_github_releases
from fetch_hackernews import fetch_hackernews
from fetch_article_text import enrich_items_with_article_text
from fetch_rss import fetch_rss_sources
from generate_intelligence_center import generate_intelligence_center, require_llm_api_key
from history import build_history_entries, filter_history_duplicates, load_recent_history, save_history
from score_items import dedupe_items, filter_by_lookback, rank_items, score_items
from summarize_with_llm import enhance_items_with_llm
from utils import ROOT, load_yaml, setup_logging


def main() -> None:
    setup_logging()
    sources_config = load_yaml(ROOT / "config" / "sources.yml")
    keywords_config = load_yaml(ROOT / "config" / "keywords.yml")
    scoring_config = load_yaml(ROOT / "config" / "scoring.yml")
    llm_config = load_yaml(ROOT / "config" / "llm.yml")
    api_key = require_llm_api_key(llm_config)

    items = []
    items.extend(fetch_rss_sources(sources_config.get("rss_sources", [])))
    items.extend(fetch_github_releases(sources_config.get("github_releases", [])))
    items.extend(fetch_hackernews(sources_config.get("hackernews", {})))
    total_count = len(items)

    lookback_hours = int(scoring_config.get("lookback_hours", 24))
    max_items = int(scoring_config.get("max_items_per_day", 20))
    candidate_pool_size = int(llm_config.get("candidate_pool_size", max_items * 3))
    history_dedupe_days = int(llm_config.get("history_dedupe_days", 7))
    recent_items = filter_by_lookback(items, lookback_hours)
    scored_items = score_items(recent_items, keywords_config, scoring_config)
    deduped_items = dedupe_items(scored_items, scoring_config)
    candidate_items = rank_items(deduped_items, candidate_pool_size)

    today = datetime.now().date()
    output_dir = Path(ROOT / "output")
    history_path = output_dir / "history.json"
    recent_history = load_recent_history(history_path, today=today, days=history_dedupe_days)
    history_filtered_items, skipped_history_count = filter_history_duplicates(
        candidate_items,
        recent_history,
        max_items=candidate_pool_size,
        title_similarity_threshold=float(scoring_config.get("title_similarity_threshold", 0.86)),
    )
    ranked_items = history_filtered_items[:max_items]
    ranked_items = enrich_items_with_article_text(ranked_items, llm_config)
    ranked_items = enhance_items_with_llm(ranked_items, llm_config)

    markdown = generate_intelligence_center(
        ranked_items,
        total_count=total_count,
        candidate_count=len(history_filtered_items),
        final_count=len(ranked_items),
        skipped_history_count=skipped_history_count,
        briefing_date=today,
        config=llm_config,
        api_key=api_key,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    dated_output_path = output_dir / f"{today.isoformat()}.md"
    latest_output_path = output_dir / "daily.md"
    dated_output_path.write_text(markdown, encoding="utf-8")
    latest_output_path.write_text(markdown, encoding="utf-8")
    save_history(
        history_path,
        recent_history,
        build_history_entries(ranked_items, briefing_date=today),
        today=today,
        days=history_dedupe_days,
    )
    logging.info(
        "Generated %s and %s with %s ranked items from %s fetched items; skipped %s recent duplicates",
        dated_output_path,
        latest_output_path,
        len(ranked_items),
        total_count,
        skipped_history_count,
    )


if __name__ == "__main__":
    main()
