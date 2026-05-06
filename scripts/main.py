from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fetch_article_text import enrich_items_with_article_text
from fetch_github_releases import fetch_github_releases
from fetch_hackernews import fetch_hackernews
from fetch_rss import fetch_rss_sources
from generate_markdown import generate_markdown
from generate_model_daily import generate_model_daily, select_items_for_model_daily
from score_items import dedupe_items, filter_by_lookback, rank_items, score_items
from summarize_with_llm import enhance_items_with_llm, get_api_key
from utils import ROOT, load_yaml, setup_logging


def main() -> None:
    setup_logging()
    sources_config = load_yaml(ROOT / "config" / "sources.yml")
    keywords_config = load_yaml(ROOT / "config" / "keywords.yml")
    scoring_config = load_yaml(ROOT / "config" / "scoring.yml")
    llm_config = _load_optional_config(ROOT / "config" / "llm.yml")

    items = []
    items.extend(fetch_rss_sources(sources_config.get("rss_sources", [])))
    items.extend(fetch_github_releases(sources_config.get("github_releases", [])))
    items.extend(fetch_hackernews(sources_config.get("hackernews", {})))
    total_count = len(items)

    lookback_hours = int(scoring_config.get("lookback_hours", 24))
    max_items = int(scoring_config.get("max_items_per_day", 20))
    recent_items = filter_by_lookback(items, lookback_hours)
    scored_items = score_items(recent_items, keywords_config, scoring_config)
    deduped_items = dedupe_items(scored_items, scoring_config)
    ranked_items = rank_items(deduped_items, max_items)

    markdown = generate_markdown(ranked_items, total_count, max_items)
    output_dir = Path(ROOT / "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    dated_output_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    latest_output_path = output_dir / "daily.md"
    model_output_path = output_dir / "model-daily.md"
    dated_output_path.write_text(markdown, encoding="utf-8")
    latest_output_path.write_text(markdown, encoding="utf-8")

    model_markdown = _try_generate_model_daily(ranked_items, total_count, scoring_config, llm_config)
    if model_markdown:
        model_output_path.write_text(model_markdown, encoding="utf-8")
        logging.info("Generated %s with model summary layer", model_output_path)

    logging.info(
        "Generated %s and %s with %s ranked items from %s fetched items",
        dated_output_path,
        latest_output_path,
        len(ranked_items),
        total_count,
    )


def _load_optional_config(path: Path) -> dict:
    if not path.exists():
        return {"enabled": False}
    return load_yaml(path)


def _try_generate_model_daily(
    ranked_items: list[dict],
    total_count: int,
    scoring_config: dict,
    llm_config: dict,
) -> str | None:
    if not llm_config.get("enabled", False):
        logging.info("Model daily skipped: LLM disabled.")
        return None
    if not get_api_key(llm_config):
        logging.warning("Model daily skipped: missing LLM API key secret.")
        return None

    model_candidates = select_items_for_model_daily(ranked_items, scoring_config, llm_config)
    model_candidates = enrich_items_with_article_text(model_candidates, llm_config)
    model_candidates = enhance_items_with_llm(model_candidates, llm_config)
    return generate_model_daily(model_candidates, total_count, scoring_config, llm_config)


if __name__ == "__main__":
    main()
