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

NEWS_SECTIONS = [
    "模型与能力更新",
    "硬件与基础设施",
    "应用与落地",
    "工具链与开发",
    "商业与产业",
    "安全与可靠性",
    "前沿研究",
]

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

    _annotate_similar_counts(items)
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


def classify_news_section(
    *,
    title: str,
    source_name: str,
    source_type: str,
    keywords: list[str],
    summary: str = "",
    content_type: str = "",
    reason: str = "",
) -> str:
    text = _domain_text(title, source_name, source_type, keywords, summary, content_type, reason)
    if _has_any(text, ("stepfun", "step ", "step-", "step3", "step 3", "nuextract", "liquid ai", "lfm")):
        return "模型与能力更新"
    if _has_any(text, ("nvidia", "n1x", "gpu", "cpu", "npu", "chip", "semiconductor", "芯片", "硬件", "半导体")):
        if _has_any(text, ("deployment", "deploy", "tps", "throughput", "speedup", "acceleration", "本地推理", "部署", "提速", "加速")):
            return "应用与落地"
        if _has_any(text, ("vllm", "llama.cpp", "executorch", "mlx", "webgpu", "gguf", "kv cache", "mtp")):
            return "工具链与开发"
        return "硬件与基础设施"
    if _has_any(text, ("itbench", "itbench-aa", "swe-bench", "agent benchmark", "enterprise agents on tool-use")):
        return "工具链与开发"
    if _has_any(
        text,
        (
            "partnership",
            "partner",
            "customer",
            "enterprise",
            "revenue",
            "earnings",
            "license",
            "licence",
            "pricing",
            "funding",
            "acquisition",
            "commercial",
            "business",
            "合作",
            "客户",
            "企业",
            "财报",
            "许可",
            "定价",
            "融资",
            "收购",
            "商业",
            "产业",
        ),
    ):
        return "商业与产业"
    if _has_any(
        text,
        (
            "prompt injection",
            "jailbreak",
            "安全",
            "长期可靠性",
            "对齐",
            "alignment",
            "risk",
            "attack",
            "防护",
            "poisoning",
            "memfail",
            "privacy",
            "leak",
            "agentwall",
            "agingbench",
            "distractionif",
        ),
    ):
        return "安全与可靠性"
    if _has_any(
        text,
        (
            "gpu",
            "cpu",
            "npu",
            "nvidia",
            "blackwell",
            "nvlink",
            "esp32",
            "chip",
            "semiconductor",
            "memory",
            "m5 mac",
            "dgx",
            "芯片",
            "硬件",
            "算力",
            "半导体",
            "边缘芯片",
        ),
    ):
        if _has_any(text, ("deployment", "deploy", "tps", "throughput", "speedup", "acceleration", "本地推理", "部署", "提速", "加速")):
            return "应用与落地"
        if _has_any(text, ("vllm", "llama.cpp", "executorch", "mlx", "webgpu", "gguf", "kv cache", "mtp")):
            return "工具链与开发"
        return "硬件与基础设施"
    if _has_any(
        text,
        (
            "deployment",
            "deploy",
            "tps",
            "tokens/s",
            "throughput",
            "latency",
            "speedup",
            "acceleration",
            "accelerate",
            "single gpu",
            "rtx",
            "local inference",
            "本地推理",
            "部署方案",
            "实测",
            "提速",
            "加速",
            "达到",
        ),
    ):
        return "应用与落地"
    if _has_any(
        text,
        (
            "itbench",
            "itbench-aa",
            "copilot",
            "cursor",
            "claude code",
            "codex",
            "swe-bench",
            "swebench",
            "code generation",
            "coding",
            "ide",
            "warp",
            "poolside",
            "composer",
            "vllm",
            "llama.cpp",
            "exectuorch",
            "executorch",
            "mlx",
            "webgpu",
            "gguf",
            "kv cache",
            "mtp",
            "runtime",
            "serving",
            "langgraph",
            "mcp",
            "tool calling",
            "gui agent",
            "browser agent",
            "workflow",
            "automation",
            "autopa",
            "autopra",
            "autorpa",
            "saas-bench",
            "graphmind",
            "智能体",
            "自动化",
            "工具调用",
            "工作流",
            "代码",
            "编程",
            "编码",
            "推理框架",
            "服务框架",
        ),
    ):
        return "工具链与开发"
    if _has_any(
        text,
        (
            "model",
            "models",
            "moe",
            "multimodal",
            "context",
            "qwen",
            "gemini",
            "gpt",
            "claude",
            "deepseek",
            "llama",
            "mistral",
            "command a",
            "step",
            "liquid ai",
            "lfm",
            "quantization",
            "模型",
            "多模态",
            "上下文",
            "量化",
            "能力",
        ),
    ):
        return "模型与能力更新"
    if _has_any(
        text,
        (
            "rag",
            "graphrag",
            "chroma",
            "retrieval",
            "knowledge graph",
            "knowledge base",
            "memory",
            "memfail",
            "nuextract",
            "datasette",
            "研究",
            "research",
            "arxiv",
            "paper",
            "benchmark",
            "bench",
            "数据",
            "检索",
            "知识库",
            "知识图谱",
            "记忆",
            "论文",
            "基准",
        ),
    ):
        return "前沿研究"
    return "前沿研究"


