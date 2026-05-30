from __future__ import annotations

import json
import re
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Any

from output_paths import discover_dated_source_paths, output_dir
from utils import LOCAL_TIMEZONE, ROOT, normalize_space, parse_datetime, strip_html


COMPANY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("OpenAI/GPT", ("openai", "gpt", "chatgpt", "codex")),
    ("Anthropic/Claude", ("anthropic", "claude")),
    ("Google/Gemini", ("google", "deepmind", "gemini")),
    ("Meta/Llama", ("meta", "llama")),
    ("DeepSeek", ("deepseek",)),
    ("xAI/Grok", ("xai", "grok")),
    ("Mistral", ("mistral",)),
    ("Qwen", ("qwen", "alibaba", "通义")),
    ("Microsoft/GitHub", ("microsoft", "github", "copilot")),
    ("NVIDIA", ("nvidia", "blackwell", "nvlink")),
]

COMPANY_ROWS = [company for company, _keywords in COMPANY_KEYWORDS]

OFFICIAL_COMPANY_SOURCES = {
    "OpenAI/GPT": {"OpenAI News"},
    "Anthropic/Claude": {"Anthropic News"},
    "Google/Gemini": {"Google DeepMind Blog"},
    "Meta/Llama": {"Meta AI Blog"},
    "DeepSeek": set(),
    "xAI/Grok": set(),
    "Mistral": set(),
    "Qwen": set(),
    "Microsoft/GitHub": {"GitHub Blog", "GitHub Changelog", "Microsoft AI Blog", "Azure AI Blog"},
    "NVIDIA": {"NVIDIA Blog"},
}

LEVEL_BY_LABEL = {
    "官方确认": "official_confirmed",
    "技术社区": "tech_community",
    "早期信号": "early_signal",
    "待验证": "needs_verification",
}


def main() -> None:
    args = _parse_args()
    write_timeline_payload(ROOT, days=args.days)


def _parse_args() -> Any:
    parser = ArgumentParser(description="Generate timeline JSON from existing source candidate markdown.")
    parser.add_argument("--days", type=int, default=30, help="Number of latest dated source files to include.")
    return parser.parse_args()


def discover_recent_source_paths(root: Path, days: int = 30) -> list[Path]:
    return discover_dated_source_paths(root)[-days:]


def build_timeline_payload(
    root: Path,
    days: int = 30,
    company_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paths = discover_recent_source_paths(root, days)
    items: list[dict[str, Any]] = []
    for path in paths:
        source_date = path.stem
        items.extend(_parse_source_markdown(path.read_text(encoding="utf-8"), source_date))

    items.sort(key=lambda item: (item["date"], item["time"], item["score"]), reverse=False)
    dates = _timeline_dates(paths, items, days)
    company_calendar_items = _raw_company_calendar_items(company_items or [], dates)
    company_matrix_items = _merge_company_items(items, company_calendar_items)
    return {
        "window_days": days,
        "generated_from": dates,
        "companies": COMPANY_ROWS,
        "items": items,
        "company_items": company_calendar_items,
        "company_matrix": _build_company_matrix(company_matrix_items, dates),
    }


def write_timeline_payload(
    root: Path,
    days: int = 30,
    company_items: list[dict[str, Any]] | None = None,
) -> Path:
    payload = build_timeline_payload(root, days=days, company_items=company_items)
    timeline_dir = output_dir(root) / "timeline"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    output_path = timeline_dir / "latest.json"
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    output_path.write_text(serialized + "\n", encoding="utf-8")
    site_dir = root / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "timeline-data.js").write_text(
        f"window.TIMELINE_DATA = {serialized};\n",
        encoding="utf-8",
    )
    return output_path


def classify_company(title: str, source_name: str, keywords: list[str]) -> str | None:
    title_and_source = " ".join([title, source_name]).lower()
    if "llama.cpp" in title_and_source:
        return None
    text = " ".join([title, source_name, " ".join(_company_keywords(keywords))]).lower()
    for company, company_keywords in COMPANY_KEYWORDS:
        if any(_matches_company_keyword(text, keyword) for keyword in company_keywords):
            return company
    return None


def official_company_for_item(item: dict[str, Any]) -> str | None:
    if item.get("source_level") != "official_confirmed":
        return None
    source_name = item.get("source_name") or ""
    for company, sources in OFFICIAL_COMPANY_SOURCES.items():
        if source_name in sources:
            return company
    return None


