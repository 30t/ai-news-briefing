from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from fetch_article_text import enrich_items_with_article_text
from generate_model_daily import generate_model_daily, select_items_for_model_daily
from judge_candidates_with_llm import require_llm_api_key
from utils import ROOT, load_yaml, setup_logging


LEVEL_MAP = {
    "官方确认": "official_confirmed",
    "技术社区": "tech_community",
    "早期信号": "early_signal",
    "待验证": "needs_verification",
}

RISK_MAP = {
    "官方确认": "official_confirmed",
    "社区讨论": "community_discussed",
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

    llm_config = _load_required_config(ROOT / "config" / "llm.yml")
    scoring_config = _load_required_config(ROOT / "config" / "scoring.yml")
    require_llm_api_key(llm_config)

    if not daily_path.exists():
        raise RuntimeError("Missing output/daily.md. Run the full daily pipeline before model-only refresh.")

    total_count, ranked_items = parse_daily_markdown(daily_path.read_text(encoding="utf-8"))
    if not ranked_items:
        raise RuntimeError("No candidate items could be parsed from output/daily.md.")

    model_candidates = select_items_for_model_daily(ranked_items, scoring_config, llm_config)
    model_candidates = enrich_items_with_article_text(model_candidates, llm_config)
    model_markdown = generate_model_daily(model_candidates, total_count, scoring_config, llm_config)
    if not model_markdown:
        raise RuntimeError("Model daily generation failed. No rule-only fallback is allowed.")

    model_output_path.write_text(model_markdown, encoding="utf-8")
    _remove_if_exists(model_failed_path)
    logging.info("Generated %s from existing %s", model_output_path, daily_path)


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
    excerpt = _blockquote_after(chunk, "Feed 摘要")
    editorial = _parse_editorial(chunk)
    editorial_score = _parse_int(_field(chunk, "模型编辑分"))
    rule_relevance_score = _parse_int(_field(chunk, "规则召回分"))
    source_trust_score = _parse_int(_field(chunk, "来源可信分"))
    keyword_relevance_score = _parse_int(_field(chunk, "关键词召回分"))
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
        "source_trust_score": source_trust_score,
        "keyword_relevance_score": keyword_relevance_score,
        "rule_relevance_score": rule_relevance_score,
        "editorial": editorial,
        "editorial_score": editorial_score or rule_relevance_score,
        "score": editorial_score or rule_relevance_score,
        "llm": _parse_reusable_llm_fields(chunk),
        "daily_index": index,
    }


def _parse_editorial(chunk: str) -> dict[str, Any]:
    scores = _parse_model_score_line(_field(chunk, "模型分项"))
    risk = _field(chunk, "风险等级")
    return {
        "newsworthiness_score": scores.get("newsworthiness_score", 1),
        "personal_relevance_score": scores.get("personal_relevance_score", 1),
        "actionability_score": scores.get("actionability_score", 1),
        "confidence_score": scores.get("confidence_score", 1),
        "content_type": _field(chunk, "内容类型") or "other",
        "risk_level": RISK_MAP.get(risk, "needs_verification"),
        "decision": _field(chunk, "编辑决策") or "maybe",
        "reason_zh": _field(chunk, "入选原因"),
    }


def _parse_reusable_llm_fields(chunk: str) -> dict[str, str]:
    return {
        "final_title_zh": _field(chunk, "模型中文标题"),
        "background_zh": _field(chunk, "模型背景"),
        "core_summary_zh": _field(chunk, "模型核心摘要"),
        "evidence_or_result_zh": _field(chunk, "模型证据说明"),
        "why_it_matters_zh": _field(chunk, "模型重要性"),
        "reader_action_zh": _field(chunk, "模型建议动作"),
    }


def _parse_model_score_line(text: str) -> dict[str, int]:
    mapping = {
        "新闻价值": "newsworthiness_score",
        "个人相关性": "personal_relevance_score",
        "可行动性": "actionability_score",
        "判断信心": "confidence_score",
    }
    result: dict[str, int] = {}
    for label, key in mapping.items():
        match = re.search(rf"{label}\s*(\d+)\s*/\s*10", text or "")
        if match:
            result[key] = max(1, min(10, int(match.group(1))))
    return result


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
    if any(word in text for word in ["risc-v", "riscv", "opensbi", "qemu", "zephyr", "rt-thread", "plct", "xiangshan"]):
        tags.add("riscv_stack")
    if any(word in text for word in ["tinyml", "edge ai", "esp32", "arduino", "raspberry pi", "tflite micro", "cmsis-nn", "mcu"]):
        tags.add("embedded_edge_ai")
    if any(word in text for word in ["enterprise", "business", "adoption", "bank", "servicenow", "pricing", "customer"]):
        tags.add("business")
    if any(word in text for word in ["gpt", "claude", "gemini", "llama", "qwen", "deepseek", "model"]):
        tags.add("model")
    return sorted(tags)


def _load_required_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Required config file does not exist: {path}")
    return load_yaml(path)


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    main()
