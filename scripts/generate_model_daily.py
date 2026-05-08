from __future__ import annotations

import json
import logging
import re
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
    "riscv_stack": "RISC-V / OS / 端侧芯片",
    "embedded_edge_ai": "嵌入式 AI / 物联网 / Edge AI",
    "business": "商业产品与政策",
}

PRIMARY_SECTION_LABELS = {
    "toolchain": "工具链更新汇总",
    "agent_coding": "Agent / 编程工具趋势",
    "open_source": "开源项目 Release 汇总",
    "business": "企业应用 / 商业化信号",
    "semiconductor": "算力 / 半导体观察",
    "embedded_edge_ai": "嵌入式 AI / 物联网 / Edge AI",
    "research": "前沿研究观察",
}

SYSTEM_PROMPT = """你是一个中文 AI 新闻解释型主编。
你的任务不是把新闻压缩成标题摘要，而是把输入的 Top 候选信息池整理成一份“有背景、能看懂、可判断、可行动”的 AI 技术情报日报。

总原则：先讲背景，再讲新闻；先解释对象，再解释变化；先说明证据，再给判断。

必须遵守：
1. 只基于输入内容写作，不编造原文没有的信息；信息不足时写“原文信息不足，无法判断”。
2. 不要做独立的“今日最重要 5 条”。重要内容要进入各自主题板块，由每个板块内部突出重点。
3. 不要机械复述所有候选新闻，但被选入正文的重要新闻都要交代背景，不能只写“发布、优化、提升、支持、增强”。
4. 所有重要判断必须保留来源索引和原文链接；正文中提到具体新闻时，优先使用 Markdown 链接，例如：[3. 标题](https://example.com)。不要只写 [3]。
5. 每条候选新闻都有 primary_section。同一条新闻只在它的 primary_section 里详细展开一次；其他章节如需提到，只能一句话交叉引用，不要重复解释。
6. 官方确认、技术社区、早期信号、待验证必须区分清楚。技术社区必须标注“社区讨论，不等于官方确认”；arXiv / 论文 / benchmark 必须标注“不等于已经产品化”。
7. 语言要像“新闻播报 + 科技解释员”，面向非专家读者，不要论文腔，不要营销夸张，不要堆英文术语。

全局背景解释规则：
- 每条重点新闻必须尽量回答：这是什么、处在哪个领域、原来有什么问题、这次发生了什么、具体变化在哪里、有没有结果或证据、为什么重要、建议读者做什么。
- 如果是版本更新，必须说明本次更新的是主项目、子项目、CLI、SDK、插件还是平台；如果原文没有说明上一个版本，写“原文未明确说明从哪个版本升级而来”。
- 如果是论文 / benchmark，必须说明研究问题、方法、实验对象、结果数字、局限，并提醒“研究信号不等于产品落地”。
- 如果是公司产品 / 官方公告，必须说明公司或产品是什么、面向谁、原来有什么能力、这次新增或改变了什么、对用户或行业有什么影响。
- 如果是社区讨论 / Reddit / Hacker News，必须说明测试条件和样本局限，不要把社区结论写成官方事实。
- 如果是半导体 / 算力 / 硬件，必须说明它位于训练、推理、存储、互联、封装、能效或端侧算力的哪一环。

英文名词背景括号规则：
- 不是所有英文都翻译。AI、GPT、ChatGPT、OpenAI、GitHub、Google、Microsoft、API、GPU、CPU 这类高频词可不强制解释。
- 对理解新闻必须知道、但普通读者可能不熟的英文名词，第一次出现时必须用中文括号补充“它是什么 / 干什么 / 属于哪类技术或公司”。括号不是机械翻译，而是功能解释。
- 示例：NVLink（NVIDIA 的 GPU 高速互联技术，用于多卡之间高速交换数据）；MCP（让 Agent 连接外部工具和数据源的协议）；CLI（命令行工具，适合开发者在终端中运行和自动化脚本调用）；HITL（人在回路中，指 Agent 执行关键动作前需要人确认）；RAG（检索增强生成，让模型先查资料再回答）；benchmark（用于测试模型或系统能力的标准化评测）。
- 公司名、项目名如果不是大众熟悉对象，第一次出现要说明它是干什么的。例如 LangChain（构建 LLM 应用和 Agent 工作流的开源开发框架）、Ollama（本地运行大模型的开源工具）、vLLM（高性能大模型推理服务框架）。

重点新闻写作结构：
对各章节中的重点新闻，优先用 5-7 句话写清楚：背景 → 原来的问题 → 这次发生了什么 → 具体变化 → 结果 / 证据 → 为什么重要 → 建议动作。
小版本 Release 可以更简洁，但仍至少说明：这是什么项目、本次改了什么、原文是否给出量化结果、读者是否需要关注。

章节要求：
1. “工具链更新汇总”：解释工具链项目的用途、更新对象、解决的问题和是否值得试用。
2. “Agent / 编程工具趋势”：重点解释 Agent 工作流、CLI、MCP、HITL、Token 成本、安全风险和开发效率的背景。
3. “开源项目 Release 汇总”：不要只列版本号；要说明项目背景、版本对象、关键变化和升级建议。
4. “企业应用 / 商业化信号”：解释真实业务落地、客户采用、价格、API、订阅、合作、ROI、职业机会等意义。
5. “算力 / 半导体观察”：解释 GPU、HBM、NVLink、CoWoS、推理、训练、先进封装、端侧芯片等在产业链的位置。
6. “嵌入式 AI / 物联网 / Edge AI”：解释 TinyML、MCU、传感器、低功耗推理、ESP32 / STM32 / Cortex-M、TFLite Micro、CMSIS-NN、Edge Impulse 等对真实设备落地的意义。
7. “前沿研究观察”：明确论文、arXiv、benchmark 的研究属性，不能写成已经产品化。
8. “今日建议动作”：必须具体到“检查什么、试用什么、归档什么、继续观察什么、暂时忽略什么”。

输出只能是 Markdown，不要代码块。
"""