def should_include_company_calendar_item(item: dict[str, Any]) -> bool:
    text = " ".join(
        str(item.get(key) or "")
        for key in ("title", "headline", "summary_or_excerpt", "summary", "reason")
    ).lower()
    if any(word in text for word in ("quota reset", "rate limit reset", "额度重置", "配额重置")):
        return False
    if any(word in text for word in ("bug fix", "bug fixes", "maintenance patch", "patch release", "修复 bug", "错误修复")):
        return False
    include_markers = (
        "introducing",
        "announce",
        "announcing",
        "launch",
        "released",
        "release",
        "new",
        "available",
        "mobile",
        "app",
        "partnership",
        "integration",
        "api",
        "model",
        "feature",
        "发布",
        "推出",
        "上线",
        "新增",
        "合作",
        "集成",
        "功能",
    )
    return any(marker in text for marker in include_markers)


def raw_company_calendar_item(item: dict[str, Any], fallback_date: str) -> dict[str, Any] | None:
    company = official_company_for_item(item)
    if not company or not should_include_company_calendar_item(item):
        return None
    date_text, time_text = _raw_date_time_parts(item.get("published_at"), fallback_date)
    title = normalize_space(str(item.get("title") or ""))
    url = normalize_space(str(item.get("url") or ""))
    if not title or not url:
        return None
    keywords = list(item.get("matched_keywords") or [])
    score = _parse_int(str(item.get("editorial_score") or item.get("score") or item.get("rule_relevance_score") or "0"))
    return {
        "id": _stable_id(date_text, url, title),
        "date": date_text,
        "time": time_text,
        "title": title,
        "headline": title,
        "url": url,
        "source_name": item.get("source_name") or "未知来源",
        "source_level": item.get("source_level") or "needs_verification",
        "source_level_label": "官方确认",
        "source_type": item.get("source_type") or "未知",
        "keywords": keywords,
        "category": "official_release",
        "score": score,
        "decision": "company_calendar",
        "content_type": "company_calendar",
        "risk_level": "官方确认",
        "reason": "公司官方来源的自家发布，进入核心公司发布节奏日历。",
        "summary": normalize_space(strip_html(item.get("summary_or_excerpt") or "")),
        "company": company,
    }


def _company_keywords(keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword.lower() not in {"github", "llama", "cuda"}]


def _matches_company_keyword(text: str, keyword: str) -> bool:
    if keyword == "github":
        return bool(re.search(r"\bgithub\s+(blog|changelog|copilot)\b|\bgithub\s+copilot\b", text))
    if keyword == "llama":
        return bool(re.search(r"\bllama\b(?!\.cpp)", text))
    if re.search(r"[a-z0-9]", keyword):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text))
    return keyword in text


def _parse_source_markdown(content: str, source_date: str) -> list[dict[str, Any]]:
    chunks = re.split(r"\n---\n", content)
    items: list[dict[str, Any]] = []
    for chunk in chunks:
        match = re.search(r"^###\s+\d+\.\s+(.+)$", chunk, flags=re.MULTILINE)
        if not match:
            continue
        title = normalize_space(match.group(1))
        url = _field(chunk, "原文链接")
        if not title or not url:
            continue
        keywords = _split_keywords(_field(chunk, "命中关键词"))
        legacy_meta = _legacy_meta(chunk)
        source_name = _field(chunk, "来源名称") or legacy_meta.get("source_name") or "未知来源"
        published_at = _field(chunk, "发布时间")
        date_text, time_text = _date_time_parts(published_at, source_date)
        llm_title = _field(chunk, "模型中文标题") or _field(chunk, "原始标题")
        source_level_label = _field(chunk, "来源等级") or legacy_meta.get("source_level_label") or "待验证"
        source_type = (
            _field(chunk, "来源类型")
            or _field(chunk, "发布渠道")
            or legacy_meta.get("source_type")
            or "未知"
        )
        item = {
            "id": _stable_id(source_date, url, title),
            "date": date_text,
            "time": time_text,
            "title": title,
            "headline": llm_title or title,
            "url": url,
            "source_name": source_name,
            "source_level": LEVEL_BY_LABEL.get(source_level_label, "needs_verification"),
            "source_level_label": source_level_label,
            "source_type": source_type,
            "keywords": keywords,
            "category": _category_for_item(chunk, keywords),
            "score": _parse_int(
                _field(chunk, "模型编辑分")
                or _field(chunk, "规则召回分")
                or legacy_meta.get("score", "")
            ),
            "decision": _field(chunk, "编辑决策"),
            "content_type": _field(chunk, "内容类型"),
            "risk_level": _field(chunk, "风险等级"),
            "reason": _field(chunk, "入选原因") or _field(chunk, "为什么值得看"),
            "summary": _blockquote_after(chunk, "Feed 摘要") or _blockquote_after(chunk, "核心总结"),
            "company": classify_company(title, source_name, keywords),
        }
        items.append(item)
    return items