classify_domain_category = classify_news_section


def infer_event_type(title: str, content_type: str, source_name: str, keywords: list[str]) -> str:
    text = " ".join([title, content_type, source_name, " ".join(keywords)]).lower()
    if _has_any(text, ("funding_rumor", "rumor", "传闻")):
        return "传闻"
    if _has_any(text, ("business_signal", "partnership", "partner", "earnings", "customer", "商业", "合作", "财报")):
        return "商业信号"
    if _has_any(text, ("benchmark", "bench", "测评", "评测", "基准")):
        return "基准"
    if _has_any(text, ("reddit", "实测", "测试")) and not _has_any(text, ("release", "发布")):
        return "实测"
    if _has_any(text, ("research", "arxiv", "paper", "论文")):
        return "论文"
    if _has_any(text, ("minor_release", "update", "updated", "changelog", "v0.", "v1.", "更新")):
        return "更新"
    if _has_any(text, ("major_release", "release", "released", "launch", "announce", "发布", "推出", "上线")):
        return "发布"
    return "更新"


def enrich_decision_fields(item: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(item)
    title = enriched.get("headline") or enriched.get("title") or "未命名新闻"
    summary = enriched.get("summary") or ""
    reason = enriched.get("reason") or ""
    category = enriched.get("category") or "前沿研究"
    source_type = enriched.get("source_type") or "未知来源"
    source_level = enriched.get("source_level") or ""
    score = _parse_int(str(enriched.get("score") or "0"))
    text = _domain_text(
        str(enriched.get("title") or title),
        str(enriched.get("source_name") or ""),
        source_type,
        list(enriched.get("keywords") or []),
        summary,
        str(enriched.get("content_type") or ""),
        reason,
    )

    enriched["decision_title"] = _decision_title(enriched)
    enriched["key_change"] = _key_change(title, summary)
    enriched["why_important"] = _why_important(category, text, reason)
    enriched["impact_objects"] = _impact_objects(category, list(enriched.get("keywords") or []), text)
    advice, advice_reason = _action_advice(score, source_level, source_type, enriched.get("event_type") or "", category, text)
    enriched["action_advice"] = advice
    enriched["action_reason"] = advice_reason
    enriched["similar_count"] = int(enriched.get("similar_count") or 0)
    return enriched


def _decision_title(item: dict[str, Any]) -> str:
    headline = normalize_space(str(item.get("headline") or ""))
    title = normalize_space(str(item.get("title") or ""))
    summary = normalize_space(str(item.get("summary") or ""))
    if _looks_like_name_only(headline) and title and title != headline:
        return _short_text(title, 72)
    if _looks_like_name_only(headline) and summary:
        return _short_text(f"{headline}：{summary}", 72)
    return _short_text(headline or title or summary or "未命名新闻", 72)


def _key_change(title: str, summary: str) -> str:
    text = normalize_space(summary or title)
    replacements = (
        ("multi-adapter inference", "多适配器推理"),
        ("throughput", "吞吐"),
        ("integrated with vLLM", "集成 vLLM"),
        ("local inference", "本地推理"),
        ("deployment", "部署"),
    )
    for source, target in replacements:
        text = re.sub(re.escape(source), target, text, flags=re.IGNORECASE)
    return _short_text(text or "暂无关键变化摘要。", 110)


def _why_important(category: str, text: str, reason: str) -> str:
    if reason:
        return reason
    if category == "模型与能力更新":
        return "它可能影响模型选型、能力替换和后续工作流接入。"
    if category == "硬件与基础设施":
        return "它会影响算力成本、边缘 AI 和未来硬件路线判断。"
    if category == "应用与落地":
        if _has_any(text, ("local inference", "本地推理", "deployment", "部署", "throughput", "tps")):
            return "它影响本地推理部署效率，尤其是可复用的部署和性能优化场景。"
        return "它更接近可直接尝试的实践经验，可能比单纯论文更快进入工作流。"
    if category == "工具链与开发":
        return "它可能改变开发工具链、Agent 工作流或代码生成效率。"
    if category == "商业与产业":
        return "它反映企业采用、合作关系或资金流向，能帮助判断产业趋势。"
    if category == "安全与可靠性":
        return "它提示真实使用中的攻击面、可靠性风险或防护方向。"
    return "它属于前沿信号，可作为长期观察和素材归档。"


def _impact_objects(category: str, keywords: list[str], text: str) -> list[str]:
    objects = [category]
    mapping = (
        ("本地推理", ("local inference", "本地推理", "vllm", "llama.cpp", "gguf", "tps")),
        ("Agent 工作流", ("agent", "mcp", "langgraph", "tool use", "工具调用")),
        ("企业部署", ("enterprise", "customer", "企业", "客户", "deployment", "部署")),
        ("半导体硬件", ("gpu", "nvidia", "chip", "semiconductor", "芯片", "硬件")),
        ("AI Coding", ("copilot", "cursor", "claude code", "codex", "swe-bench", "代码")),
        ("RAG / 数据", ("rag", "retrieval", "knowledge", "nuextract", "数据", "检索")),
        ("AI 安全", ("prompt injection", "poisoning", "安全", "可靠性", "attack")),
        ("边缘 AI", ("edge", "esp32", "边缘", "端侧")),
    )
    keyword_text = " ".join(keywords).lower()
    combined = f"{text} {keyword_text}"
    for label, needles in mapping:
        if _has_any(combined, needles) and label not in objects:
            objects.append(label)
    return objects[:5]


def _action_advice(
    score: int,
    source_level: str,
    source_type: str,
    event_type: str,
    category: str,
    text: str,
) -> tuple[str, str]:
    if score >= 78 and source_level == "official_confirmed":
        return "必看", "官方高分信号，优先判断是否能接入现有方案或影响主线判断。"
    if score < 50 or _has_any(text, ("bug fix", "maintenance patch", "quota reset", "配额重置", "小修复")):
        return "忽略", "信号较弱或偏维护性更新，除非正在使用相关项目，否则可以跳过。"
    if source_type in {"Reddit", "HN", "社区", "早期信号"} or event_type in {"传闻", "实测"}:
        return "跟进", "有方向价值，但来源不是官方或仍需复验，需要等待后续验证。"
    if category in {"模型与能力更新", "硬件与基础设施", "应用与落地", "工具链与开发"} and score >= 65:
        return "跟进", "和核心能力、部署或工具链相关，值得后续观察可用性。"
    return "归档", "信息有参考价值，但当前不需要立刻行动。"


def _domain_text(
    title: str,
    source_name: str,
    source_type: str,
    keywords: list[str],
    summary: str,
    content_type: str,
    reason: str,
) -> str:
    return " ".join([title, source_name, source_type, " ".join(keywords), summary, content_type, reason]).lower()


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.lower() in text for needle in needles)