REQUIRED_SECTIONS = [
    "## 今日一句话",
    "## 工具链更新汇总",
    "## Agent / 编程工具趋势",
    "## 开源项目 Release 汇总",
    "## 企业应用 / 商业化信号",
    "## 算力 / 半导体观察",
    "## 嵌入式 AI / 物联网 / Edge AI",
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
        logging.warning("Model daily generation failed: %s", exc)
        return None


def select_items_for_model_daily(
    items: list[dict[str, Any]],
    scoring_config: dict[str, Any],
    llm_config: dict[str, Any],
) -> list[dict[str, Any]]:
    pool_size = int(llm_config.get("model_daily_candidate_pool_size", scoring_config.get("max_items_per_day", 40)))
    max_items = int(llm_config.get("model_daily_max_items", 18))
    max_release_items = int(llm_config.get("model_daily_max_release_items", 6))
    pool = [item for item in items[:pool_size] if _is_meaningful_for_model_daily(item)]

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    selected_release_count = 0

    def add(candidates: list[dict[str, Any]], limit: int) -> None:
        nonlocal selected_release_count

        added = 0
        for item in candidates:
            if len(selected) >= max_items or added >= limit:
                break
            key = item.get("url") or item.get("title") or ""
            if not key or key in seen:
                continue
            if _is_release_update(item) and selected_release_count >= max_release_items:
                continue

            selected.append(item)
            seen.add(key)
            added += 1
            if _is_release_update(item):
                selected_release_count += 1

    add([item for item in pool if _has_any_tag(item, {"business"})], 5)
    add([item for item in pool if _has_any_tag(item, {"agent", "coding_tool"})], 5)
    add([item for item in pool if _has_any_tag(item, {"embedded_edge_ai"})], 4)
    add([item for item in pool if _has_any_tag(item, {"ai_app", "rag_data", "open_source"})], 5)
    add([item for item in pool if item.get("source_level") == "official_confirmed"], 6)
    add([item for item in pool if _has_any_tag(item, {"semiconductor", "riscv_stack"})], 5)
    add([item for item in pool if item.get("source_level") == "tech_community"], 3)
    add([item for item in pool if item.get("source_level") == "early_signal"], 3)
    add([item for item in pool if item.get("source_level") == "needs_verification"], 1)
    add(pool, max_items - len(selected))
    return selected[:max_items]


def _generate_with_llm(items: list[dict[str, Any]], total_count: int, config: dict[str, Any], api_key: str) -> str:
    base_url = str(config.get("base_url") or "https://api.deepseek.com").rstrip("/")
    payload = {
        "model": config.get("model", "deepseek-chat"),
        "temperature": float(config.get("model_daily_temperature", 0.2)),
        "max_tokens": int(config.get("model_daily_max_output_tokens", 9000)),
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
    timeout = int(config.get("model_daily_timeout_seconds", 100))
    max_retries = int(config.get("model_daily_max_retries", 1))
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("empty model daily response")
            return _auto_link_source_refs(_ensure_required_sections(content), items)
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
        "release_update_count": stats["release_update_count"],
        "items": [_serialize_item(index, item) for index, item in enumerate(items, 1)],
    }
    return (
        "请根据下面 JSON 写一份固定结构 Markdown 日报。\n"
        "结构必须完整包含：\n"
        "# AI 新闻模型解读日报｜YYYY-MM-DD\n"
        + "\n".join(REQUIRED_SECTIONS)
        + "\n\n写作要求：\n"
        "- 这份日报的目标读者不是领域专家，而是正在建立 AI / Agent / 工具链 / 半导体认知框架的中文读者。\n"
        "- 每条重点新闻先讲背景，再讲结论。不要只写“发布、优化、提升、支持、增强”，必须解释优化的是哪一步、解决了什么问题、通过什么动作实现。\n"
        "- 不要写独立的“今日最重要 5 条”。重要新闻要进入各自主题板块，不要单独抽出来。\n"
        "- 不要逐条机械复述所有 items；但凡进入正文的新闻，都要至少说明“这是什么 + 这次改了什么 + 为什么值得关注”。\n"
        "- 每个 item 已给出 primary_section；同一个 item 只在 primary_section 对应章节详细展开一次，避免跨章节重复。\n"
        "- 正文任何位置提到具体新闻时，必须使用 item.markdown_link，例如 [3. 标题](url)，不要让读者去附录表格反查。\n"
        "- 重点新闻建议按“背景 / 原来的问题 / 这次发生了什么 / 具体变化 / 结果或证据 / 为什么重要 / 建议动作”的顺序写成 5-7 句话。\n"
        "- 普通小版本 Release 可以较短，但也必须写清楚项目背景、更新对象、关键变化和是否值得普通读者关注。\n"
        "- 如果是版本新闻，要明确本次更新的是主项目、子项目、CLI、SDK、插件还是平台；如果原文未提供上一版本，必须写“原文未明确说明从哪个版本升级而来”。\n"
        "- 如果是 alpha、beta、rc、pre-release 等预发布版本，必须提醒“更适合开发者测试，不一定适合生产环境”。\n"
        "- 如果原文没有明确量化结果，必须写“原文未给出明确量化结果”，禁止编造。\n"
        "- 英文名词第一次出现时按需加中文背景括号。不要机械翻译，要解释它在新闻里的作用。例如 NVLink（NVIDIA 的 GPU 高速互联技术，用于多卡之间高速交换数据）、MCP（让 Agent 连接外部工具和数据源的协议）、CLI（命令行工具，适合开发者在终端中运行和自动化脚本调用）。\n"
        "- 高频词 AI、GPT、ChatGPT、OpenAI、GitHub、Google、Microsoft、API、GPU、CPU 可不强制解释；但如果该词是理解新闻的关键，也可以简短解释。\n"
        "- 企业应用 / 商业化信号要解释真实业务落地、客户采用、价格、API、订阅、合作、收入、ROI、行业采用对销售、市场、职业机会的意义。\n"
        "- tags 包含 riscv_stack 或 semiconductor 的条目，优先解释其在训练、推理、存储、互联、封装、能效或端侧算力链条中的位置。\n"
        "- tags 包含 embedded_edge_ai 的条目，优先解释 TinyML、MCU、传感器、低功耗推理、ESP32 / STM32 / Cortex-M、TFLite Micro、CMSIS-NN、Edge Impulse 等对真实设备落地的意义。\n"
        "- 对早期信号要写清楚：这是研究或早期线索，不等于已经产品化。\n"
        "- 对技术社区要写清楚：社区讨论，不等于官方确认，结果可能受测试条件、样本和硬件环境影响。\n"
        "- 附录仍要列出候选来源索引，包含编号、标题、来源等级、来源名称和链接。\n\n"
        f"输入 JSON：{json.dumps(payload, ensure_ascii=False)}"
    )


def _serialize_item(index: int, item: dict[str, Any]) -> dict[str, Any]:
    llm = item.get("llm") or {}
    title = _display_title(item)
    url = item.get("url") or ""
    excerpt = strip_html(item.get("article_text") or item.get("summary_or_excerpt") or "")
    primary_section = _primary_section(item)
    return {
        "id": index,
        "title": item.get("title"),
        "display_title": title,
        "markdown_link": _markdown_link(index, title, url),
        "primary_section": primary_section,
        "primary_section_zh": PRIMARY_SECTION_LABELS.get(primary_section, primary_section),
        "content_handling": _content_handling(item),
        "llm_title": llm.get("final_title_zh"),
        "llm_summary": llm.get("core_summary_zh"),
        "llm_why_it_matters": llm.get("why_it_matters_zh"),
        "source_name": item.get("source_name"),
        "source_type": item.get("source_type"),
        "source_level": item.get("source_level"),
        "source_level_zh": LEVEL_LABELS.get(item.get("source_level"), "待验证"),
        "published_at": format_local_time(item.get("published_at")),
        "url": url,
        "score": item.get("score"),
        "hn_score": item.get("hn_score"),
        "matched_keywords": item.get("matched_keywords") or [],
        "tags": item.get("tags") or [],
        "tags_zh": [TAG_LABELS.get(tag, tag) for tag in item.get("tags") or []],
        "release_version": item.get("release_version"),
        "excerpt": excerpt[:1600],
    }


def _ensure_required_sections(content: str) -> str:
    today = datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d")
    cleaned = content.strip()
    cleaned = cleaned.removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
    if not cleaned.startswith("# AI 新闻模型解读日报"):
        cleaned = f"# AI 新闻模型解读日报｜{today}\n\n{cleaned}"
    missing = [section for section in REQUIRED_SECTIONS if section not in cleaned]
    if missing:
        raise ValueError(f"model daily response missed required sections: {', '.join(missing)}")
    return cleaned + "\n"


def _auto_link_source_refs(content: str, items: list[dict[str, Any]]) -> str:
    links = {
        str(index): _markdown_link(index, _display_title(item), item.get("url") or "")
        for index, item in enumerate(items, 1)
    }

    def replace(match: re.Match[str]) -> str:
        index = match.group(1)
        return links.get(index, match.group(0))

    return re.sub(r"(?<!\])\[(\d+)\](?!\()", replace, content)


def _build_stats(items: list[dict[str, Any]], total_count: int) -> dict[str, Any]:
    source_level_stats: dict[str, int] = {}
    tag_stats: dict[str, int] = {}
    release_update_count = 0
    for item in items:
        level = str(item.get("source_level") or "needs_verification")
        source_level_stats[LEVEL_LABELS.get(level, level)] = source_level_stats.get(LEVEL_LABELS.get(level, level), 0) + 1
        if _is_release_update(item):
            release_update_count += 1
        for tag in item.get("tags") or []:
            label = TAG_LABELS.get(tag, str(tag))
            tag_stats[label] = tag_stats.get(label, 0) + 1
    return {
        "total_fetched": total_count,
        "source_level_stats": source_level_stats,
        "tag_stats": tag_stats,
        "release_update_count": release_update_count,
    }


def _is_meaningful_for_model_daily(item: dict[str, Any]) -> bool:
    if item.get("source_level") in {"official_confirmed", "tech_community"}:
        return True
    if item.get("source_level") == "early_signal":
        return _has_any_tag(item, {"agent", "coding_tool", "ai_app", "rag_data", "open_source", "semiconductor", "riscv_stack", "embedded_edge_ai"})
    return bool(item.get("matched_keywords"))


def _has_any_tag(item: dict[str, Any], tags: set[str]) -> bool:
    return bool(set(item.get("tags") or []).intersection(tags))


def _primary_section(item: dict[str, Any]) -> str:
    if item.get("source_level") == "early_signal":
        return "research"
    tags = set(item.get("tags") or [])
    source_type = item.get("source_type")
    if source_type == "github_release":
        return "open_source"
    if "business" in tags:
        return "business"
    if tags.intersection({"agent", "coding_tool"}):
        return "agent_coding"
    if "embedded_edge_ai" in tags:
        return "embedded_edge_ai"
    if "open_source" in tags:
        return "open_source"
    if "riscv_stack" in tags or "semiconductor" in tags:
        return "semiconductor"
    if tags.intersection({"ai_app", "rag_data", "model"}):
        return "toolchain"
    return "toolchain"


def _content_handling(item: dict[str, Any]) -> str:
    if _is_release_update(item):
        return "background_release_update"
    return "background_explainer"


def _is_release_update(item: dict[str, Any]) -> bool:
    return item.get("source_type") == "github_release"


def _display_title(item: dict[str, Any]) -> str:
    llm = item.get("llm") or {}
    return llm.get("final_title_zh") or item.get("title") or "无标题"


def _markdown_link(index: int, title: str, url: str) -> str:
    safe_title = normalize_space(title).replace("[", "【").replace("]", "】")
    if not url:
        return f"[{index}. {safe_title}]"
    return f"[{index}. {safe_title}]({url})"
