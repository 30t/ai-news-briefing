from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from utils import normalize_space, strip_html


SYSTEM_PROMPT = """你是一个严谨的中文 AI 新闻编辑。
你的任务是根据系统提供的结构化信息和可用正文片段，直接写出适合中文读者阅读的新闻标题和核心摘要。

必须遵守：
1. 只能基于输入内容写作，不得编造原文没有的信息。
2. 如果信息不足，明确写“原文信息不足”。
3. 保留公司名、模型名、项目名、版本号的英文原文。
4. 不要把发布渠道误写成新闻主体。例如 GitHub Releases 是发布渠道，Ollama 才可能是项目来源。
5. 来源等级由系统给出，你不能把社区讨论改写成官方确认。
6. 中文标题由你直接决定，不要只是机械翻译原始标题；标题必须点出新闻主体和关键变化。
7. 核心摘要优先基于正文片段，其次才参考 RSS 摘要；如果没有正文片段，必须更保守。
8. 输出必须是严格 JSON，不要包含 Markdown、解释或代码块。
"""


def enhance_items_with_llm(items: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("enabled", False):
        logging.info("LLM enhancement disabled by config.")
        return items

    api_key = _get_api_key(config)
    if not api_key:
        logging.warning("LLM enhancement skipped: missing API key env %s.", config.get("api_key_env", "LLM_API_KEY"))
        return items

    max_items = int(config.get("max_items_for_llm", 20))
    enhanced: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if index >= max_items:
            enhanced.append(item)
            continue
        enhanced.append(_enhance_one_item(item, config, api_key))
    return enhanced


def _get_api_key(config: dict[str, Any]) -> str:
    primary = str(config.get("api_key_env") or "LLM_API_KEY")
    fallback = str(config.get("fallback_api_key_env") or "")
    return os.getenv(primary, "").strip() or (os.getenv(fallback, "").strip() if fallback else "")


def _enhance_one_item(item: dict[str, Any], config: dict[str, Any], api_key: str) -> dict[str, Any]:
    max_retries = int(config.get("max_retries", 1))
    for attempt in range(max_retries + 1):
        try:
            result = _call_openai_compatible(item, config, api_key)
            validated = _validate_llm_result(result)
            if not validated:
                raise ValueError("LLM result did not contain usable fields")
            updated = dict(item)
            updated["llm"] = validated
            return updated
        except Exception as exc:  # noqa: BLE001 - each item must fail independently.
            if attempt >= max_retries:
                logging.warning("LLM enhancement failed for %s: %s", item.get("title", "untitled"), exc)
                return item
            time.sleep(1 + attempt)
    return item


def _call_openai_compatible(item: dict[str, Any], config: dict[str, Any], api_key: str) -> dict[str, Any]:
    base_url = str(config.get("base_url") or "https://api.deepseek.com").rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    payload = {
        "model": config.get("model", "deepseek-chat"),
        "temperature": float(config.get("temperature", 0.2)),
        "max_tokens": int(config.get("max_output_tokens", 700)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(
                    item,
                    int(config.get("excerpt_input_limit", 1800)),
                    int(config.get("article_text_limit", 5000)),
                ),
            },
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-news-briefing/llm-enhancer",
        },
        method="POST",
    )
    timeout = int(config.get("timeout_seconds", 30))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-configured API endpoint.
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("empty LLM response")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON response: {content[:300]}") from exc


def _build_user_prompt(item: dict[str, Any], excerpt_limit: int, article_limit: int) -> str:
    excerpt = strip_html(item.get("summary_or_excerpt") or "")
    if len(excerpt) > excerpt_limit:
        excerpt = excerpt[: excerpt_limit - 1].rstrip() + "..."
    article_text = strip_html(item.get("article_text") or "")
    if len(article_text) > article_limit:
        article_text = article_text[: article_limit - 1].rstrip() + "..."
    source_context = {
        "original_title": item.get("title"),
        "url": item.get("url"),
        "source_name": item.get("source_name"),
        "source_type": item.get("source_type"),
        "source_level": item.get("source_level"),
        "published_at": item.get("published_at"),
        "matched_keywords": item.get("matched_keywords") or [],
        "rule_score": item.get("score", 0),
        "hn_score": item.get("hn_score"),
        "release_version": item.get("release_version"),
        "summary_or_excerpt": excerpt,
        "article_text": article_text,
        "article_text_source": item.get("article_text_source"),
    }
    schema = {
        "final_title_zh": "你直接决定的准确中文标题，尽量不超过 36 个汉字；保留必要英文名和版本号",
        "core_summary_zh": "2-3 句中文核心摘要，说明原文真正说了什么；不要只复述标题",
        "why_it_matters_zh": "1 句中文，说明为什么值得关注；信息不足则写原文信息不足",
    }
    return (
        "请根据下面的新闻信息输出 JSON。\n"
        f"目标 JSON 字段：{json.dumps(schema, ensure_ascii=False)}\n"
        f"新闻信息：{json.dumps(source_context, ensure_ascii=False)}"
    )


def _validate_llm_result(result: dict[str, Any]) -> dict[str, str]:
    validated = {
        "final_title_zh": _clean_result_text(result.get("final_title_zh") or result.get("improved_title_zh"), 100),
        "core_summary_zh": _clean_result_text(result.get("core_summary_zh"), 360),
        "why_it_matters_zh": _clean_result_text(result.get("why_it_matters_zh"), 180),
    }
    return {key: value for key, value in validated.items() if value}


def _clean_result_text(value: Any, limit: int) -> str:
    text = normalize_space(str(value or ""))
    text = text.strip("` \n\t")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
