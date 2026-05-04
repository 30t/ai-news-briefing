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
请把结构化新闻材料改写成一份“每日 AI 情报中心”，风格接近新闻联播 + 白话科技讲解。

写作目标：
1. 这不是逐字稿，不是短视频脚本，也不是技术 changelog；它应该像有人在认真给用户播报并解释今天 AI 圈发生了什么。
2. 先总后分，先给今天主线，再按主题合并讲重点新闻，不要机械逐条复述。
3. 技术词随文解释，解释要白话，例如 Agent、function calling、vLLM、Ollama、llama.cpp、GGUF、GPU、VRAM、API、CUDA。
4. 可信度要清楚：官方发布可以说可信度较高；Reddit、Hacker News 等社区来源必须写“社区讨论，不等于官方确认”。
5. “对我的意义”从普通 AI 工具使用者、自动化实践者、职业探索者的视角写，不要假装知道私人背景。
6. 不要输出冗长原文摘录，不要写“中文翻译 / 大意（规则版）”。
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
    lines.extend(["", "## 今日开场", "", _text(result.get("opening"), "今天 AI 圈没有足够信息形成明确主线。"), ""])

    lines.extend(["## 重点播报", ""])
    for segment in _list(result.get("broadcast_segments")):
        related_numbers = [_coerce_int(number) for number in _list(segment.get("related_news_numbers"))]
        related_items = [indexed_items[number] for number in related_numbers if number in indexed_items]
        links = _segment_links(related_items)
        title = _text(segment.get("title"), "未命名重点")
        lines.extend([f"## {title}", ""])
        for paragraph in _list(segment.get("paragraphs")):
            lines.extend([_text(paragraph), ""])
        if segment.get("plain_explainer"):
            lines.extend([f"白话解释：{_text(segment.get('plain_explainer'))}", ""])
        if segment.get("why_it_matters"):
            lines.extend([f"为什么重要：{_text(segment.get('why_it_matters'))}", ""])
        if segment.get("personal_meaning"):
            lines.extend([f"对我的意义：{_text(segment.get('personal_meaning'))}", ""])
        if related_items:
            lines.extend(["来源与可信度：", *[f"- {_source_label(item)}｜{item.get('url') or '无链接'}" for item in related_items], ""])
        elif links:
            lines.extend(["来源与可信度：", *[f"- {link}" for link in links], ""])

    lines.extend(["## 其他消息一句话带过", ""])
    for brief in _list(result.get("quick_mentions")):
        number = _coerce_int(brief.get("number"))
        item = indexed_items.get(number)
        prefix = f"{number}. " if number else "- "
        link = f"（{item.get('url')}）" if item and item.get("url") else ""
        lines.append(f"{prefix}{_text(brief.get('summary'))}{link}")
    lines.append("")

    lines.extend(["## 社区观察与风险提醒", ""])
    risks = _list(result.get("risk_reminders"))
    if risks:
        for risk in risks:
            lines.append(f"- {_text(risk)}")
    else:
        lines.append("- 今天没有明显需要单独标出的高风险消息，但社区讨论仍需结合原文判断。")
    lines.append("")

    lines.extend(["## 今日总评", "", _text(result.get("daily_review"), "今天的 AI 情报主线尚不明确，建议优先查看官方来源。"), ""])

    lines.extend(["## 给我的重点建议", ""])
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
        "opening": "新闻联播式开场，1-3 段。先总结今天 AI 圈主线，并点出官方发布与社区讨论的可信度差异。",
        "broadcast_segments": [
            {
                "title": "重点播报标题，例如：Ollama 更新：本地模型工具正在和 Claude Code 靠近",
                "related_news_numbers": [1, 2],
                "paragraphs": ["播报正文。可以合并多条相关新闻讲，不要机械逐条复述。"],
                "plain_explainer": "随文白话解释关键技术词。",
                "why_it_matters": "为什么重要。",
                "personal_meaning": "对普通 AI 工具使用者、自动化实践者、职业探索者的意义。",
            }
        ],
        "quick_mentions": [{"number": 9, "summary": "其他消息一句话带过"}],
        "risk_reminders": ["社区讨论，不等于官方确认；说明为什么需要谨慎。"],
        "daily_review": "今日总评，用 2-4 句话收束今天的趋势判断。",
        "action_items": ["最多 3 条具体建议，例如值得补课的概念、值得点开的原文、值得尝试的工具。"],
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
            "broadcast_segments_min": int(config.get("broadcast_segments_min", 5)),
            "broadcast_segments_max": int(config.get("broadcast_segments_max", 8)),
            "action_items_max": int(config.get("action_items_max", 3)),
        },
        "style_reference": "请更接近这样的节奏：先说今天主线；然后按主题播报，例如 LangChain 连发版本说明 Agent 架构迁移、Ollama 靠近 Claude Code、llama.cpp 是本地模型底层发动机、vLLM 是服务器部署调度器；最后做今日总评和给我的重点建议。",
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
    required = ["opening", "broadcast_segments", "quick_mentions", "risk_reminders", "daily_review", "action_items"]
    missing = [key for key in required if key not in result]
    if missing:
        raise RuntimeError(f"Intelligence center JSON missing fields: {', '.join(missing)}")
    segments = _list(result.get("broadcast_segments"))
    minimum = int(config.get("broadcast_segments_min", 5))
    if len(segments) < minimum:
        logging.warning("LLM returned only %s broadcast segments; expected at least %s.", len(segments), minimum)


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


def _segment_links(items: list[dict[str, Any]]) -> list[str]:
    return [item.get("url", "") for item in items if item.get("url")]
