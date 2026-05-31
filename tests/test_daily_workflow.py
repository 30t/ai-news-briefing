from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DailyWorkflowTest(unittest.TestCase):
    def test_daily_action_refreshes_timeline_site_at_7am_china_time(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "daily-news.yml").read_text(encoding="utf-8")

        self.assertIn("cron: '0 23 * * *'", workflow)
        self.assertIn("python scripts/main.py", workflow)
        self.assertIn("git add output/ site/timeline-data.js", workflow)

    def test_pages_action_publishes_static_site_directory(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")

        self.assertIn("Deploy Timeline Site", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("enablement: true", workflow)
        self.assertIn("path: site", workflow)
        self.assertIn("actions/deploy-pages", workflow)


if __name__ == "__main__":
    unittest.main()
