from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from output_paths import (  # noqa: E402
    dated_model_path,
    dated_source_path,
    discover_dated_source_paths,
    latest_model_path,
    latest_source_path,
)


class OutputPathsTest(unittest.TestCase):
    def test_builds_separate_source_and_model_paths(self) -> None:
        root = Path("/tmp/project")

        self.assertEqual(root / "output" / "sources" / "2026-05-15.md", dated_source_path(root, "2026-05-15"))
        self.assertEqual(root / "output" / "sources" / "latest.md", latest_source_path(root))
        self.assertEqual(root / "output" / "model" / "2026-05-15.md", dated_model_path(root, "2026-05-15"))
        self.assertEqual(root / "output" / "model" / "latest.md", latest_model_path(root))

    def test_discovers_only_dated_source_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = root / "output" / "sources"
            sources.mkdir(parents=True)
            (sources / "2026-05-14.md").write_text("old", encoding="utf-8")
            (sources / "2026-05-15.md").write_text("new", encoding="utf-8")
            (sources / "latest.md").write_text("latest", encoding="utf-8")
            (sources / "notes.txt").write_text("ignore", encoding="utf-8")

            self.assertEqual(
                [sources / "2026-05-14.md", sources / "2026-05-15.md"],
                discover_dated_source_paths(root),
            )


if __name__ == "__main__":
    unittest.main()
