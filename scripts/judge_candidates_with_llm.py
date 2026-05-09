from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from summarize_with_llm import get_api_key
from utils import normalize_space, strip_html


SYSTEM_PROMPT = """你是一个严格的中文 AI 情报编辑。
你的任务不是写新闻摘要，而是根据编辑政策判断一条候选信息是否值得进入当天日报。

必须遵守：
1. 只能基于输入信息和编辑政策判断，不得补充输入中没有的事实。
2. 关键词命中只代表相关，不代表重要。
3. 来源等级只是可信度底座，不代表自动重要。
4. 官方来源通常可信度更高，但小版本、纯营销、活动信息仍可能不重要。
5. 社区、Reddit、Hacker News 可以有早期价值，但必须降低事实确认权重。
6. arXiv / benchmark / 论文属于早期信号，不等于产品落地。
7. 评分要保守。普通版本更新、低密度博客、纯活动、纯招聘、纯融资传言不要给高分。
8. 输出必须是严格 JSON，不要 Markdown，不要代码块。
"""


def require_llm_api_key(config: dict[str, Any]) -> str:
    if not config.get("enabled", False):
        raise RuntimeError("LLM layer is required, but config/llm.yml has enabled=false.")
    api_key = get_api_key(config)
    if not api_key:
        primary = config.get("api_key_env", "LLM_API_KEY")
        fallback = config.get("fallback_api_key_env", "DEEPSEEK_API_KEY")
        raise RuntimeError(f"LLM layer is required, but missing {primary} or {fallback} secret.")
    return api_key


def judge_candidates_with_llm(
    items: list[dict[str, Any]],
    config: dict[str, Any],
    editorial_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    api_key = require_llm_api_key(config)
    max_items = int(config.get("editorial_judge_max_items", config.get("editorial_candidate_pool_size", 120)))
    judged: list[dict[str, Any]] = []
    for index, item in enumerate(items[:max_items]):
        judged.append(_judge_one_item(index + 1, item, config, api_key, editorial_policy or {}))
    if len(items) > max_items:
        logging.info("Skipped %s items beyond editorial_judge_max_items=%s", len(items) - max_items, max_items)
    return judged


def _judge_one_item(
    index: int,
    item: dict[str, Any],
    config: dict[str, Any],
    api_key: str,
    editorial_policy: dict[str, Any],
) -> dict[str, Any]:
    max_retries = int(config.get("editorial_judge_max_retries", config.get("max_retries", 1)))
    for attempt in range(max_retries + 1):
        try:
            result = _call_llm(item, config, api_key, editorial_policy)
            editorial = _validate_result(result)
            updated = dict(item)
            updated["editorial"] = editorial
            updated["editorial_score"] = _calculate_editorial_score(updated)
            updated["score"] = updated["editorial_score"]
            return updated
        except Exception as exc:  # noqa: BLE001 - fail the whole run if editorial judging fails repeatedly.
            if attempt >= max_retries:
                raise RuntimeError(f"Editorial judge failed for item {index}: {item.get('title', 'untitled')}: {exc}") from exc
            time.sleep(1 + attempt)
    raise RuntimeError("Editorial judge failed unexpectedly")


def _call_llm(
    item: dict[str, Any],
    config: dict[str, Any],
    api_key: str,
    editorial_policy: dict[str, Any],
) -> dict[str, Any]:
    base_url = str(config.get("base_url") or "https://api.deepseek.com").rstrip("/")
    payload = {
        "model": config.get("model", "deepseek-chat"),
        "temperature": float(config.get("editorial_judge_temperature", 0.1)),
        "max_tokens": int(config.get("editorial_judge_max_output_tokens", 800)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_prompt(
                    item,
                    editorial_policy,
                    int(config.get("editorial_judge_excerpt_limit", 1800)),
                ),
            },
        ],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-news-briefing/editorial-judge",
        },
        method="POST",
    )
    timeout = int(config.get("editorial_judge_timeout_seconds", config.get("timeout_seconds", 55)))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-configured API endpoint.
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("empty editorial judge response")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON response: {content[:300]}") from exc


