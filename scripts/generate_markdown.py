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
    "github_release": "GitHub Release",
    "hackernews": "Hacker News",
}


def _read_hint(level: str) -> str:
    if level == "official_confirmed":
        return "这是官方来源，可信度较高。"
    if level == "tech_community":
        return "这是社区讨论，不等于事实确认，需要结合原文判断。"
    if level == "early_signal":
        return "该信息属于早期信号，尚未看到官方确认，请谨慎判断。"
    return "该信息仍需进一步核验，请优先查看原文链接。"


def _section_title(levels: tuple[str, ...]) -> str:
    if levels == ("official_confirmed",):
        return "今日优先阅读"
    if levels == ("tech_community",):
        return "技术社区热议"
    return "早期信号 / 待验证"


def _render_item(index: int, item: dict[str, Any]) -> str:
    source_type = item.get("source_type", "")
    lines = [
        f"### {index}. {item.get('title') or '无标题'}",
        "",
        f"- 来源等级：{LEVEL_LABELS.get(item.get('source_level'), '待验证')}",
        f"- 来源：{item.get('source_name') or '未知来源'}",
        f"- 类型：{TYPE_LABELS.get(source_type, source_type or '未知')}",
        f"- 发布时间：{format_local_time(item.get('published_at'))}",
        f"- 原文链接：{item.get('url') or '无链接'}",
    ]
    if source_type == "hackernews" and item.get("hn_score") is not None:
        lines.append(f"- HN 分数：{item.get('hn_score')}")
    matched = ", ".join(item.get("matched_keywords") or []) or "无"
    lines.extend(
        [
            f"- 命中关键词：{matched}",
            f"- 规则分数：{item.get('score', 0)}",
            "- 原文摘录：",
            f"  > {item.get('summary_or_excerpt') or '暂无摘要，请查看原文。'}",
            "",
            "- 阅读提醒：",
            f"  {_read_hint(item.get('source_level', 'needs_verification'))}",
            "",
            "---",
        ]
    )
    return "\n".join(lines)


def generate_markdown(items: list[dict[str, Any]], total_count: int, max_items: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# AI 早报｜{today}",
        "",
        "## 今日一句话",
        "",
        f"今天共抓取 {total_count} 条信息，筛选出 Top {min(max_items, len(items))} 条。优先展示官方确认来源，其次是技术社区热议和早期信号。",
        "",
    ]
    if not items:
        lines.extend(
            [
                "## 今日优先阅读",
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
        lines.extend([f"## {_section_title(section_levels)}", ""])
        for item in section_items:
            lines.append(_render_item(index, item))
            lines.append("")
            index += 1

    lines.extend(
        [
            "## 本系统的判断原则",
            "",
            "本简报不把自动化摘要视为最终事实。",
            "请优先查看官方来源和原文链接。",
            "社区热议和早期信号仅用于发现趋势，不直接作为事实依据。",
            "",
        ]
    )
    return "\n".join(lines)
