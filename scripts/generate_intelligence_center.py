from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from generate_markdown import LEVEL_LABELS, TYPE_LABELS
from utils import format_local_time, normalize_space, strip_html


SYSTEM_PROMPT = """你是一名中文 AI 情报主播兼科技解释员。
请把结构化新闻材料改写成一份“每日 AI 情报中心”，适合阅读，也适合 ChatGPT 语音朗读。

要求：
1. 语言像新闻联播 + 科技解释员：清楚、有节奏、不夸大。
2. 不要输出冗长原文摘录，不要写“中文翻译 / 大意（规则版）”。
3. 社区来源必须明确写“社区讨论，不等于官方确认”。
4. 技术词必须随文白话解释，例如 Agent、function calling、vLLM、Ollama、llama.cpp、GGUF、GPU、VRAM、API、CUDA。
5. “对我的意义”使用普通 AI 工具使用者、自动化实践者、职业探索者的视角，不要假装知道私人背景。
6. 模型根据当天新闻本身判断主线和必听内容，不要按固定用户兴趣列表重排。
7. 只基于输入材料写作，不得编造事实。信息不足就保守表达。
8. 输出必须是严格 JSON，不要包含 Markdown、解释或代码块。
"""


def require_llm_api_key(config: dict[str, Any]) -> str:
    primary = str(config.get("api_key_env") or "LLM_API_KEY")
    fallback = str(config.get("fallback_api_key_env") or "DEEPSEEK_API_KEY")
    api_key = os.getenv(primary, "").strip() or os.getenv(fallback, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing required LLM API key. Set {primary} or {fallback}.")
    return api_key


def generate_intelligence_center(
    items: list[dict[str, Any]],
    *,
    total_count: int,
    candidate_count: int,
    final_count: int,
    skipped_history_count: int,
    briefing_date: date,
    config: dict[str, Any],
    api_key: str,
) -> str:
    result = _call_openai_compatible_center(
        items,
        total_count=total_count,
        candidate_count=candidate_count,
        final_count=final_count,
        skipped_history_count=skipped_history_count,
        briefing_date=briefing_date,
        config=config,
        api_key=api_key,
    )
    return render_intelligence_markdown(
        result,
        items,
        total_count=total_count,
        candidate_count=candidate_count,
        final_count=final_count,
        skipped_history_count=skipped_history_count,
        briefing_date=briefing_date,
        config=config,
    )


def render_intelligence_markdown(
    result: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    total_count: int,
    candidate_count: int,
    final_count: int,
    skipped_history_count: int,
    briefing_date: date,
    config: dict[str, Any],
) -> str:
    indexed_items = {index + 1: item for index, item in enumerate(items)}
    lines = [
        f"# 每日 AI 情报｜{briefing_date.isoformat()}",
        "",
        f"今天抓取 {total_count} 条，7 天历史去重后进入候选池 {candidate_count} 条，最终写入 {final_count} 条。",
    ]
    if skipped_history_count:
        lines.append(f"其中 {skipped_history_count} 条因过去 7 天已出现而跳过。")
    lines.extend(["", "## 今日一句话", "", _text(result.get("one_sentence"), "今天没有足够信息形成明确主线。"), ""])

    lines.extend(["## 今日三条主线", ""])
    for thread in _list(result.get("main_threads")):
        related = _join_numbers(thread.get("related_news_numbers"))
        lines.extend(
            [
                f"### {_text(thread.get('title'), '未命名主线')}",
                "",
                f"- 发生了什么：{_text(thread.get('what_happened'))}",
                f"- 相关新闻编号：{related or '无'}",
                f"- 为什么重要：{_text(thread.get('why_it_matters'))}",
                f"- 对我的意义：{_text(thread.get('personal_meaning'))}",
                "",
            ]
        )

    lines.extend(["## 今日必听新闻", ""])
    for news in _list(result.get("must_listen_news")):
        number = _coerce_int(news.get("number"))
        item = indexed_items.get(number)
        source_label = _source_label(item) if item else _text(news.get("credibility"))
        link = item.get("url") if item else news.get("url")
        title = _text(news.get("broadcast_title"), item.get("title") if item else "未命名新闻")
        lines.extend(
            [
                f"### {number or '-'}. {title}",
                "",
                f"- 一句话：{_text(news.get('one_liner'))}",
                f"- 发生了什么：{_text(news.get('what_happened'))}",
                f"- 名词解释：{_text(news.get('term_explainer'))}",
                f"- 为什么重要：{_text(news.get('why_it_matters'))}",
                f"- 对我的意义：{_text(news.get('personal_meaning'))}",
                f"- 可信度：{source_label}",
                f"- 原文链接：{link or '无链接'}",
                "",
            ]
        )

    lines.extend(["## 今日一句话带过", ""])
    for brief in _list(result.get("quick_mentions")):
        number = _coerce_int(brief.get("number"))
        item = indexed_items.get(number)
        prefix = f"{number}. " if number else "- "
        link = f"（{item.get('url')}）" if item and item.get("url") else ""
        lines.append(f"{prefix}{_text(brief.get('summary'))}{link}")
    lines.append("")

    lines.extend(["## 今日风险提醒", ""])
    risks = _list(result.get("risk_reminders"))
    if risks:
        for risk in risks:
            lines.append(f"- {_text(risk)}")
    else:
        lines.append("- 今天没有明显需要单独标出的高风险消息，但社区讨论仍需结合原文判断。")
    lines.append("")

    lines.extend(["## 今日行动建议", ""])
    for action in _list(result.get("action_items"))[: int(config.get("action_items_max", 3))]:
        lines.append(f"- {_text(action)}")
    lines.append("")
    return "\n".join(lines)


def _call_openai_compatible_center(
    items: list[dict[str, Any]],
    *,
    total_count: int,
    candidate_count: int,
    final_count: int,
    skipped_history_count: int,
    briefing_date: date,
    config: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    base_url = str(config.get("base_url") or "https://api.deepseek.com").rstrip("/")
    payload = {
        "model": config.get("model", "deepseek-v4-flash"),
        "temperature": float(config.get("center_temperature", config.get("temperature", 0.2))),
        "max_tokens": int(config.get("center_max_output_tokens", 3500)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_center_prompt(items, total_count, candidate_count, final_count, skipped_history_count, briefing_date, config)},
        ],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-news-briefing/intelligence-center",
        },
        method="POST",
    )
    timeout = int(config.get("center_timeout_seconds", 60))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured LLM endpoint.
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Intelligence center LLM request failed: HTTP {exc.code}: {body[:500]}") from exc
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Intelligence center LLM returned empty content.")
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Intelligence center LLM returned invalid JSON: {content[:500]}") from exc
    _validate_center_result(result, config)
    return result