def _build_prompt(item: dict[str, Any], editorial_policy: dict[str, Any], excerpt_limit: int) -> str:
    excerpt = strip_html(item.get("summary_or_excerpt") or "")
    excerpt = normalize_space(excerpt)
    if len(excerpt) > excerpt_limit:
        excerpt = excerpt[: excerpt_limit - 1].rstrip() + "..."
    payload = {
        "title": item.get("title"),
        "url": item.get("url"),
        "source_name": item.get("source_name"),
        "source_type": item.get("source_type"),
        "source_level": item.get("source_level"),
        "published_at": item.get("published_at"),
        "matched_keywords": item.get("matched_keywords") or [],
        "tags": item.get("tags") or [],
        "rule_relevance_score": item.get("rule_relevance_score", item.get("score", 0)),
        "keyword_relevance_score": item.get("keyword_relevance_score", 0),
        "source_trust_score": item.get("source_trust_score", 0),
        "rule_penalty": item.get("rule_penalty", 0),
        "hn_score": item.get("hn_score"),
        "release_version": item.get("release_version"),
        "summary_or_excerpt": excerpt,
    }
    schema = {
        "newsworthiness_score": "1-10，新闻本身的信息增量和重要性。关键词多不等于高分。",
        "personal_relevance_score": "1-10，对个人 AI/Agent/工具链/半导体/端侧智能情报系统的相关性。",
        "actionability_score": "1-10，是否值得今天试用、归档、跟踪、深入研究或调整工作流。",
        "confidence_score": "1-10，基于来源和内容完整度的判断信心。社区传言和信息不足要低分。",
        "content_type": "major_release / minor_release / research / benchmark / community_discussion / funding_rumor / business_signal / tutorial / marketing / event / other",
        "risk_level": "official_confirmed / community_discussed / early_signal / needs_verification",
        "decision": "include / maybe / exclude",
        "reason_zh": "用 1-2 句中文说明为什么值得或不值得进入日报。"
    }
    return (
        "请根据编辑政策评审下面这条候选信息是否值得进入今天的 AI 情报日报。\n"
        "注意：关键词只代表召回，不代表价值；请重点判断新闻价值、个人相关性、可行动性和可信风险。\n"
        f"编辑政策：{json.dumps(editorial_policy, ensure_ascii=False)}\n"
        f"目标 JSON 字段：{json.dumps(schema, ensure_ascii=False)}\n"
        f"候选信息：{json.dumps(payload, ensure_ascii=False)}"
    )


def _validate_result(result: dict[str, Any]) -> dict[str, Any]:
    def score(name: str, default: int = 1) -> int:
        try:
            value = int(float(result.get(name, default)))
        except (TypeError, ValueError):
            value = default
        return max(1, min(10, value))

    decision = str(result.get("decision") or "maybe").strip().lower()
    if decision not in {"include", "maybe", "exclude"}:
        decision = "maybe"
    risk_level = str(result.get("risk_level") or "needs_verification").strip()
    if risk_level not in {"official_confirmed", "community_discussed", "early_signal", "needs_verification"}:
        risk_level = "needs_verification"
    return {
        "newsworthiness_score": score("newsworthiness_score"),
        "personal_relevance_score": score("personal_relevance_score"),
        "actionability_score": score("actionability_score"),
        "confidence_score": score("confidence_score"),
        "content_type": normalize_space(str(result.get("content_type") or "other"))[:80],
        "risk_level": risk_level,
        "decision": decision,
        "reason_zh": normalize_space(str(result.get("reason_zh") or "模型未给出明确理由"))[:260],
    }


def _calculate_editorial_score(item: dict[str, Any]) -> int:
    editorial = item.get("editorial") or {}
    source_trust = int(item.get("source_trust_score", 0))
    newsworthiness = int(editorial.get("newsworthiness_score", 1))
    relevance = int(editorial.get("personal_relevance_score", 1))
    actionability = int(editorial.get("actionability_score", 1))
    confidence = int(editorial.get("confidence_score", 1))
    decision = editorial.get("decision")
    decision_bonus = {"include": 8, "maybe": 0, "exclude": -25}.get(decision, 0)
    return round(
        source_trust * 0.25
        + newsworthiness * 10 * 0.35
        + relevance * 10 * 0.25
        + actionability * 10 * 0.10
        + confidence * 10 * 0.05
        + decision_bonus
    )
