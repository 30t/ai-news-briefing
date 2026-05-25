from __future__ import annotations

import re
from pathlib import Path


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def output_dir(root: Path) -> Path:
    return root / "output"


def source_output_dir(root: Path) -> Path:
    return output_dir(root) / "sources"


def model_output_dir(root: Path) -> Path:
    return output_dir(root) / "model"


def dated_source_path(root: Path, date_text: str) -> Path:
    _require_date(date_text)
    return source_output_dir(root) / f"{date_text}.md"


def latest_source_path(root: Path) -> Path:
    return source_output_dir(root) / "latest.md"


def dated_model_path(root: Path, date_text: str) -> Path:
    _require_date(date_text)
    return model_output_dir(root) / f"{date_text}.md"


def latest_model_path(root: Path) -> Path:
    return model_output_dir(root) / "latest.md"


def discover_dated_source_paths(root: Path) -> list[Path]:
    sources_dir = source_output_dir(root)
    if not sources_dir.exists():
        return []
    return sorted(path for path in sources_dir.glob("*.md") if DATE_PATTERN.match(path.stem))


def _require_date(date_text: str) -> None:
    if not DATE_PATTERN.match(date_text):
        raise ValueError(f"Expected YYYY-MM-DD date, got: {date_text}")
