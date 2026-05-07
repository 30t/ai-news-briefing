from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fetch_article_text import enrich_items_with_article_text
from generate_model_daily import generate_model_daily, select_items_for_model_daily
from summarize_with_llm import enhance_items_with_llm, get_api_key
from utils import LOCAL_TIMEZONE, ROOT, load_yaml, setup_logging


LEVEL_MAP = {
    "官方确认": "official_confirmed",
    "技术社区": "tech_community",
    "早期信号": "early_signal",
    "待验证": "needs_verification",
}

TYPE_MAP = {
    "RSS": "rss",
    "GitHub Releases": "github_release",
    "Hacker News": "hackernews",
}


def main() -> None:
    setup_logging()
    output_dir = Path(ROOT / "output")
    daily_path = output_dir / "daily.md"
    model_output_path = output_dir / "model-daily.md"
    model_failed_path = output_dir / "model-daily-failed.md"

    llm_config = _load_optional_config(ROOT / "config" / "llm.yml")
    scoring_config = _load_optional_config(ROOT / "config" / "scoring.yml")

    if not daily_path.exists():
        _write_failure(model_failed_path, "找不到 output/daily.md，无法只针对现有候选池生成模型日报。")
        _remove_if_exists(model_output_path)
        return

    total_count, ranked_items = parse_daily_markdown(daily_path.read_text(encoding="utf-8"))
    if not ranked_items:
        _write_failure(model_failed_path, "output/daily.md 中没有解析到候选新闻条目。")
        _remove_if_exists(model_output_path)
        return

    model_markdown = _try_generate_model_daily_from_items(ranked_items, total_count, scoring_config, llm_config)
    if model_markdown:
        model_output_path.write_text(model_markdown, encoding="utf-8")
        _remove_if_exists(model_failed_path)
        logging.info("Generated %s from existing %s", model_output_path, daily_path)
        return

    _remove_if_exists(model_output_path)
    _write_failure(model_failed_path, "模型日报没有成功生成。基础候选池未重新抓取，仍可查看 output/daily.md。")


def parse_daily_markdown(content: str) -> tuple[int, list[dict[str, Any]]]:
    total_count = _parse_total_count(content)
    chunks = re.split(r"\n---\n", content)
    items: list[dict[str, Any]] = []
    for chunk in chunks:
        match = re.search(r"^###\s+(\d+)\.\s+(.+)$", chunk, flags=re.MULTILINE)
        if not match:
            continue
        item = _parse_item_chunk(int(match.group(1)), match.group(2).strip(), chunk)
        if item:
            items.append(item)
    return total_count or len(items), items


def _parse_item_chunk(index: int, title: str, chunk: str) -> dict[str, Any] | None:
    url = _field(chunk, "原文链接")
    if not url:
        return None
    source_type = _field(chunk, "来源类型") or _field(chunk, "发布渠道")
    keywords = _field(chunk, "命中关键词")
    score = _field(chunk, "规则分数")
    excerpt = _blockquote_after(chunk, "Feed 摘要")
    return {
        "title": title,
        "url": url,
        "source_name": _field(chunk, "来源名称") or "未知来源",
        "source_type": TYPE_MAP.get(source_type, source_type or "rss"),
        "source_level": LEVEL_MAP.get(_field(chunk, "来源等级"), "needs_verification"),
        "published_at": _field(chunk, "发布时间"),
        "summary_or_excerpt": excerpt,
        "matched_keywords": _split_keywords(keywords),
        "tags": _infer_tags(title, keywords, source_type),
        "score": _parse_int(score),
        "daily_index": index,
    }


def _field(chunk: str, name: str) -> str:
    pattern = rf"^- {re.escape(name)}：(.+)$"
    match = re.search(pattern, chunk, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _blockquote_after(chunk: str, heading: str) -> str:
    marker = f"- {heading}："
    if marker not in chunk:
        return ""
    after = chunk.split(marker, 1)[1]
    lines: list[str] = []
    for line in after.splitlines()[1:]:
        if line.startswith("  > "):
            lines.append(line.removeprefix("  > ").strip())
            continue
        if line.startswith("- "):
            break
    return "\n".join(lines).strip()


def _parse_total_count(content: str) -> int:
    match = re.search(r"今天自动抓取\s+(\d+)\s+条信息", content)
    return int(match.group(1)) if match else 0


def _split_keywords(text: str) -> list[str]:
    if not text or text == "无":
        return []
    return [part.strip() for part in re.split(r"、|,", text) if part.strip()]


def _parse_int(text: str) -> int:
    match = re.search(r"-?\d+", text or "")
    return int(match.group(0)) if match else 0


def _infer_tags(title: str, keywords: str, source_type: str) -> list[str]:
    text = f"{title} {keywords} {source_type}".lower()
    tags: set[str] = set()
    if any(word in text for word in ["agent", "mcp", "copilot", "codex", "claude code", "cursor"]):
        tags.add("agent")
        tags.add("coding_tool")
    if any(word in text for word in ["n8n", "dify", "langchain", "langgraph", "llamaindex", "workflow", "open webui", "ollama", "litellm"]):
        tags.add("ai_app")
    if any(word in text for word in ["rag", "retrieval", "embedding", "vector", "qdrant", "milvus", "chroma"]):
        tags.add("rag_data")
    if any(word in text for word in ["release", "github releases", "open source", "llama.cpp", "transformers", "crewai"]):
        tags.add("open_source")
    if any(word in text for word in ["nvidia", "gpu", "blackwell", "cuda", "hbm", "tsmc", "semiconductor", "rtx"]):
        tags.add("semiconductor")
    if any(word in text for word in ["enterprise", "business", "adoption", "bank", "servicenow", "pricing", "customer"]):
        tags.add("business")
    if any(word in text for word in ["gpt", "claude", "gemini", "llama", "qwen", "deepseek", "model"]):
        tags.add("model")
    return sorted(tags)


def _try_generate_model_daily_from_items(
    ranked_items: list[dict[str, Any]],
    total_count: int,
    scoring_config: dict[str, Any],
    llm_config: dict[str, Any],
) -> str | None:
    if not llm_config.get("enabled", False):
        logging.warning("Model-only generation skipped: LLM disabled.")
        return None
    if not get_api_key(llm_config):
        logging.warning("Model-only generation skipped: missing LLM API key secret.")
        return None

    model_candidates = select_items_for_model_daily(ranked_items, scoring_config, llm_config)
    model_candidates = enrich_items_with_article_text(model_candidates, llm_config)
    model_candidates = enhance_items_with_llm(model_candidates, llm_config)
    return generate_model_daily(model_candidates, total_count, scoring_config, llm_config)


def _load_optional_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"enabled": False}
    return load_yaml(path)


def _write_failure(path: Path, reason: str) -> None:
    today = datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M")
    path.write_text(
        "\n".join(
            [
                f"# AI 新闻模型日报生成失败｜{today}",
                "",
                reason,
                "",
                "基础规则版日报仍然可用：",
                "",
                "- `output/daily.md`",
                "- `output/YYYY-MM-DD.md`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    main()
