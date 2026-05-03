from __future__ import annotations

from datetime import datetime
from typing import Any

from utils import format_local_time


LEVEL_LABELS = {
    "official_confirmed": "官方确认",
    "tech_community": "技术社区",
    "early_signal": "早期信号",
    "needs_verification": "待验证",
}

TYPE_LABELS = {
    "rss": "RSS",
    "github_release": "GitHub 发布",
    "hackernews": "Hacker News",
}


def _read_hint(level: str) -> str:
    if level == "official_confirmed":
        return "优先读原文。这类信息来自官方或项目发布页，适合作为事实依据。"
    if level == "tech_community":
        return "适合观察技术圈关注点，但不等于事实确认，建议结合原文和官方来源判断。"
    if level == "early_signal":
        return "适合捕捉趋势苗头，但尚未看到官方确认，不建议直接当成结论。"
    return "信息仍需核验。建议先看原文，再决定是否继续追踪。"


def _section_title(levels: tuple[str, ...]) -> str:
    if levels == ("official_confirmed",):
        return "一、优先看：官方确认与项目发布"
    if levels == ("tech_community",):
        return "二、技术社区正在讨论"
    return "三、早期信号与待验证信息"


def _section_intro(levels: tuple[str, ...]) -> str:
    if levels == ("official_confirmed",):
        return "这一部分可信度最高，适合先读。仍建议点开原文确认细节和上下文。"
    if levels == ("tech_community",):
        return "这一部分反映社区热度和工程师关注点，可以用来发现趋势，但不能直接当作事实结论。"
    return "这一部分只作为线索池，适合收藏观察，不适合直接转述为确定消息。"


def _one_line_reason(item: dict[str, Any]) -> str:
    level = item.get("source_level", "needs_verification")
    source_type = item.get("source_type", "")
    keywords = item.get("matched_keywords") or []
    keyword_text = "、".join(keywords[:4])
    if level == "official_confirmed":
        prefix = "来自官方或项目发布渠道"
    elif level == "tech_community":
        prefix = "来自技术社区讨论"
    elif level == "early_signal":
        prefix = "属于早期趋势线索"
    else:
        prefix = "来源仍需进一步核验"
    if source_type == "hackernews" and item.get("hn_score") is not None:
        return f"{prefix}，HN 热度 {item.get('hn_score')} 分，建议结合原文判断。"
    if keyword_text:
        return f"{prefix}，命中 {keyword_text} 等关键词，值得快速浏览。"
    return f"{prefix}，建议先看标题和原文链接，再决定是否深入阅读。"


def _render_item(index: int, item: dict[str, Any]) -> str:
    source_type = item.get("source_type", "")
    level_label = LEVEL_LABELS.get(item.get("source_level"), "待验证")
    source_name = item.get("source_name") or "未知来源"
    type_label = TYPE_LABELS.get(source_type, source_type or "未知")
    matched = "、".join(item.get("matched_keywords") or []) or "无"
    lines = [
        f"### {index}. {item.get('title') or '无标题'}",
        "",
        f"**判断：{level_label}｜{source_name}｜{type_label}｜规则分 {item.get('score', 0)}**",
        "",
        f"- 为什么值得看：{_one_line_reason(item)}",
        f"- 发布时间：{format_local_time(item.get('published_at'))}",
        f"- 原文链接：{item.get('url') or '无链接'}",
        f"- 命中关键词：{matched}",
    ]
    if source_type == "hackernews" and item.get("hn_score") is not None:
        lines.append(f"- HN 分数：{item.get('hn_score')}")
    lines.extend(
        [
            "- 原文摘录：",
            f"  > {item.get('summary_or_excerpt') or '暂无摘要，请查看原文。'}",
            "",
            f"- 阅读提醒：{_read_hint(item.get('source_level', 'needs_verification'))}",
            "",
            "---",
        ]
    )
    return "\n".join(lines)


def generate_markdown(items: list[dict[str, Any]], total_count: int, max_items: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 每日 AI 早报｜{today}",
        "",
        "## 先说结论",
        "",
        f"今天自动抓取 {total_count} 条信息，按来源可信度、关键词和规则分数筛出 {min(max_items, len(items))} 条。",
        "阅读顺序建议：先看官方确认和项目发布，再看社区热议，最后把早期信号当作观察线索。",
        "",
        "## 标签说明",
        "",
        "- 官方确认：公司官方博客、官方 changelog、论文源或开源项目发布页，可信度较高。",
        "- 技术社区：Hacker News、Reddit、技术博客等，适合看热度和工程讨论。",
        "- 早期信号 / 待验证：适合发现苗头，但需要等待官方或多来源确认。",
        "",
    ]
    if not items:
        lines.extend(
            [
                "## 今日内容",
                "",
                "今天没有筛选出符合时间窗口和规则的新闻。请检查来源配置或稍后重新运行。",
                "",
            ]
        )

    index = 1
    sections = [
        ("official_confirmed",),
        ("tech_community",),
        ("early_signal", "needs_verification"),
    ]
    for section_levels in sections:
        section_items = [item for item in items if item.get("source_level") in section_levels]
        if not section_items:
            continue
        lines.extend([f"## {_section_title(section_levels)}", "", _section_intro(section_levels), ""])
        for item in section_items:
            lines.append(_render_item(index, item))
            lines.append("")
            index += 1

    lines.extend(
        [
            "## 阅读原则",
            "",
            "这份早报只做自动抓取、分级、打分和排序，不把自动化摘录当成最终事实。",
            "重要信息请优先查看官方来源和原文链接。",
            "社区热议和早期信号只用于发现趋势，不直接作为事实依据。",
            "",
        ]
    )
    return "\n".join(lines)
