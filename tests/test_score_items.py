from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from score_items import score_items  # noqa: E402


class ScoreItemsTest(unittest.TestCase):
    def test_keyword_relevance_uses_highest_matching_rule_score(self) -> None:
        items = [
            {
                "title": "OpenAI launches Agent API for enterprise workflow automation",
                "url": "https://example.com/news",
                "source_name": "Example",
                "source_type": "rss",
                "source_level": "official_confirmed",
                "summary_or_excerpt": "",
            }
        ]
        keywords_config = {
            "categories": {
                "agent": {"tag": "agent", "keywords": ["Agent"]},
                "business": {"tag": "business", "keywords": ["enterprise"]},
            }
        }
        scoring_config = {
            "source_level_scores": {"official_confirmed": 18},
            "keyword_scores": {
                "launch": {"score": 28, "keywords": ["launches"]},
                "agent": {"score": 16, "keywords": ["Agent"]},
                "business": {"score": 22, "keywords": ["enterprise"]},
            },
            "penalties": {},
        }

        scored = score_items(items, keywords_config, scoring_config)[0]

        self.assertEqual(28, scored["keyword_relevance_score"])
        self.assertEqual(46, scored["rule_relevance_score"])


if __name__ == "__main__":
    unittest.main()
