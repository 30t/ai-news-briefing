from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from utils import normalize_space, strip_html


SYSTEM_PROMPT = """你是一个严谨的中文 AI 新闻解释型编辑。
你的任务是根据系统提供的结构化信息和可用正文片段，写出适合中文读者阅读的新闻标题、背景解释、核心摘要、结果证据和重要性判断。

必须遵守：
1. 只能基于输入内容写作，不得编造原文没有的信息。
2. 如果信息不足，明确写“原文信息不足”。
3. 保留公司名、模型名、项目名、版本号的英文原文。
4. 不要把发布渠道误写成新闻主体。例如 GitHub Releases 是发布渠道，Ollama / LangGraph / n8n 才是项目来源。
5. 来源等级由系统给出，你不能把社区讨论改写成官方确认。
6. 中文标题由你直接决定，不要只是机械翻译原始标题；标题必须点出新闻主体和关键变化。
7. 核心摘要优先基于正文片段，其次才参考 RSS 摘要；如果没有正文片段，必须更保守。
8. 对普通读者可能不懂的英文名词，第一次出现时用中文括号解释它是什么或干什么；不要机械翻译。
9. 对版本新闻，要说明更新对象是主项目、子项目、CLI、SDK、插件还是平台；如果原文未说明上一版本，写“原文未明确说明从哪个版本升级而来”。
10. 对论文 / benchmark，必须说明这是研究或评测，不等于已经产品化。
11. 对社区讨论，必须说明“社区讨论，不等于官方确认”。
12. 输出必须是严格 JSON，不要包含 Markdown、解释或代码块。
"""


def enhance_items_with_llm(items: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("enabled", False):
        logging.info("LLM enhancement disabled by config.")
        return items

    api_key = get_api_key(config)
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


def get_api_key(config: dict[str, Any]) -> str:
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
        "temperature": float(config.get("temperature", 0.15)),
        "max_tokens": int(config.get("max_output_tokens", 1100)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(
                    item,
                    int(config.get("excerpt_input_limit", 2200)),
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
    timeout = int(config.get("timeout_seconds", 55))
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
        "tags": item.get("tags") or [],
        "rule_score": item.get("score", 0),
        "hn_score": item.get("hn_score"),
        "release_version": item.get("release_version"),
        "summary_or_excerpt": excerpt,
        "article_text": article_text,
        "article_text_source": item.get("article_text_source"),
    }
    schema = {
        "final_title_zh": "准确中文标题，尽量不超过 44 个汉字；保留必要英文名和版本号；点出新闻主体和关键变化",
        "background_zh": "2-3 句中文背景，说明新闻对象是什么、处在哪个领域、原来解决什么问题；必要英文名词加中文功能括号",
        "core_summary_zh": "3-4 句中文核心摘要，说明这次具体发生了什么、变化点是什么；不要只复述标题",
        "evidence_or_result_zh": "1-2 句中文，说明原文有没有量化结果、测试数据、版本关系或证据；没有则写原文未给出明确量化结果/版本关系",
        "why_it_matters_zh": "1-2 句中文，说明为什么值得关注；信息不足则写原文信息不足",
        "reader_action_zh": "1 句中文，说明读者应该试用、观察、归档、检查自身系统、深入研究或暂时忽略",
    }
    return (
        "请根据下面的新闻信息输出 JSON。\n"
        "写作目标：把每条新闻从摘要升级为背景解释，帮助非专家读者看懂。\n"
        f"目标 JSON 字段：{json.dumps(schema, ensure_ascii=False)}\n"
        "注意：不要编造输入中没有的事实。公司或项目背景如果输入不足，写原文信息不足。\n"
        f"新闻信息：{json.dumps(source_context, ensure_ascii=False)}"
    )


def _validate_llm_result(result: dict[str, Any]) -> dict[str, str]:
    validated = {
        "final_title_zh": _clean_result_text(result.get("final_title_zh") or result.get("improved_title_zh"), 120),
        "background_zh": _clean_result_text(result.get("background_zh"), 520),
        "core_summary_zh": _clean_result_text(result.get("core_summary_zh"), 760),
        "evidence_or_result_zh": _clean_result_text(result.get("evidence_or_result_zh"), 360),
        "why_it_matters_zh": _clean_result_text(result.get("why_it_matters_zh"), 360),
        "reader_action_zh": _clean_result_text(result.get("reader_action_zh"), 260),
    }
    return {key: value for key, value in validated.items() if value}


def _clean_result_text(value: Any, limit: int) -> str:
    text = normalize_space(str(value or ""))
    text = text.strip("` \n\t")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
