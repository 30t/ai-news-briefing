from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_model_daily import select_items_for_model_daily  # noqa: E402


def item(
    title: str,
    *,
    source_level: str,
    score: int,
    tags: list[str] | None = None,
    source_type: str = "rss",
) -> dict:
    return {
        "title": title,
        "url": f"https://example.com/{title.replace(' ', '-').lower()}",
        "source_level": source_level,
        "source_type": source_type,
        "score": score,
        "editorial_score": score,
        "tags": tags or [],
    }


class SelectItemsForModelDailyTest(unittest.TestCase):
    def test_caps_early_signal_items_even_when_pool_has_room(self) -> None:
        items = [
            item("Applied product launch", source_level="official_confirmed", score=72, tags=["business"]),
            item("High value benchmark", source_level="early_signal", score=82, tags=["agent"]),
            item("Second strong research signal", source_level="early_signal", score=76, tags=["rag_data"]),
            item("Ordinary theory paper A", source_level="early_signal", score=64, tags=["agent"]),
            item("Ordinary theory paper B", source_level="early_signal", score=63, tags=["agent"]),
            item("Ordinary theory paper C", source_level="early_signal", score=62, tags=["agent"]),
            item("Ordinary theory paper D", source_level="early_signal", score=61, tags=["agent"]),
        ]

        selected = select_items_for_model_daily(
            items,
            {},
            {
                "model_daily_candidate_pool_size": 20,
                "model_daily_max_items": 6,
                "model_daily_max_early_signal_items": 2,
                "model_daily_min_early_signal_score": 70,
            },
        )

        early_signal_items = [entry for entry in selected if entry["source_level"] == "early_signal"]
        self.assertLessEqual(len(early_signal_items), 2)
        self.assertEqual(
            ["High value benchmark", "Second strong research signal"],
            [entry["title"] for entry in early_signal_items],
        )

    def test_retains_exceptionally_high_value_early_signal(self) -> None:
        items = [
            item("Routine product note", source_level="official_confirmed", score=55, tags=["business"]),
            item("Routine tool release", source_level="official_confirmed", score=54, tags=["open_source"]),
            item("Production risk benchmark", source_level="early_signal", score=88, tags=["agent"]),
            item("Low value theory paper", source_level="early_signal", score=50, tags=["model"]),
        ]

        selected = select_items_for_model_daily(
            items,
            {},
            {
                "model_daily_candidate_pool_size": 10,
                "model_daily_max_items": 3,
                "model_daily_max_early_signal_items": 1,
                "model_daily_min_early_signal_score": 75,
            },
        )

        self.assertIn("Production risk benchmark", [entry["title"] for entry in selected])
        self.assertNotIn("Low value theory paper", [entry["title"] for entry in selected])


if __name__ == "__main__":
    unittest.main()