def _build_center_prompt(
    items: list[dict[str, Any]],
    total_count: int,
    candidate_count: int,
    final_count: int,
    skipped_history_count: int,
    briefing_date: date,
    config: dict[str, Any],
) -> str:
    compact_items = [_compact_item(index + 1, item, int(config.get("center_article_text_limit", 2200))) for index, item in enumerate(items)]
    schema = {
        "one_sentence": "1-2 句话，总结今天 AI 圈最重要的主线",
        "main_threads": [
            {
                "title": "主线标题",
                "what_happened": "发生了什么",
                "related_news_numbers": [1, 2],
                "why_it_matters": "为什么重要",
                "personal_meaning": "对普通 AI 工具使用者、自动化实践者、职业探索者的意义",
            }
        ],
        "must_listen_news": [
            {
                "number": 1,
                "broadcast_title": "播报标题",
                "one_liner": "一句话",
                "what_happened": "发生了什么",
                "term_explainer": "随文解释关键名词",
                "why_it_matters": "为什么重要",
                "personal_meaning": "对我的意义",
            }
        ],
        "quick_mentions": [{"number": 9, "summary": "一句话带过"}],
        "risk_reminders": ["社区讨论，不等于官方确认；说明为什么需要谨慎。"],
        "action_items": ["最多 3 条具体行动建议"],
    }
    instructions = {
        "briefing_date": briefing_date.isoformat(),
        "stats": {
            "fetched_total": total_count,
            "history_deduped_candidate_count": candidate_count,
            "final_item_count": final_count,
            "history_skipped_count": skipped_history_count,
        },
        "limits": {
            "main_threads_min": int(config.get("main_thread_min", 2)),
            "main_threads_max": int(config.get("main_thread_max", 4)),
            "must_listen_min": int(config.get("must_listen_min", 6)),
            "must_listen_max": int(config.get("must_listen_max", 8)),
            "action_items_max": int(config.get("action_items_max", 3)),
        },
        "schema": schema,
        "news_items": compact_items,
    }
    return "请根据以下 JSON 输入生成严格 JSON 输出：\n" + json.dumps(instructions, ensure_ascii=False)


def _compact_item(index: int, item: dict[str, Any], text_limit: int) -> dict[str, Any]:
    llm = item.get("llm") or {}
    text = strip_html(item.get("article_text") or item.get("summary_or_excerpt") or "")
    if len(text) > text_limit:
        text = text[: text_limit - 1].rstrip() + "..."
    return {
        "number": index,
        "title": item.get("title"),
        "llm_title": llm.get("final_title_zh"),
        "llm_core_summary": llm.get("core_summary_zh"),
        "llm_why_it_matters": llm.get("why_it_matters_zh"),
        "source_name": item.get("source_name"),
        "source_type": item.get("source_type"),
        "source_type_label": TYPE_LABELS.get(item.get("source_type"), item.get("source_type")),
        "source_level": item.get("source_level"),
        "source_level_label": LEVEL_LABELS.get(item.get("source_level"), "待验证"),
        "published_at": format_local_time(item.get("published_at")),
        "url": item.get("url"),
        "rule_score": item.get("score"),
        "hn_score": item.get("hn_score"),
        "matched_keywords": item.get("matched_keywords") or [],
        "material": text,
    }


def _validate_center_result(result: dict[str, Any], config: dict[str, Any]) -> None:
    required = ["one_sentence", "main_threads", "must_listen_news", "quick_mentions", "risk_reminders", "action_items"]
    missing = [key for key in required if key not in result]
    if missing:
        raise RuntimeError(f"Intelligence center JSON missing fields: {', '.join(missing)}")
    must_listen = _list(result.get("must_listen_news"))
    minimum = int(config.get("must_listen_min", 6))
    if len(must_listen) < minimum:
        logging.warning("LLM returned only %s must-listen items; expected at least %s.", len(must_listen), minimum)


def _source_label(item: dict[str, Any] | None) -> str:
    if not item:
        return "待验证"
    level = LEVEL_LABELS.get(item.get("source_level"), "待验证")
    source = item.get("source_name") or "未知来源"
    if item.get("source_level") == "tech_community":
        return f"{level}｜{source}｜社区讨论，不等于官方确认"
    if item.get("source_level") in {"early_signal", "needs_verification"}:
        return f"{level}｜{source}｜需要继续核验"
    return f"{level}｜{source}"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str = "信息不足。") -> str:
    text = normalize_space(str(value or ""))
    return text or fallback


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _join_numbers(value: Any) -> str:
    numbers = [str(number) for number in _list(value)]
    return "、".join(numbers)
