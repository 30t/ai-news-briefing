from __future__ import annotations

from datetime import datetime
from typing import Any

from utils import LOCAL_TIMEZONE, format_local_time, normalize_space, strip_html


LEVEL_LABELS = {
    "official_confirmed": "官方确认",
    "tech_community": "技术社区",
    "early_signal": "早期信号",
    "needs_verification": "待验证",
}

RISK_LABELS = {
    "official_confirmed": "官方确认",
    "community_discussed": "社区讨论",
    "early_signal": "早期信号",
    "needs_verification": "待验证",
}

TYPE_LABELS = {
    "rss": "RSS",
    "github_release": "GitHub Releases",
    "hackernews": "Hacker News",
}


def _read_hint(level: str) -> str:
    if level == "official_confirmed":
        return "来自官方或项目发布渠道，可信度较高，但仍建议查看原文确认细节。"
    if level == "tech_community":
        return "来自技术社区，适合观察讨论热度，不等于事实确认。"
    if level == "early_signal":
        return "属于早期研究或趋势信号，适合收藏观察，不建议直接当成确定结论。"
    return "信息仍需核验，请优先查看原文链接。"


def _excerpt(item: dict[str, Any], limit: int = 420) -> str:
    text = strip_html(item.get("summary_or_excerpt") or "")
    text = normalize_space(text)
    if not text:
        if item.get("source_type") == "hackernews" and item.get("hn_score") is not None:
            return f"Hacker News 讨论，HN 分数 {item.get('hn_score')}。"
        return "暂无 feed 摘要，请查看原文。"
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _why_selected(item: dict[str, Any]) -> str:
    editorial = item.get("editorial") or {}
    reason = editorial.get("reason_zh")
    if reason:
        return str(reason)

    level = item.get("source_level", "needs_verification")
    keywords = item.get("matched_keywords") or []
    keyword_text = "、".join(keywords[:4])
    if level == "official_confirmed":
        prefix = "来源可靠性较高"
    elif level == "tech_community":
        prefix = "社区热度或讨论价值较高"
    elif level == "early_signal":
        prefix = "可作为早期研究或趋势线索"
    else:
        prefix = "需要进一步核验"
    if item.get("source_type") == "hackernews" and item.get("hn_score") is not None:
        return f"{prefix}，HN 分数 {item.get('hn_score')}。"
    if keyword_text:
        return f"{prefix}，命中 {keyword_text} 等关键词。"
    return f"{prefix}，由规则召回分进入候选池。"


def _render_editorial_fields(item: dict[str, Any]) -> list[str]:
    editorial = item.get("editorial") or {}
    if not editorial:
        return []
    risk = RISK_LABELS.get(editorial.get("risk_level"), editorial.get("risk_level", "未知"))
    return [
        f"- 模型编辑分：{item.get('editorial_score', item.get('score', 0))}",
        f"- 编辑决策：{editorial.get('decision', '未知')}",
        f"- 内容类型：{editorial.get('content_type', 'other')}",
        f"- 风险等级：{risk}",
        "- 模型分项："
        f" 新闻价值 {editorial.get('newsworthiness_score', '未知')}/10；"
        f"个人相关性 {editorial.get('personal_relevance_score', '未知')}/10；"
        f"可行动性 {editorial.get('actionability_score', '未知')}/10；"
        f"判断信心 {editorial.get('confidence_score', '未知')}/10",
    ]


def _render_reusable_llm_fields(item: dict[str, Any]) -> list[str]:
    llm = item.get("llm") or {}
    fields = [
        ("模型中文标题", llm.get("final_title_zh")),
        ("模型背景", llm.get("background_zh")),
        ("模型核心摘要", llm.get("core_summary_zh")),
        ("模型证据说明", llm.get("evidence_or_result_zh")),
        ("模型重要性", llm.get("why_it_matters_zh")),
        ("模型建议动作", llm.get("reader_action_zh")),
    ]
    lines: list[str] = []
    for label, value in fields:
        text = normalize_space(str(value or ""))
        if text:
            lines.append(f"- {label}：{text}")
    return lines


