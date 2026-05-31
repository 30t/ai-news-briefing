from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_timeline import (  # noqa: E402
    COMPANY_ROWS,
    NEWS_SECTIONS,
    build_timeline_payload,
    classify_company,
    classify_news_section,
    discover_recent_source_paths,
    infer_event_type,
    raw_company_calendar_item,
    official_company_for_item,
    should_include_company_calendar_item,
    write_timeline_payload,
)
from utils import load_yaml  # noqa: E402


SOURCE_MARKDOWN = """# 每日 AI 情报候选池｜2026-05-25

## 今日 Top 4

### 1. OpenAI releases GPT-5 tools

- 来源等级：官方确认
- 来源名称：OpenAI News
- 来源类型：RSS
- 发布时间：2026-05-25 09:30
- 原文链接：https://example.com/openai
- 命中关键词：OpenAI、GPT、Agent
- 来源可信分：18
- 关键词召回分：28
- 规则召回分：46
- 模型编辑分：82
- 编辑决策：include
- 内容类型：major_release
- 风险等级：官方确认
- 模型分项： 新闻价值 9/10；个人相关性 8/10；可行动性 7/10；判断信心 9/10
- 模型中文标题：OpenAI 发布 GPT 工具更新
- 入选原因：官方发布，和 Agent 工作流高度相关。
- Feed 摘要：
  > OpenAI released new GPT tool capabilities.
- 阅读提醒：来自官方或项目发布渠道。

---

### 2. Small unrelated note

- 来源等级：技术社区
- 来源名称：Example Blog
- 来源类型：RSS
- 发布时间：2026-05-25 11:00
- 原文链接：https://example.com/other
- 命中关键词：无
- 来源可信分：14
- 关键词召回分：0
- 规则召回分：14
- 模型编辑分：40
- 编辑决策：maybe
- 内容类型：other
- 风险等级：社区讨论
- 入选原因：普通记录。
- Feed 摘要：
  > A small note.
- 阅读提醒：来自技术社区。

---

### 3. Claude Code community benchmark

- 来源等级：技术社区
- 来源名称：Reddit r/LocalLLaMA
- 来源类型：RSS
- 发布时间：2026-05-25 12:00
- 原文链接：https://example.com/community-claude
- 命中关键词：Claude
- 来源可信分：14
- 关键词召回分：10
- 规则召回分：24
- 模型编辑分：70
- 编辑决策：include
- 内容类型：community_discussion
- 风险等级：社区讨论
- 入选原因：社区讨论。
- Feed 摘要：
  > Community users discussed Claude Code.
- 阅读提醒：来自技术社区。

---

### 4. Ollama adds Claude launcher

- 来源等级：官方确认
- 来源名称：Ollama
- 发布渠道：GitHub Releases
- 发布时间：2026-05-25 13:00
- 原文链接：https://example.com/ollama-claude
- 命中关键词：Claude、GitHub
- 来源可信分：18
- 关键词召回分：20
- 规则召回分：38
- 模型编辑分：78
- 编辑决策：include
- 内容类型：major_release
- 风险等级：官方确认
- 入选原因：Ollama 官方发布。
- Feed 摘要：
  > Ollama added a launcher for Claude integrations.
- 阅读提醒：来自官方或项目发布渠道。

---
"""

OLD_SOURCE_MARKDOWN = """# 每日 AI 早报｜2026-05-03

### 1. Ollama v0.23.0 发布：原生支持 Claude Desktop 与 Claude Code

**判断：官方确认｜信息来源：Ollama｜发布渠道：GitHub Releases｜规则分 83**

- 为什么值得看：来自官方或项目发布渠道，命中 Claude、Claude Code、GitHub 等关键词，值得快速浏览。
- 发布时间：2026-05-03 03:34
- 原文链接：https://github.com/ollama/ollama/releases/tag/v0.23.0
- 命中关键词：Claude、Claude Code、GitHub
- 原始标题：Ollama v0.23.0：支持 Claude Desktop 与 Claude Code 启动
- 核心总结：
  > Ollama v0.23.0 正式发布，新增对 Claude Desktop 应用的支持。

---
"""


