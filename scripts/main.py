from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from backlog import load_backlog, merge_backlog_with_today, update_backlog_after_model_selection
from fetch_article_text import enrich_items_with_article_text
from fetch_github_releases import fetch_github_releases
from fetch_hackernews import fetch_hackernews
from fetch_rss import fetch_rss_sources
from generate_markdown import generate_markdown
from generate_model_daily import generate_model_daily, select_items_for_model_daily
from judge_candidates_with_llm import judge_candidates_with_llm, require_llm_api_key
from score_items import dedupe_items, filter_by_lookback, rank_items, score_items
from utils import LOCAL_TIMEZONE, ROOT, load_yaml, setup_logging


def main() -> None:
    setup_logging()
    sources_config = load_yaml(ROOT / "config" / "sources.yml")
    keywords_config = load_yaml(ROOT / "config" / "keywords.yml")
    scoring_config = load_yaml(ROOT / "config" / "scoring.yml")
    llm_config = _load_required_config(ROOT / "config" / "llm.yml")
    editorial_policy = _load_required_config(ROOT / "config" / "editorial_policy.yml")
    require_llm_api_key(llm_config)

    items = []
    items.extend(fetch_rss_sources(sources_config.get("rss_sources", [])))
    items.extend(fetch_github_releases(sources_config.get("github_releases", [])))
    items.extend(fetch_hackernews(sources_config.get("hackernews", {})))
    total_count = len(items)

    lookback_hours = int(scoring_config.get("lookback_hours", 24))
    max_items = int(scoring_config.get("max_items_per_day", 20))
    candidate_pool_size = int(llm_config.get("editorial_candidate_pool_size", max_items * 3))

    recent_items = filter_by_lookback(items, lookback_hours)
    scored_items = score_items(recent_items, keywords_config, scoring_config)
    deduped_items = dedupe_items(scored_items, scoring_config)
    rule_candidates = rank_items(deduped_items, candidate_pool_size)
    judged_candidates = judge_candidates_with_llm(rule_candidates, llm_config, editorial_policy)
    ranked_items = rank_items(judged_candidates, max_items)

    markdown = generate_markdown(ranked_items, total_count, max_items)
    output_dir = Path(ROOT / "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    dated_output_path = output_dir / f"{datetime.now(LOCAL_TIMEZONE).strftime('%Y-%m-%d')}.md"
    latest_output_path = output_dir / "daily.md"
    model_output_path = output_dir / "model-daily.md"
    model_failed_path = output_dir / "model-daily-failed.md"
    dated_output_path.write_text(markdown, encoding="utf-8")
    latest_output_path.write_text(markdown, encoding="utf-8")

    previous_backlog = load_backlog(output_dir)
    model_markdown, selected_model_items = _generate_model_daily_required(
        ranked_items,
        previous_backlog,
        total_count,
        scoring_config,
        llm_config,
    )
    model_output_path.write_text(model_markdown, encoding="utf-8")
    _remove_if_exists(model_failed_path)
    logging.info("Generated %s with model summary layer", model_output_path)

    new_backlog = update_backlog_after_model_selection(
        output_dir=output_dir,
        previous_backlog=previous_backlog,
        ranked_items=ranked_items,
        selected_model_items=selected_model_items,
    )
    logging.info("Backlog now contains %s carried candidate items", len(new_backlog))

    logging.info(
        "Generated %s and %s with %s model-ranked items from %s fetched items",
        dated_output_path,
        latest_output_path,
        len(ranked_items),
        total_count,
    )


def _load_required_config(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Required config file does not exist: {path}")
    return load_yaml(path)


def _generate_model_daily_required(
    ranked_items: list[dict],
    previous_backlog: list[dict],
    total_count: int,
    scoring_config: dict,
    llm_config: dict,
) -> tuple[str, list[dict]]:
    merged_candidates = merge_backlog_with_today(ranked_items, previous_backlog)
    logging.info(
        "Model candidate pool merged %s today items with %s backlog items into %s items",
        len(ranked_items),
        len(previous_backlog),
        len(merged_candidates),
    )
    model_candidates = select_items_for_model_daily(merged_candidates, scoring_config, llm_config)
    model_candidates = enrich_items_with_article_text(model_candidates, llm_config)
    model_markdown = generate_model_daily(model_candidates, total_count, scoring_config, llm_config)
    if not model_markdown:
        raise RuntimeError("Model daily generation failed. No rule-only fallback is allowed.")
    return model_markdown, model_candidates


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    main()
