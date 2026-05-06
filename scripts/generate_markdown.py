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
    return f"{prefix}，由规则分数进入今日列表。"


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
        f"- 规则分数：{item.get('score', 0)}",
    ]
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
        f"# 每日 AI 新闻规则简报｜{today}",
        "",
        "## 今日概况",
        "",
        f"今天自动抓取 {total_count} 条信息，系统先按时间窗口保留候选信息，再根据关键词命中、来源等级、规则分数和去重规则筛出 {selected_count} 条。",
        "本文件不调用任何模型 API，不生成模型总结，只保留规则判断、feed 摘要和原文链接。",
        "",
        "## 判断标签",
        "",
        "- 官方确认：公司官方博客、官方 changelog 或开源项目发布页。",
        "- 技术社区：Hacker News、Reddit、技术博客等，适合观察讨论热度。",
        "- 早期信号：arXiv 论文、早期研究动态或仍需进一步观察的信息。",
        "- 待验证：来源不够明确或需要进一步核验的信息。",
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
        lines.extend([f"## 今日 Top {selected_count}", "", "以下内容按综合规则分数排序展示。", ""])
        for index, item in enumerate(items, start=1):
            lines.append(_render_item(index, item))
            lines.append("")

    lines.extend(
        [
            "## 本系统的判断原则",
            "",
            "这份简报只做自动抓取、来源分级、关键词匹配、规则打分、去重、排序和 Markdown 输出。",
            "它不把自动化摘录当成最终事实，也不把社区讨论当成官方确认。",
            "重要信息请优先查看原文链接，并结合来源等级、命中关键词和规则分数判断可信度与阅读优先级。",
            "",
        ]
    )
    return "\n".join(lines)
