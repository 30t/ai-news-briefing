from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticSiteTest(unittest.TestCase):
    def test_static_dashboard_reads_timeline_json_and_has_two_sections(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

        self.assertIn("../output/timeline/latest.json", html)
        self.assertIn("timeline-data.js", html)
        self.assertIn("window.TIMELINE_DATA", html)
        self.assertIn("30 天情报时间线", html)
        self.assertIn("核心公司日历", html)
        self.assertIn("company-calendar-grid", html)
        self.assertIn("company-card", html)
        self.assertIn("day-column", html)
        self.assertIn("day-events", html)
        self.assertIn("event-group", html)
        self.assertIn("categoryLabels", html)
        self.assertIn("模型与能力更新", html)
        self.assertIn("硬件与基础设施", html)
        self.assertIn("应用与落地", html)
        self.assertIn("工具链与开发", html)
        self.assertIn("商业与产业", html)
        self.assertIn("安全与可靠性", html)
        self.assertIn("前沿研究", html)
        self.assertIn("event_type", html)
        self.assertIn("source_type", html)
        self.assertIn("groupedDayItems", html)
        self.assertIn("translucentColor", html)
        self.assertIn("activity-dot", html)
        self.assertIn("activity-count", html)
        self.assertIn("activity-headline", html)
        self.assertIn("renderCompanyCalendars", html)
        self.assertIn("calendarCellsForDates", html)
        self.assertNotIn("matrix-row", html)
        self.assertIn("grid-template-columns: repeat(7, minmax(0, 1fr))", html)
        self.assertIn("timeline-density", html)
        self.assertIn("timeline-pan", html)
        self.assertIn("时间滑轨", html)
        self.assertIn("daily-limit", html)
        self.assertIn("密度", html)
        self.assertIn("cleanLabelText", html)
        self.assertIn("detail-section", html)
        self.assertIn("一句话结论", html)
        self.assertIn("为什么重要", html)
        self.assertIn("影响领域", html)
        self.assertIn("处理建议", html)
        self.assertIn("原始来源", html)
        self.assertIn("相似新闻", html)
        self.assertIn("decision_title", html)
        self.assertIn("action_advice", html)
        self.assertIn("继续看原文", html)
        self.assertIn("renderDetailSections", html)
        self.assertIn("detailOriginalTitle", html)
        self.assertNotIn("https://cdn.jsdelivr.net/npm/react", html)


if __name__ == "__main__":
    unittest.main()
