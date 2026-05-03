from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from utils import format_local_time, normalize_space, strip_html


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

GLOSSARY = {
    "Claude Desktop": "Claude 桌面版",
    "Claude Code": "Claude Code 编程工具",
    "GitHub Release": "GitHub 发布",
    "Hacker News": "Hacker News 技术社区",
    "open source": "开源",
    "OpenAI": "OpenAI",
    "Anthropic": "Anthropic",
    "DeepMind": "DeepMind",
    "Meta AI": "Meta AI",
    "benchmark": "基准测试",
    "release": "发布",
    "pricing": "定价",
    "API": "API",
    "agent": "智能体",
    "Agent": "智能体",
    "coding": "编程",
    "workflow": "工作流",
    "automation": "自动化",
    "inference": "推理",
    "fine-tuning": "微调",
    "model": "模型",
    "models": "模型",
    "GPU": "GPU",
    "CUDA": "CUDA",
    "semiconductor": "半导体",
    "funding": "融资",
    "startup": "创业公司",
    "partnership": "合作",
    "enterprise": "企业",
    "productivity": "生产力",
}


def _split_sentences(text: str) -> list[str]:
    cleaned = _clean_excerpt_text(text)
    if not cleaned:
        return []
    chunks = re.split(r"(?<=[.!?。！？])\s+|\n+", cleaned)
    sentences = []
    for chunk in chunks:
        sentence = chunk.strip(" -•*")
        if len(sentence) < 24:
            continue
        if sentence.lower().startswith(("comments:", "hn points:")):
            continue
        if len(re.findall(r"https?://", sentence)) >= 2:
            continue
        sentences.append(sentence)
    return sentences


def _clean_excerpt_text(text: str) -> str:
    cleaned = strip_html(text)
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"#+\s*", " ", cleaned)
    cleaned = re.sub(r"\s+[-*]\s+", ". ", cleaned)
    if "What's Changed" in cleaned:
        cleaned = cleaned.split("What's Changed", 1)[0]
    if "macOS/iOS:" in cleaned:
        cleaned = cleaned.split("macOS/iOS:", 1)[0]
    return normalize_space(cleaned)


def _sentence_score(sentence: str, item: dict[str, Any]) -> int:
    lower = sentence.lower()
    score = 0
    for keyword in item.get("matched_keywords") or []:
        if str(keyword).lower() in lower:
            score += 8
    title_words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9.+#-]{2,}", item.get("title", "").lower())
    for word in set(title_words):
        if word in lower:
            score += 2
    signal_words = (
        "release",
        "launched",
        "announced",
        "supports",
        "now",
        "new",
        "benchmark",
        "performance",
        "pricing",
        "api",
        "model",
        "open source",
        "github",
        "gpu",
        "cuda",
    )
    for word in signal_words:
        if word in lower:
            score += 3
    if 60 <= len(sentence) <= 260:
        score += 4
    if sentence.startswith(("http://", "https://")):
        score -= 8
    if len(re.findall(r"https?://", sentence)) >= 2:
        score -= 8
    return score


def _core_excerpt(item: dict[str, Any], limit: int = 520) -> str:
    if item.get("source_type") == "hackernews":
        hn_score = item.get("hn_score")
        if hn_score is not None:
            return f"Hacker News discussion: {item.get('title', 'Untitled')}. HN points: {hn_score}."
        return f"Hacker News discussion: {item.get('title', 'Untitled')}."
    raw = item.get("summary_or_excerpt") or ""
    sentences = _split_sentences(raw)
    if not sentences:
        return "暂无摘要，请查看原文。"
    ranked = sorted(enumerate(sentences), key=lambda pair: _sentence_score(pair[1], item), reverse=True)
    selected_indexes = sorted(index for index, _sentence in ranked[:2])
    selected = " ".join(sentences[index] for index in selected_indexes)
    selected = normalize_space(selected)
    if len(selected) <= limit:
        return selected
    return selected[: limit - 1].rstrip() + "..."


def _rule_based_translation(text: str, item: dict[str, Any]) -> str:
    if not text or text == "暂无摘要，请查看原文。":
        return "暂无可翻译摘要，请查看原文。"
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    translated_sentences = []
    for sentence in _split_sentences(text) or [text]:
        translated_sentences.append(_translate_sentence(sentence, item))
    return normalize_space(" ".join(translated_sentences))