def _timeline_dates(paths: list[Path], items: list[dict[str, Any]], days: int) -> list[str]:
    path_dates = {path.stem for path in paths}
    item_dates = {item["date"] for item in items if item.get("date")}
    return sorted(path_dates | item_dates)[-days:]


def _raw_company_calendar_items(items: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any]]:
    if not dates:
        return []
    date_set = set(dates)
    fallback_date = dates[-1]
    calendar_items: list[dict[str, Any]] = []
    for item in items:
        converted = raw_company_calendar_item(item, fallback_date)
        if converted and converted["date"] in date_set:
            calendar_items.append(converted)
    calendar_items.sort(key=lambda item: (item["date"], item["time"], item["score"]), reverse=False)
    return calendar_items


def _merge_company_items(
    timeline_items: list[dict[str, Any]],
    company_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen_ids = {item["id"] for item in timeline_items}
    seen_urls = {item["url"] for item in timeline_items if item.get("url")}
    merged = list(timeline_items)
    for item in company_items:
        if item["id"] in seen_ids or item.get("url") in seen_urls:
            continue
        seen_ids.add(item["id"])
        if item.get("url"):
            seen_urls.add(item["url"])
        merged.append(item)
    return merged


def _build_company_matrix(items: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for company in COMPANY_ROWS:
        row_days: list[dict[str, Any]] = []
        for date_text in dates:
            day_items = [
                item for item in items if _is_company_calendar_item(item, company) and item["date"] == date_text
            ]
            day_items.sort(key=lambda item: item["score"], reverse=True)
            top = day_items[0] if day_items else None
            row_days.append(
                {
                    "date": date_text,
                    "count": len(day_items),
                    "headline": top["headline"] if top else "",
                    "score": top["score"] if top else 0,
                    "item_ids": [item["id"] for item in day_items],
                }
            )
        result.append({"company": company, "days": row_days})
    return result


def _is_company_calendar_item(item: dict[str, Any], company: str) -> bool:
    if official_company_for_item(item) != company:
        return False
    return should_include_company_calendar_item(item)


def _field(chunk: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}：(.+)$", chunk, flags=re.MULTILINE)
    return normalize_space(match.group(1)) if match else ""


def _legacy_meta(chunk: str) -> dict[str, str]:
    match = re.search(
        r"\*\*判断：(?P<level>[^｜]+)｜信息来源：(?P<source>[^｜]+)｜(?:发布渠道|来源类型)：(?P<type>[^｜]+)｜规则分 (?P<score>\d+)\*\*",
        chunk,
    )
    if not match:
        return {}
    return {
        "source_level_label": normalize_space(match.group("level")),
        "source_name": normalize_space(match.group("source")),
        "source_type": normalize_space(match.group("type")),
        "score": normalize_space(match.group("score")),
    }


def _blockquote_after(chunk: str, heading: str) -> str:
    marker = f"- {heading}："
    if marker not in chunk:
        return ""
    after = chunk.split(marker, 1)[1]
    lines: list[str] = []
    for line in after.splitlines()[1:]:
        if line.startswith("  > "):
            lines.append(line.removeprefix("  > ").strip())
            continue
        if line.startswith("- "):
            break
    return normalize_space(" ".join(lines))


def _split_keywords(text: str) -> list[str]:
    if not text or text == "无":
        return []
    return [part.strip() for part in re.split(r"、|,", text) if part.strip()]


def _parse_int(text: str) -> int:
    match = re.search(r"-?\d+", text or "")
    return int(match.group(0)) if match else 0


def _date_time_parts(published_at: str, fallback_date: str) -> tuple[str, str]:
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", published_at or "")
    if match:
        return match.group(1), match.group(2)
    return fallback_date, "00:00"


def _raw_date_time_parts(published_at: Any, fallback_date: str) -> tuple[str, str]:
    parsed = parse_datetime(published_at)
    if parsed is None:
        return fallback_date, "00:00"
    local = parsed.astimezone(LOCAL_TIMEZONE)
    return local.strftime("%Y-%m-%d"), local.strftime("%H:%M")


def _category_for_item(chunk: str, keywords: list[str]) -> str:
    content_type = _field(chunk, "内容类型")
    if content_type:
        return content_type
    lowered = " ".join(keywords).lower()
    if any(keyword in lowered for keyword in ("agent", "codex", "copilot", "mcp")):
        return "agent"
    if any(keyword in lowered for keyword in ("gpu", "nvidia", "chip", "semiconductor")):
        return "semiconductor"
    if any(keyword in lowered for keyword in ("release", "github")):
        return "release"
    return "news"


def _stable_id(source_date: str, url: str, title: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "-", f"{source_date}-{url or title}").strip("-").lower()
    return key[:120]


if __name__ == "__main__":
    main()
