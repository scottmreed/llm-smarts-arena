from __future__ import annotations

import re
from pathlib import Path


def model_slug(model_name: str) -> str:
    slug = model_name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def run_directory(output_root: Path, family: str, model_name: str, stamp: str) -> Path:
    return output_root / family / model_slug(model_name) / stamp


def figures_directory(figures_root: Path, family: str) -> Path:
    return figures_root / family