def _render_item(index: int, item: dict[str, Any]) -> str:
    source_type = item.get("source_type", "")
    level_label = LEVEL_LABELS.get(item.get("source_level"), "待验证")
    source_name = item.get("source_name") or "未知来源"
    type_label = TYPE_LABELS.get(source_type, source_type or "未知")
    channel_label = "发布渠道" if source_type == "github_release" else "来源类型"
    matched = "、".join(item.get("matched_keywords") or []) or "无"

    lines = [
        f"### {index}. {item.get('title') or '无标题'}",
        "",
        f"- 来源等级：{level_label}",
        f"- 来源名称：{source_name}",
        f"- {channel_label}：{type_label}",
        f"- 发布时间：{format_local_time(item.get('published_at'))}",
        f"- 原文链接：{item.get('url') or '无链接'}",
        f"- 命中关键词：{matched}",
        f"- 来源可信分：{item.get('source_trust_score', '未知')}",
        f"- 关键词召回分：{item.get('keyword_relevance_score', '未知')}",
        f"- 规则召回分：{item.get('rule_relevance_score', item.get('score', 0))}",
    ]
    lines.extend(_render_editorial_fields(item))
    lines.extend(_render_reusable_llm_fields(item))
    if source_type == "hackernews" and item.get("hn_score") is not None:
        lines.append(f"- HN 分数：{item.get('hn_score')}")
    lines.extend(
        [
            f"- 入选原因：{_why_selected(item)}",
            "- Feed 摘要：",
            f"  > {_excerpt(item)}",
            f"- 阅读提醒：{_read_hint(item.get('source_level', 'needs_verification'))}",
            "",
            "---",
        ]
    )
    return "\n".join(lines)


def generate_markdown(items: list[dict[str, Any]], total_count: int, max_items: int) -> str:
    today = datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d")
    selected_count = min(max_items, len(items))
    lines = [
        f"# 每日 AI 情报候选池｜{today}",
        "",
        "## 今日概况",
        "",
        f"今天自动抓取 {total_count} 条信息，系统先按时间窗口过滤，再用来源等级、关键词和噪声规则形成候选池，最后由模型编辑评审排序出 {selected_count} 条。",
        "本文件保留原文链接、来源等级、关键词召回信息、模型编辑分、模型入选理由和模型单条解释字段。关键词只负责召回，不代表新闻价值。",
        "",
        "## 判断标签",
        "",
        "- 官方确认：公司官方博客、官方 changelog 或开源项目发布页。",
        "- 技术社区：Hacker News、Reddit、技术博客等，适合观察讨论热度。",
        "- 早期信号：arXiv 论文、早期研究动态或仍需进一步观察的信息。",
        "- 待验证：来源不够明确或需要进一步核验的信息。",
        "",
        "## 排序逻辑",
        "",
        "- 关键词召回分：只表示是否可能相关，不等于新闻价值。",
        "- 来源可信分：提供可信度底座，但官方小更新也可能低价值。",
        "- 模型编辑分：综合新闻价值、个人相关性、可行动性、判断信心和入选决策。",
        "- 最终 Top 列表按模型编辑分排序。",
        "",
    ]
    if not items:
        lines.extend(
            [
                "## 今日 Top 0",
                "",
                "今天没有筛选出符合时间窗口和规则的新闻。请检查来源配置或稍后重新运行。",
                "",
            ]
        )
    else:
        lines.extend([f"## 今日 Top {selected_count}", "", "以下内容按模型编辑分排序展示。", ""])
        for index, item in enumerate(items, start=1):
            lines.append(_render_item(index, item))
            lines.append("")

    lines.extend(
        [
            "## 本系统的判断原则",
            "",
            "这份候选池先用规则保证可追溯召回，再用模型编辑评审判断是否值得阅读。",
            "它不把关键词命中当成重要性，也不把社区讨论当成官方确认。",
            "重要信息请优先查看原文链接，并结合来源等级、模型风险等级、模型分项和入选理由判断阅读优先级。",
            "",
        ]
    )
    return "\n".join(lines)
