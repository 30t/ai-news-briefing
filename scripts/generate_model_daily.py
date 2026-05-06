from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from summarize_with_llm import get_api_key
from utils import LOCAL_TIMEZONE, format_local_time, normalize_space, strip_html


LEVEL_LABELS = {
    "official_confirmed": "官方确认",
    "tech_community": "技术社区",
    "early_signal": "早期信号",
    "needs_verification": "待验证",
}

TAG_LABELS = {
    "model": "模型与 AI 公司",
    "agent": "Agent 与工作流",
    "coding_tool": "编程工具",
    "ai_app": "AI 应用平台",
    "rag_data": "RAG 与数据栈",
    "open_source": "开源基础设施",
    "semiconductor": "算力与半导体",
    "business": "商业产品与政策",
}

SYSTEM_PROMPT = """你是一个中文 AI 新闻主编。
你的任务是把输入的 Top 候选信息池，整理成一份“可听、可读、可行动”的 AI 新闻模型解读日报。

必须遵守：
1. 只基于输入内容写作，不编造原文没有的信息。
2. 不要逐条机械复述所有候选新闻，要综合、分组、统计和提炼。
3. 所有重要判断必须保留来源索引，例如 [1]、[2]、[7]。
4. 官方确认、技术社区、早期信号、待验证必须区分清楚。
5. arXiv / 论文 / benchmark 只能作为“前沿研究观察”，不许写成已产品化事实。
6. 社区来源必须标注“社区讨论，不等于官方确认”。
7. GitHub Release 可以归纳成“开源工具链更新”，不需要每条小版本都展开。
8. 语言要清楚、干练，像“新闻播报 + 科技解释员”，不要论文腔，不要营销夸张。
9. 输出只能是 Markdown，不要代码块。
"""

REQUIRED_SECTIONS = [
    "## 今日一句话",
    "## 今日最重要 5 条",
    "## 工具链更新汇总",
    "## Agent / 编程工具趋势",
    "## 开源项目 Release 汇总",
    "## 企业应用 / 商业化信号",
    "## 算力 / 半导体观察",
    "## 前沿研究观察",
    "## 今日建议动作",
    "## 附录：候选来源索引",
]


def generate_model_daily(
    items: list[dict[str, Any]],
    total_count: int,
    scoring_config: dict[str, Any],
    llm_config: dict[str, Any],
) -> str | None:
    if not llm_config.get("enabled", False):
        logging.info("Model daily skipped: LLM disabled.")
        return None
    api_key = get_api_key(llm_config)
    if not api_key:
        logging.warning("Model daily skipped: missing API key env %s.", llm_config.get("api_key_env", "LLM_API_KEY"))
        return None

    selected = select_items_for_model_daily(items, scoring_config, llm_config)
    if not selected:
        logging.warning("Model daily skipped: no selected items.")
        return None

    try:
        return _generate_with_llm(selected, total_count, llm_config, api_key)
    except Exception as exc:  # noqa: BLE001 - raw daily should still be produced.
        logging.warning("Model daily generation fell back to rule renderer: %s", exc)
        if llm_config.get("fallback_on_error", True):
            return _generate_rule_based(selected, total_count)
        return None


def select_items_for_model_daily(
    items: list[dict[str, Any]],
    scoring_config: dict[str, Any],
    llm_config: dict[str, Any],
) -> list[dict[str, Any]]:
    pool_size = int(llm_config.get("model_daily_candidate_pool_size", scoring_config.get("max_items_per_day", 40)))
    max_items = int(llm_config.get("model_daily_max_items", 18))
    pool = [item for item in items[:pool_size] if _is_meaningful_for_model_daily(item)]

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(candidates: list[dict[str, Any]], limit: int) -> None:
        added = 0
        for item in candidates:
            if len(selected) >= max_items or added >= limit:
                break
            key = item.get("url") or item.get("title") or ""
            if not key or key in seen:
                continue
            selected.append(item)
            seen.add(key)
            added += 1

    official = [item for item in pool if item.get("source_level") == "official_confirmed"]
    community = [item for item in pool if item.get("source_level") == "tech_community"]
    early = [item for item in pool if item.get("source_level") == "early_signal"]
    needs_check = [item for item in pool if item.get("source_level") == "needs_verification"]

    agent_or_coding = [item for item in pool if _has_any_tag(item, {"agent", "coding_tool"})]
    app_or_rag = [item for item in pool if _has_any_tag(item, {"ai_app", "rag_data", "open_source"})]
    business_or_chip = [item for item in pool if _has_any_tag(item, {"business", "semiconductor"})]

    add(agent_or_coding, 5)
    add(app_or_rag, 5)
    add(official, 6)
    add(business_or_chip, 4)
    add(community, 3)
    add(early, 2)
    add(needs_check, 1)
    add(pool, max_items - len(selected))

    return selected[:max_items]