class GenerateTimelineTest(unittest.TestCase):
    def test_aihot_featured_source_is_configured_as_needs_verification(self) -> None:
        config = load_yaml(ROOT / "config" / "sources.yml")
        sources = {source["name"]: source for source in config["rss_sources"]}

        self.assertEqual("https://aihot.virxact.com/feed.xml", sources["AIHOT Featured"]["url"])
        self.assertEqual("needs_verification", sources["AIHOT Featured"]["level"])

    def test_classifies_core_company_from_title_keywords_and_source(self) -> None:
        self.assertIn("OpenAI/GPT", COMPANY_ROWS)
        self.assertEqual("OpenAI/GPT", classify_company("GPT-5 tools", "OpenAI News", ["Agent"]))
        self.assertEqual("Anthropic/Claude", classify_company("Claude Code update", "GitHub", []))
        self.assertEqual("NVIDIA", classify_company("Blackwell NVLink update", "NVIDIA Blog", []))
        self.assertIsNone(classify_company("Unrelated AI note", "Example", []))

    def test_does_not_classify_generic_github_releases_as_github_company_news(self) -> None:
        self.assertIsNone(classify_company("llama.cpp b9010 fixes CUDA OOM", "llama.cpp", ["GitHub", "CUDA"]))
        self.assertIsNone(classify_company("llama.cpp b9008 发布", "llama.cpp", ["GitHub", "Llama"]))
        self.assertIsNone(classify_company("llama : add missing backend call", "llama.cpp", ["Llama"]))
        self.assertIsNone(classify_company("llama: avoid copying logits by ggml-org/llama.cpp", "Reddit r/LocalLLaMA", ["Llama"]))
        self.assertEqual("Microsoft/GitHub", classify_company("GitHub Copilot adds agent mode", "GitHub Blog", []))

    def test_classifies_news_by_reader_priority_section_not_source_shape(self) -> None:
        self.assertEqual(
            "模型与能力更新",
            classify_news_section(
                title="Step 3.7 Flash 发布：196B MoE，多模态能力增强",
                source_name="Reddit r/LocalLLaMA",
                source_type="RSS",
                keywords=["model", "multimodal", "benchmark"],
                summary="New model capability update.",
                content_type="community_discussion",
            ),
        )
        self.assertEqual(
            "应用与落地",
            classify_news_section(
                title="Qwen 27B deployment guide reaches 164 TPS on a single RTX 3090",
                source_name="llama.cpp",
                source_type="GitHub Releases",
                keywords=["deployment", "TPS", "RTX 3090"],
                summary="Practical deployment result.",
                content_type="minor_release",
            ),
        )
        self.assertEqual(
            "工具链与开发",
            classify_news_section(
                title="GitHub Copilot adds coding agent API for SWE-bench tasks",
                source_name="GitHub Blog",
                source_type="RSS",
                keywords=["Copilot", "SWE-bench", "coding agent"],
                summary="Coding workflow update.",
                content_type="major_release",
            ),
        )
        self.assertEqual(
            "安全与可靠性",
            classify_news_section(
                title="arXiv paper studies prompt injection in agent workflows",
                source_name="arXiv cs.AI",
                source_type="RSS",
                keywords=["Prompt Injection", "Agent safety"],
                summary="Attack and mitigation study.",
                content_type="research",
            ),
        )
        self.assertEqual(
            "商业与产业",
            classify_news_section(
                title="OpenAI and Cisco announce enterprise partnership",
                source_name="OpenAI News",
                source_type="RSS",
                keywords=["partnership", "enterprise"],
                summary="Commercial adoption signal.",
                content_type="business_signal",
            ),
        )
        self.assertEqual(
            NEWS_SECTIONS,
            [
                "模型与能力更新",
                "硬件与基础设施",
                "应用与落地",
                "工具链与开发",
                "商业与产业",
                "安全与可靠性",
                "前沿研究",
            ],
        )

    def test_infers_event_type_without_using_it_as_category(self) -> None:
        self.assertEqual("论文", infer_event_type("Agent safety paper", "research", "arXiv cs.AI", ["Agent"]))
        self.assertEqual("基准", infer_event_type("Qwen benchmark result", "community_discussion", "Reddit r/LocalLLaMA", ["benchmark"]))
        self.assertEqual("更新", infer_event_type("vLLM v0.22.0 released", "minor_release", "vLLM", ["vLLM"]))
        self.assertEqual("商业信号", infer_event_type("OpenAI partners with Cisco", "business_signal", "OpenAI News", ["partnership"]))

    def test_discovers_recent_source_paths_by_latest_available_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            for day in range(1, 36):
                (sources / f"2026-05-{day:02d}.md").write_text("x", encoding="utf-8")
            (sources / "latest.md").write_text("ignore", encoding="utf-8")

            paths = discover_recent_source_paths(root, days=30)

            self.assertEqual(30, len(paths))
            self.assertEqual("2026-05-06.md", paths[0].name)
            self.assertEqual("2026-05-35.md", paths[-1].name)

    def test_builds_timeline_payload_from_existing_source_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            (sources / "2026-05-25.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")

            payload = build_timeline_payload(root, days=30)

            self.assertEqual("2026-05-25", payload["generated_from"][-1])
            self.assertEqual(4, len(payload["items"]))
            first = payload["items"][0]
            self.assertEqual("OpenAI releases GPT-5 tools", first["title"])
            self.assertEqual("OpenAI/GPT", first["company"])
            self.assertEqual("工具链与开发", first["category"])
            self.assertEqual("发布", first["event_type"])
            self.assertEqual("官方", first["source_type"])
            self.assertEqual("RSS", first["source_channel"])
            self.assertEqual(82, first["score"])
            self.assertEqual("官方发布，和 Agent 工作流高度相关。", first["reason"])
            self.assertEqual("OpenAI released new GPT tool capabilities.", first["summary"])

            matrix = payload["company_matrix"]
            self.assertEqual("OpenAI/GPT", matrix[0]["company"])
            self.assertEqual("OpenAI 发布 GPT 工具更新", matrix[0]["days"][0]["headline"])
            self.assertEqual(1, matrix[0]["days"][0]["count"])
            anthropic = next(row for row in matrix if row["company"] == "Anthropic/Claude")
            self.assertEqual(0, anthropic["days"][0]["count"])

            json.dumps(payload, ensure_ascii=False)

    def test_timeline_dates_include_actual_published_dates_from_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            (sources / "2026-05-25.md").write_text(
                SOURCE_MARKDOWN.replace("2026-05-25 09:30", "2026-05-24 23:30"),
                encoding="utf-8",
            )

            payload = build_timeline_payload(root, days=30)

            self.assertIn("2026-05-24", payload["generated_from"])
            self.assertIn("2026-05-25", payload["generated_from"])

    def test_builds_timeline_payload_from_legacy_source_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            (sources / "2026-05-03.md").write_text(OLD_SOURCE_MARKDOWN, encoding="utf-8")

            payload = build_timeline_payload(root, days=30)

            first = payload["items"][0]
            self.assertEqual("Ollama", first["source_name"])
            self.assertEqual("GitHub", first["source_type"])
            self.assertEqual("GitHub Releases", first["source_channel"])
            self.assertEqual("official_confirmed", first["source_level"])
            self.assertEqual("工具链与开发", first["category"])
            self.assertEqual("更新", first["event_type"])
            self.assertEqual(83, first["score"])
            self.assertEqual("来自官方或项目发布渠道，命中 Claude、Claude Code、GitHub 等关键词，值得快速浏览。", first["reason"])
            self.assertEqual("Ollama v0.23.0 正式发布，新增对 Claude Desktop 应用的支持。", first["summary"])

    def test_writes_latest_timeline_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            (sources / "2026-05-25.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")

            output_path = write_timeline_payload(root, days=30)

            self.assertEqual(root / "output" / "timeline" / "latest.json", output_path)
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(4, len(data["items"]))
            site_data = root / "site" / "timeline-data.js"
            self.assertTrue(site_data.exists())
            self.assertTrue(site_data.read_text(encoding="utf-8").startswith("window.TIMELINE_DATA = "))

    def test_company_calendar_uses_official_self_owned_significant_items(self) -> None:
        self.assertEqual(
            "OpenAI/GPT",
            official_company_for_item(
                {
                    "title": "Introducing Codex mobile app",
                    "source_name": "OpenAI News",
                    "source_level": "official_confirmed",
                    "matched_keywords": ["Codex"],
                }
            ),
        )
        self.assertIsNone(
            official_company_for_item(
                {
                    "title": "Claude Code benchmark discussion",
                    "source_name": "Reddit r/LocalLLaMA",
                    "source_level": "tech_community",
                    "matched_keywords": ["Claude"],
                }
            )
        )
        self.assertIsNone(
            official_company_for_item(
                {
                    "title": "Ollama adds Claude launcher",
                    "source_name": "Ollama",
                    "source_level": "official_confirmed",
                    "matched_keywords": ["Claude"],
                }
            )
        )
        self.assertTrue(should_include_company_calendar_item({"title": "Introducing Codex mobile app"}))
        self.assertFalse(should_include_company_calendar_item({"title": "Quota reset schedule update"}))
        self.assertFalse(should_include_company_calendar_item({"title": "Bug fixes and maintenance patch"}))

    def test_company_calendar_can_use_raw_official_items_without_adding_them_to_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            (sources / "2026-05-25.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")

            payload = build_timeline_payload(
                root,
                days=30,
                company_items=[
                    {
                        "title": "Introducing Codex mobile app",
                        "url": "https://example.com/codex-mobile",
                        "source_name": "OpenAI News",
                        "source_type": "RSS",
                        "source_level": "official_confirmed",
                        "published_at": "2026-05-25T06:20:00+00:00",
                        "summary_or_excerpt": "OpenAI released Codex on mobile.",
                        "matched_keywords": ["Codex"],
                        "score": 45,
                    },
                    {
                        "title": "Quota reset schedule update",
                        "url": "https://example.com/quota-reset",
                        "source_name": "OpenAI News",
                        "source_type": "RSS",
                        "source_level": "official_confirmed",
                        "published_at": "2026-05-25T08:00:00+00:00",
                        "summary_or_excerpt": "Quota reset notice.",
                    },
                ],
            )

            self.assertEqual(4, len(payload["items"]))
            self.assertIsNotNone(
                raw_company_calendar_item(
                    {
                        "title": "Introducing Codex mobile app",
                        "url": "https://example.com/codex-mobile",
                        "source_name": "OpenAI News",
                        "source_type": "RSS",
                        "source_level": "official_confirmed",
                        "published_at": "2026-05-25T06:20:00+00:00",
                    },
                    "2026-05-25",
                )
            )
            openai = next(row for row in payload["company_matrix"] if row["company"] == "OpenAI/GPT")
            self.assertEqual(2, openai["days"][0]["count"])
            self.assertIn("2026-05-25-https-example-com-codex-mobile", openai["days"][0]["item_ids"])


if __name__ == "__main__":
    unittest.main()
