from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backlog import update_backlog_after_model_selection  # noqa: E402


def candidate(
    title: str,
    *,
    score: int,
    source_name: str,
    source_level: str,
) -> dict:
    return {
        "title": title,
        "url": f"https://example.com/{title.replace(' ', '-').lower()}",
        "source_name": source_name,
        "source_type": "rss",
        "source_level": source_level,
        "published_at": "2026-06-04T00:00:00+08:00",
        "summary_or_excerpt": title,
        "matched_keywords": ["Agent"],
        "tags": ["agent"],
        "score": score,
    }


class BacklogTest(unittest.TestCase):
    def test_limits_early_signal_and_single_source_backlog_items(self) -> None:
        arxiv_items = [
            candidate(
                f"Agent benchmark paper {index}",
                score=80 - index,
                source_name="arXiv cs.AI",
                source_level="early_signal",
            )
            for index in range(40)
        ]
        official_items = [
            candidate(
                f"Official tool release {index}",
                score=60 - index,
                source_name=f"Official Source {index}",
                source_level="official_confirmed",
            )
            for index in range(15)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            backlog = update_backlog_after_model_selection(
                output_dir=Path(tmpdir),
                previous_backlog=[],
                ranked_items=arxiv_items + official_items,
                selected_model_items=[],
                max_items=50,
            )

        early_signals = [item for item in backlog if item["source_level"] == "early_signal"]
        arxiv = [item for item in backlog if item["source_name"] == "arXiv cs.AI"]

        self.assertLessEqual(len(early_signals), 20)
        self.assertLessEqual(len(arxiv), 15)
        self.assertEqual(15, len([item for item in backlog if item["source_level"] == "official_confirmed"]))


if __name__ == "__main__":
    unittest.main()