def _generate_with_llm(items: list[dict[str, Any]], total_count: int, config: dict[str, Any], api_key: str) -> str:
    base_url = str(config.get("base_url") or "https://api.deepseek.com").rstrip("/")
    payload = {
        "model": config.get("model", "deepseek-chat"),
        "temperature": float(config.get("model_daily_temperature", 0.25)),
        "max_tokens": int(config.get("model_daily_max_output_tokens", 6200)),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(items, total_count)},
        ],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-news-briefing/model-daily",
        },
        method="POST",
    )
    timeout = int(config.get("model_daily_timeout_seconds", 80))
    max_retries = int(config.get("model_daily_max_retries", 1))
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("empty model daily response")
            return _ensure_required_sections(content, items, total_count)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if attempt >= max_retries:
                raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
        except Exception:
            if attempt >= max_retries:
                raise
        time.sleep(1 + attempt)
    raise RuntimeError("model daily generation failed")


def _build_prompt(items: list[dict[str, Any]], total_count: int) -> str:
    today = datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d")
    stats = _build_stats(items, total_count)
    payload = {
        "date": today,
        "total_fetched": total_count,
        "selected_count": len(items),
        "required_title": f"# AI 新闻模型解读日报｜{today}",
        "required_sections": REQUIRED_SECTIONS,
        "source_level_stats": stats["source_level_stats"],
        "tag_stats": stats["tag_stats"],
        "items": [_serialize_item(index, item) for index, item in enumerate(items, 1)],
    }
    return (
        "请根据下面 JSON 写一份固定结构 Markdown 日报。\n"
        "结构必须完整包含：\n"
        "# AI 新闻模型解读日报｜YYYY-MM-DD\n"
        + "\n".join(REQUIRED_SECTIONS)
        + "\n\n写作要求：\n"
        "- 不要逐条复述所有 items。\n"
        "- 今日最重要 5 条必须每条都带来源索引。\n"
        "- 工具链 / Agent / 开源 release 可以合并同类项。\n"
        "- 附录要列出候选来源索引，包含编号、标题、来源等级、来源名称和链接。\n"
        "- 对早期信号要写清楚：这是研究或早期线索，不等于已经产品化。\n"
        "- 对技术社区要写清楚：社区讨论，不等于官方确认。\n\n"
        f"输入 JSON：{json.dumps(payload, ensure_ascii=False)}"
    )


def _serialize_item(index: int, item: dict[str, Any]) -> dict[str, Any]:
    llm = item.get("llm") or {}
    excerpt = strip_html(item.get("article_text") or item.get("summary_or_excerpt") or "")
    return {
        "id": index,
        "title": item.get("title"),
        "llm_title": llm.get("final_title_zh"),
        "llm_summary": llm.get("core_summary_zh"),
        "llm_why_it_matters": llm.get("why_it_matters_zh"),
        "source_name": item.get("source_name"),
        "source_type": item.get("source_type"),
        "source_level": item.get("source_level"),
        "source_level_zh": LEVEL_LABELS.get(item.get("source_level"), "待验证"),
        "published_at": format_local_time(item.get("published_at")),
        "url": item.get("url"),
        "score": item.get("score"),
        "hn_score": item.get("hn_score"),
        "matched_keywords": item.get("matched_keywords") or [],
        "tags": item.get("tags") or [],
        "tags_zh": [TAG_LABELS.get(tag, tag) for tag in item.get("tags") or []],
        "excerpt": excerpt[:1200],
    }


def _ensure_required_sections(content: str, items: list[dict[str, Any]], total_count: int) -> str:
    today = datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d")
    cleaned = content.strip()
    cleaned = cleaned.removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
    if not cleaned.startswith("# AI 新闻模型解读日报"):
        cleaned = f"# AI 新闻模型解读日报｜{today}\n\n{cleaned}"
    missing = [section for section in REQUIRED_SECTIONS if section not in cleaned]
    if missing:
        logging.warning("Model daily response missed sections: %s", ", ".join(missing))
        return _generate_rule_based(items, total_count)
    return cleaned + "\n"