def _looks_like_name_only(text: str) -> bool:
    value = normalize_space(text)
    if not value:
        return True
    if len(value) <= 18 and not re.search(r"\s|：|:|，|,|发布|提升|支持|上线|新增|released|improves|adds", value, flags=re.IGNORECASE):
        return True
    return False


def _short_text(text: str, limit: int) -> str:
    value = normalize_space(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


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
    source_channel = item.get("source_type") or "未知"
    category = classify_domain_category(
        title=title,
        source_name=item.get("source_name") or "未知来源",
        source_type=source_channel,
        keywords=keywords,
        summary=item.get("summary_or_excerpt") or "",
        content_type="official_release",
    )
    return enrich_decision_fields({
        "id": _stable_id(date_text, url, title),
        "date": date_text,
        "time": time_text,
        "title": title,
        "headline": title,
        "url": url,
        "source_name": item.get("source_name") or "未知来源",
        "source_level": item.get("source_level") or "needs_verification",
        "source_level_label": "官方确认",
        "source_type": normalize_source_type(item.get("source_name") or "", source_channel, item.get("source_level") or ""),
        "source_channel": source_channel,
        "keywords": keywords,
        "category": category,
        "event_type": infer_event_type(title, "official_release", item.get("source_name") or "", keywords),
        "score": score,
        "decision": "company_calendar",
        "content_type": "company_calendar",
        "risk_level": "官方确认",
        "reason": "公司官方来源的自家发布，进入核心公司发布节奏日历。",
        "summary": normalize_space(strip_html(item.get("summary_or_excerpt") or "")),
        "company": company,
    })


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


def normalize_source_type(source_name: str, source_channel: str, source_level: str) -> str:
    text = " ".join([source_name, source_channel]).lower()
    if "arxiv" in text:
        return "arXiv"
    if "github" in text:
        return "GitHub"
    if "reddit" in text:
        return "Reddit"
    if "hacker news" in text or text.strip() == "hn":
        return "HN"
    if "blog" in text:
        return "博客"
    if source_level == "official_confirmed":
        return "官方"
    if source_level == "tech_community":
        return "社区"
    if source_level == "early_signal":
        return "早期信号"
    return "媒体"


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
        source_level = LEVEL_BY_LABEL.get(source_level_label, "needs_verification")
        content_type = _field(chunk, "内容类型")
        reason = _field(chunk, "入选原因") or _field(chunk, "为什么值得看")
        summary = _blockquote_after(chunk, "Feed 摘要") or _blockquote_after(chunk, "核心总结")
        category = classify_domain_category(
            title=title,
            source_name=source_name,
            source_type=source_type,
            keywords=keywords,
            summary=summary,
            content_type=content_type,
            reason=reason,
        )
        item = {
            "id": _stable_id(source_date, url, title),
            "date": date_text,
            "time": time_text,
            "title": title,
            "headline": llm_title or title,
            "url": url,
            "source_name": source_name,
            "source_level": source_level,
            "source_level_label": source_level_label,
            "source_type": normalize_source_type(source_name, source_type, source_level),
            "source_channel": source_type,
            "keywords": keywords,
            "category": category,
            "event_type": infer_event_type(title, content_type, source_name, keywords),
            "score": _parse_int(
                _field(chunk, "模型编辑分")
                or _field(chunk, "规则召回分")
                or legacy_meta.get("score", "")
            ),
            "decision": _field(chunk, "编辑决策"),
            "content_type": content_type,
            "risk_level": _field(chunk, "风险等级"),
            "reason": reason,
            "summary": summary,
            "company": classify_company(title, source_name, keywords),
        }
        items.append(enrich_decision_fields(item))
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


def _annotate_similar_counts(items: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = _similarity_key(item)
        if not key:
            continue
        groups.setdefault(key, []).append(item)
    for group in groups.values():
        if len(group) <= 1:
            continue
        for item in group:
            item["similar_count"] = len(group) - 1


def _similarity_key(item: dict[str, Any]) -> str:
    text = normalize_space(str(item.get("title") or item.get("headline") or "")).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    stopwords = {"the", "a", "an", "to", "and", "of", "in", "for", "with", "发布", "更新"}
    tokens = [token for token in text.split() if token not in stopwords]
    return " ".join(tokens[:8])


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