def _translate_sentence(sentence: str, item: dict[str, Any]) -> str:
    if sentence.startswith("Hacker News discussion:"):
        title = item.get("title") or sentence.replace("Hacker News discussion:", "").strip()
        hn_score = item.get("hn_score")
        if hn_score is not None:
            return f"Hacker News 上关于《{title}》的讨论，当前热度约 {hn_score} 分。"
        return f"Hacker News 上关于《{title}》的讨论。"
    patterns = [
        (
            r"Both (?P<a>.+?) and (?P<b>.+?) are supported within the (?P<c>.+?) App\.?$",
            lambda match: f"{match.group('c')} 应用内已经支持 {match.group('a')} 和 {match.group('b')}。",
        ),
        (
            r"(?P<a>.+?) on the terminal can still be accessed through the CLI with:?\s*(?P<cmd>.*?)\.?$",
            lambda match: f"终端里的 {match.group('a')} 仍可通过 CLI{(' 命令 ' + match.group('cmd')) if match.group('cmd') else ''} 访问。",
        ),
        (
            r"(?P<a>.+?) on the terminal can still be accessed through the CLI\.?$",
            lambda match: f"终端里的 {match.group('a')} 仍可通过 CLI 访问。",
        ),
        (
            r"(?P<a>.+?) is now supported with (?P<b>.+?)\.?$",
            lambda match: f"{match.group('a')} 现在可通过 {match.group('b')} 支持。",
        ),
        (
            r"(?P<a>.+?) now supports (?P<b>.+?)\.?$",
            lambda match: f"{match.group('a')} 现在支持 {match.group('b')}。",
        ),
        (
            r"(?P<a>.+?) supports (?P<b>.+?)\.?$",
            lambda match: f"{match.group('a')} 支持 {match.group('b')}。",
        ),
        (
            r"fix:\s*(?P<a>.+)$",
            lambda match: f"修复：{match.group('a')}。",
        ),
        (
            r"(?P<a>.+?) beats (?P<b>.+?) in (?P<c>.+?)\.?$",
            lambda match: f"{match.group('a')} 在 {match.group('c')} 中超过了 {match.group('b')}。",
        ),
        (
            r"(?P<a>.+?) is the best (?P<b>.+?) for (?P<c>.+?)\.?$",
            lambda match: f"{match.group('a')} 是用于 {match.group('c')} 的最佳 {match.group('b')}。",
        ),
    ]
    for pattern, builder in patterns:
        match = re.search(pattern, sentence, flags=re.IGNORECASE)
        if match:
            return _apply_glossary(builder(match))

    translated = _apply_glossary(sentence)
    ascii_letters = len(re.findall(r"[A-Za-z]", translated))
    if ascii_letters > max(80, len(translated) * 0.45):
        return _fallback_chinese_meaning(sentence, item)
    return translated


def _fallback_chinese_meaning(sentence: str, item: dict[str, Any]) -> str:
    source = item.get("source_name") or "该来源"
    title = item.get("title") or "这条信息"
    keywords = "、".join((item.get("matched_keywords") or [])[:5])
    if keywords:
        return f"规则版大意：{source} 的这条信息《{title}》主要涉及 {keywords}。原文细节较多，建议点开原文确认完整语境。"
    return f"规则版大意：{source} 的这条信息《{title}》包含较多细节，建议点开原文确认完整语境。"


def _apply_glossary(text: str) -> str:
    translated = text
    for english, chinese in sorted(GLOSSARY.items(), key=lambda pair: len(pair[0]), reverse=True):
        translated = re.sub(re.escape(english), chinese, translated, flags=re.IGNORECASE)
    replacements = [
        (r"\bnow supports\b", "现在支持"),
        (r"\bis now supported with\b", "现在可通过以下方式支持"),
        (r"\bcan still be accessed through\b", "仍可通过以下方式访问"),
        (r"\bwhat'?s changed\b", "主要变化"),
        (r"\bfix:\b", "修复："),
        (r"\bnew\b", "新的"),
        (r"\blaunch\b", "启动"),
        (r"\blaunched\b", "已发布"),
        (r"\bannounced\b", "宣布"),
        (r"\bsupported\b", "支持"),
        (r"\bsupports\b", "支持"),
        (r"\bperformance\b", "性能"),
        (r"\bcompared\b", "对比"),
        (r"\bfully local\b", "完全本地运行"),
        (r"\bsingle\b", "单个"),
        (r"\bWindows\b", "Windows"),
        (r"\bMac\b", "Mac"),
        (r"\bno Docker\b", "不需要 Docker"),
        (r"\bno WSL\b", "不需要 WSL"),
    ]
    for pattern, replacement in replacements:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
    return normalize_space(translated)


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
    core_excerpt = _core_excerpt(item)
    translated_excerpt = _rule_based_translation(core_excerpt, item)
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
            f"  > {core_excerpt}",
            "",
            "- 中文翻译 / 大意（规则版，仅供快速理解）：",
            f"  > {translated_excerpt}",
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
        "- 中文翻译：当前为 No API Key 规则版参考翻译，不调用模型 API；准确含义仍以原文为准。",
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