def _generate_rule_based(items: list[dict[str, Any]], total_count: int) -> str:
    today = datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d")
    stats = _build_stats(items, total_count)
    lines = [
        f"# AI 新闻模型解读日报｜{today}",
        "",
        "## 今日一句话",
        "",
        f"今天规则层共抓取 {total_count} 条信息，模型层选取 {len(items)} 条高价值候选信息做综合整理。",
        "",
        "## 今日最重要 5 条",
        "",
    ]
    for index, item in enumerate(items[:5], 1):
        lines.extend([
            f"### {index}. {_display_title(item)}",
            "",
            f"- 来源索引：[{index}]",
            f"- 来源等级：{LEVEL_LABELS.get(item.get('source_level'), '待验证')}",
            f"- 为什么重要：{_why_it_matters(item)}",
            f"- 原文链接：{item.get('url')}",
            "",
        ])
    section_map = [
        ("## 工具链更新汇总", {"ai_app", "rag_data"}),
        ("## Agent / 编程工具趋势", {"agent", "coding_tool"}),
        ("## 开源项目 Release 汇总", {"open_source"}),
        ("## 企业应用 / 商业化信号", {"business"}),
        ("## 算力 / 半导体观察", {"semiconductor"}),
        ("## 前沿研究观察", set()),
    ]
    for title, tags in section_map:
        lines.extend([title, ""])
        candidates = [item for item in items if _has_any_tag(item, tags)] if tags else [item for item in items if item.get("source_level") == "early_signal"]
        if not candidates:
            lines.extend(["今天没有足够明确的同类信号。", ""])
            continue
        for item in candidates[:4]:
            lines.append(f"- [{items.index(item) + 1}] {_display_title(item)}：{_why_it_matters(item)}")
        lines.append("")
    lines.extend([
        "## 今日建议动作",
        "",
        "1. 先打开官方确认来源，核验产品入口、版本号和适用范围。",
        "2. 对 GitHub Release 集中看项目级变化，不必被小版本刷屏牵着走。",
        "3. 对社区与早期研究保持观察，不直接当成事实或可用产品。",
        "",
        "## 附录：候选来源索引",
        "",
        f"- 来源等级统计：{stats['source_level_stats']}",
        f"- 标签统计：{stats['tag_stats']}",
        "",
    ])
    for index, item in enumerate(items, 1):
        lines.append(f"- [{index}] {_display_title(item)}｜{LEVEL_LABELS.get(item.get('source_level'), '待验证')}｜{item.get('source_name')}｜{item.get('url')}")
    lines.append("")
    return "\n".join(lines)


def _build_stats(items: list[dict[str, Any]], total_count: int) -> dict[str, Any]:
    source_level_stats: dict[str, int] = {}
    tag_stats: dict[str, int] = {}
    for item in items:
        level = str(item.get("source_level") or "needs_verification")
        source_level_stats[LEVEL_LABELS.get(level, level)] = source_level_stats.get(LEVEL_LABELS.get(level, level), 0) + 1
        for tag in item.get("tags") or []:
            label = TAG_LABELS.get(tag, str(tag))
            tag_stats[label] = tag_stats.get(label, 0) + 1
    return {"total_fetched": total_count, "source_level_stats": source_level_stats, "tag_stats": tag_stats}


def _is_meaningful_for_model_daily(item: dict[str, Any]) -> bool:
    if item.get("source_level") in {"official_confirmed", "tech_community"}:
        return True
    if item.get("source_level") == "early_signal":
        return _has_any_tag(item, {"agent", "coding_tool", "ai_app", "rag_data", "open_source", "semiconductor"})
    return bool(item.get("matched_keywords"))


def _has_any_tag(item: dict[str, Any], tags: set[str]) -> bool:
    return bool(set(item.get("tags") or []).intersection(tags))


def _display_title(item: dict[str, Any]) -> str:
    llm = item.get("llm") or {}
    return llm.get("final_title_zh") or item.get("title") or "无标题"


def _why_it_matters(item: dict[str, Any]) -> str:
    llm = item.get("llm") or {}
    if llm.get("why_it_matters_zh"):
        return str(llm["why_it_matters_zh"])
    keywords = "、".join((item.get("matched_keywords") or [])[:4]) or "相关方向"
    return f"命中 {keywords}，规则分数 {item.get('score', 0)}。"
