#!/usr/bin/env python3
"""Generate shareable percentage-only benchmark comparison charts."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from benchmark_manifest import (
    BENCHMARK_NAME,
    BENCHMARK_VERSION,
    CORE_QUESTION_IDS,
    FAMILY_DISPLAY_NAMES,
    QUESTION_CATEGORIES,
    benchmark_major,
    percent_for_questions,
)

BACKGROUND = "#F6F3EE"
CARD = "#FFFFFF"
CARD_BORDER = "#D9D1C6"
TEXT = "#141414"
MUTED = "#7A746B"
GRID = "#DDD7CF"
ACCENT = "#7C3AED"

# Green heatmap palette - consistent across all families
PALETTES = {
    "claude":     ["#1B5E20", "#2E7D32", "#43A047", "#66BB6A"],
    "openai":     ["#1B5E20", "#2E7D32", "#43A047", "#66BB6A"],
    "google":     ["#1B5E20", "#2E7D32", "#43A047", "#66BB6A"],
    "openrouter": ["#1B5E20", "#2E7D32", "#43A047", "#66BB6A"],
}

FAMILY_ORDER = ["claude", "openai", "google", "openrouter"]

FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"


@dataclass
class RunResult:
    label: str
    model: str
    family: str
    brand_family: str
    provider: str
    percent: float
    benchmark_version: str
    benchmark_major: int
    per_question: dict
    elapsed_seconds: float | None = None
    total_tokens: int | None = None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_font(size: int, *, serif: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_SERIF if serif else FONT_REGULAR
    return ImageFont.truetype(path, size=size)


def _resolve_run(path_str: str) -> tuple[Path, Path, Path]:
    path = Path(path_str)
    if path.is_dir():
        return path, path / "summary.json", path / "grade_result.json"
    if path.name == "summary.json":
        return path.parent, path, path.parent / "grade_result.json"
    if path.name == "grade_result.json":
        return path.parent, path.parent / "summary.json", path
    raise ValueError(f"Unsupported run path: {path}")


def _infer_family(run_dir: Path, model_name: str) -> str:
    family = run_dir.parent.name.lower()
    if family in FAMILY_DISPLAY_NAMES:
        return family
    if model_name.lower().startswith("claude"):
        return "claude"
    if model_name.lower().startswith("gpt"):
        return "openai"
    if model_name.lower().startswith("gemini"):
        return "google"
    if "/" in model_name:
        return "openrouter"
    return family


def _infer_brand_family(model_name: str, fallback_family: str) -> str:
    model = model_name.lower()
    if model.startswith("gemini") or "gemma" in model:
        return "google"
    return fallback_family


def _pretty_model_label(model_name: str) -> str:
    aliases = {
        "claude-sonnet-4-6": "Claude Sonnet 4.6",
        "claude-haiku-4-5": "Claude Haiku 4.5",
        "claude-opus-4-7": "Claude Opus 4.7",
        "gpt-5.4": "GPT-5.4",
        "gpt-5.5": "GPT-5.5",
        "gpt-5-5": "GPT-5.5",
        "gpt-5.4-nano": "GPT-5.4 nano",
        "gpt-5-4-nano": "GPT-5.4 nano",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
        "google/gemma-4-31b-it:free": "Gemma 4 31B",
        "google-gemma-4-31b-it-free": "Gemma 4 31B",
    }
    if model_name in aliases:
        return aliases[model_name]
    slug = model_name.replace("_", "-").strip("-")
    parts = [part for part in slug.split("-") if part]
    out: list[str] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.isdigit() and i + 1 < len(parts) and parts[i + 1].isdigit():
            out.append(f"{part}.{parts[i + 1]}")
            i += 2
            continue
        if part == "gpt" and i + 2 < len(parts) and parts[i + 1].isdigit() and parts[i + 2].isdigit():
            out.append(f"GPT-{parts[i + 1]}.{parts[i + 2]}")
            i += 3
            continue
        out.append(part.upper() if len(part) <= 3 else part.capitalize())
        i += 1
    return " ".join(out)


def load_run(path_str: str, label_override: str | None) -> RunResult:
    run_dir, summary_path, grade_path = _resolve_run(path_str)
    grade = _load_json(grade_path)
    meta_path = run_dir / "run_meta.json"
    meta = _load_json(meta_path) if meta_path.exists() else {}
    metrics_path = run_dir / "run_metrics.json"
    metrics = _load_json(metrics_path) if metrics_path.exists() else {}
    model_name = meta.get("model") or run_dir.parent.name
    family = _infer_family(run_dir, model_name)
    brand_family = _infer_brand_family(model_name, family)
    # Use brand_family for provider display when model is from a different origin (e.g., Gemma via OpenRouter shows as Google)
    provider = FAMILY_DISPLAY_NAMES.get(brand_family, brand_family.title())
    version = meta.get("benchmark_version", BENCHMARK_VERSION)
    label = label_override or _pretty_model_label(model_name)
    core_percent = percent_for_questions(grade["per_question"], CORE_QUESTION_IDS)
    elapsed = metrics.get("elapsed_seconds")
    if elapsed is not None:
        try:
            elapsed = float(elapsed)
        except (TypeError, ValueError):
            elapsed = None
    total_tokens = metrics.get("total_tokens")
    if total_tokens is not None:
        try:
            total_tokens = int(total_tokens)
        except (TypeError, ValueError):
            total_tokens = None
    return RunResult(
        label=label,
        model=model_name,
        family=family,
        brand_family=brand_family,
        provider=provider,
        percent=core_percent,
        benchmark_version=version,
        benchmark_major=benchmark_major(version),
        per_question=grade["per_question"],
        elapsed_seconds=elapsed,
        total_tokens=total_tokens,
    )


def category_percentages(run: RunResult) -> dict[str, float]:
    values: dict[str, float] = {}
    for category, questions in QUESTION_CATEGORIES.items():
        values[category] = percent_for_questions(run.per_question, questions)
    return values


def _family_rank(family: str) -> tuple[int, str]:
    if family in FAMILY_ORDER:
        return FAMILY_ORDER.index(family), family
    return len(FAMILY_ORDER), family


def _bar_color(run: RunResult, index_within_family: int) -> str:
    palette = PALETTES.get(run.brand_family, ["#1B5E20"])
    return palette[index_within_family % len(palette)]


def _create_canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (width, height), ImageColor.getrgb(BACKGROUND))
    draw = ImageDraw.Draw(image)
    return image, draw


def _card_box(width: int, height: int) -> tuple[int, int, int, int]:
    return (20, 20, width - 20, height - 20)


def _draw_card(image: Image.Image, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_box = (box[0], box[1] + 6, box[2], box[3] + 6)
    shadow_draw.rounded_rectangle(shadow_box, radius=32, fill=(0, 0, 0, 18))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    image.alpha_composite(shadow)
    draw.rounded_rectangle(box, radius=32, fill=CARD, outline=CARD_BORDER, width=2)


def _draw_header(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    subtitle: str,
) -> None:
    accent_box = (box[0] + 36, box[1] + 48, box[0] + 92, box[1] + 104)
    draw.rectangle(accent_box, fill=ACCENT)
    draw.text(
        (box[0] + 118, box[1] + 36),
        title,
        fill=TEXT,
        font=_load_font(54, serif=True),
    )
    draw.text(
        (box[0] + 38, box[1] + 128),
        subtitle,
        fill=MUTED,
        font=_load_font(28),
    )


def _draw_grid(draw: ImageDraw.ImageDraw, plot: tuple[int, int, int, int], *, steps: int = 6) -> None:
    left, top, right, bottom = plot
    for idx in range(steps + 1):
        y = top + int((bottom - top) * idx / steps)
        draw.line((left, y, right, y), fill=GRID, width=2)


_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "logos"


# Cache for loaded logo images
_LOGO_CACHE: dict[str, Image.Image] = {}


def _load_logo(family: str, size: int) -> Image.Image | None:
    """Load and cache a logo image, resized to the specified size."""
    cache_key = f"{family}_{size}"
    if cache_key in _LOGO_CACHE:
        return _LOGO_CACHE[cache_key]

    if family == "claude":
        logo_path = _ASSETS_DIR / "claude-logo.png"
    elif family == "openai":
        logo_path = _ASSETS_DIR / "openai-new-logo.png"
    elif family == "google":
        logo_path = _ASSETS_DIR / "google-gemini-logo.png"
    else:
        return None

    if not logo_path.exists():
        return None

    try:
        img = Image.open(logo_path).convert("RGBA")
        # Resize maintaining aspect ratio
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        _LOGO_CACHE[cache_key] = img
        return img
    except Exception:
        return None


def _draw_openai_logo(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int) -> None:
    cx, cy = center
    radius = size // 7
    orbit = size * 0.22
    for step in range(6):
        angle = math.radians(step * 60)
        x = cx + orbit * math.cos(angle)
        y = cy + orbit * math.sin(angle)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#111111")
    draw.ellipse((cx - radius * 1.1, cy - radius * 1.1, cx + radius * 1.1, cy + radius * 1.1), fill=CARD)
    draw.ellipse((cx - radius * 0.8, cy - radius * 0.8, cx + radius * 0.8, cy + radius * 0.8), outline="#111111", width=3)


def _draw_anthropic_logo(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int) -> None:
    cx, cy = center
    half = size // 2
    badge = (cx - half, cy - half, cx + half, cy + half)
    draw.rounded_rectangle(badge, radius=size // 5, fill="#E8D9CA")
    stroke = max(4, size // 10)
    draw.line((cx - size * 0.2, cy + size * 0.25, cx, cy - size * 0.25), fill="#111111", width=stroke)
    draw.line((cx + size * 0.2, cy + size * 0.25, cx, cy - size * 0.25), fill="#111111", width=stroke)
    draw.line((cx - size * 0.1, cy + size * 0.02, cx + size * 0.1, cy + size * 0.02), fill="#111111", width=stroke)


def _draw_provider_logo(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    family: str,
    center: tuple[int, int],
    size: int,
) -> None:
    """Draw provider logo using actual image file if available, fallback to vector drawing."""
    logo = _load_logo(family, size)
    if logo:
        cx, cy = center
        # Center the logo image
        lx = cx - logo.width // 2
        ly = cy - logo.height // 2
        image.alpha_composite(logo, (lx, ly))
        return

    # Fallback to vector drawing
    if family == "openai":
        _draw_openai_logo(draw, center, size)
        return
    if family == "claude":
        _draw_anthropic_logo(draw, center, size)
        return
    cx, cy = center
    half = size // 2
    draw.rounded_rectangle((cx - half, cy - half, cx + half, cy + half), radius=10, fill="#E7E4DE")
    initial = FAMILY_DISPLAY_NAMES.get(family, family[:1].upper())[:1]
    draw.text((cx, cy), initial, fill=TEXT, font=_load_font(size // 2), anchor="mm")


def _draw_rotated_label(
    image: Image.Image,
    text: str,
    *,
    anchor: tuple[int, int],
    angle: float = 62.0,
    font_size: int = 24,
) -> None:
    font = _load_font(font_size)
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy)
    left, top, right, bottom = dummy_draw.textbbox((0, 0), text, font=font)
    width = right - left + 12
    height = bottom - top + 12
    label = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    label_draw = ImageDraw.Draw(label)
    label_draw.text((6, 6), text, fill=TEXT, font=font)
    rotated = label.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    image.alpha_composite(rotated, dest=(anchor[0], anchor[1]))


def _draw_value(draw: ImageDraw.ImageDraw, bar_box: tuple[int, int, int, int], value: float, color: str) -> None:
    left, top, right, bottom = bar_box
    bar_height = bottom - top
    if bar_height >= 82:
        draw.text(
            ((left + right) / 2, bottom - min(84, bar_height * 0.42)),
            f"{value:.0f}",
            fill="#FFFFFF",
            font=_load_font(42),
            anchor="mm",
        )
        return
    draw.text(
        ((left + right) / 2, top - 18),
        f"{value:.0f}%",
        fill=color,
        font=_load_font(24),
        anchor="mb",
    )


def _ordered_runs(runs: list[RunResult]) -> list[RunResult]:
    family_counts: dict[str, int] = {}
    ordered = sorted(runs, key=lambda run: (-run.percent, _family_rank(run.family), run.label))
    for run in ordered:
        family_counts[run.family] = family_counts.get(run.family, 0) + 1
    return ordered


def _ensure_major_compatibility(runs: list[RunResult], allow_mixed_major: bool) -> None:
    majors = {run.benchmark_major for run in runs}
    current_major = benchmark_major()
    if not allow_mixed_major and (len(majors) > 1 or (majors and current_major not in majors)):
        raise SystemExit(
            "Mixed benchmark major versions detected. Generate separate graphs for each major version."
        )


def plot_overall(runs: list[RunResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = _ordered_runs(runs)
    family_seen: dict[str, int] = {}

    width, height = 1600, 900
    image, draw = _create_canvas(width, height)
    box = _card_box(width, height)
    _draw_card(image, draw, box)
    _draw_header(
        draw,
        box,
        "SMARTS Test",
        f"{BENCHMARK_NAME} v{BENCHMARK_VERSION}; higher core-set percentage is better",
    )

    plot = (box[0] + 95, box[1] + 208, box[2] - 44, box[3] - 330)
    left, top, right, bottom = plot
    _draw_grid(draw, plot)
    draw.line((left, bottom, right, bottom), fill=GRID, width=2)

    count = max(len(ordered), 1)
    gap = 42
    slot_width = (right - left - gap * (count - 1)) / count
    bar_width = min(78, int(slot_width * 0.74))

    for idx, run in enumerate(ordered):
        family_index = family_seen.get(run.family, 0)
        family_seen[run.family] = family_index + 1
        color = _bar_color(run, family_index)
        x_center = int(left + idx * (slot_width + gap) + slot_width / 2)
        height_px = max(6, int((bottom - top - 12) * run.percent / 100.0))
        bar_box = (x_center - bar_width // 2, bottom - height_px, x_center + bar_width // 2, bottom)
        draw.rounded_rectangle(bar_box, radius=18, fill=color)
        _draw_value(draw, bar_box, run.percent, color)
        _draw_provider_logo(image, draw, run.brand_family, (x_center, bottom + 68), 56)
        label = run.label
        _draw_rotated_label(image, label, anchor=(x_center - 40, bottom + 105))

    image.save(output_path)


def _blend(color: str, amount: float) -> tuple[int, int, int]:
    base = ImageColor.getrgb(color)
    return tuple(int(255 - (255 - channel) * amount) for channel in base)


def plot_categories(runs: list[RunResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = _ordered_runs(runs)
    categories = list(QUESTION_CATEGORIES.keys())
    width = 1700
    height = 280 + len(ordered) * 96 + len(categories) * 8
    image, draw = _create_canvas(width, height)
    box = _card_box(width, height)
    _draw_card(image, draw, box)
    _draw_header(
        draw,
        box,
        "SMARTS Test Category Breakdown",
        "Percentages are normalized inside the stable core question set",
    )

    table_left = box[0] + 44
    table_top = box[1] + 210
    row_height = 88
    name_col_width = 350
    value_col_width = 145

    for idx, category in enumerate(categories):
        x0 = table_left + name_col_width + idx * value_col_width
        x1 = x0 + value_col_width - 12
        draw.rounded_rectangle((x0, table_top - 58, x1, table_top - 10), radius=14, fill="#F2EEE7")
        draw.text(((x0 + x1) / 2, table_top - 34), category, fill=TEXT, font=_load_font(21), anchor="mm")

    family_seen: dict[str, int] = {}
    for row_idx, run in enumerate(ordered):
        y0 = table_top + row_idx * row_height
        y1 = y0 + row_height - 14
        draw.rounded_rectangle((table_left, y0, box[2] - 36, y1), radius=22, fill="#FBFAF7", outline="#EEE7DD")
        _draw_provider_logo(image, draw, run.brand_family, (table_left + 40, (y0 + y1) // 2), 42)
        draw.text((table_left + 80, y0 + 22), run.label, fill=TEXT, font=_load_font(26))
        draw.text((table_left + 80, y0 + 50), run.provider, fill=MUTED, font=_load_font(19))
        family_index = family_seen.get(run.family, 0)
        family_seen[run.family] = family_index + 1
        color = _bar_color(run, family_index)
        percentages = category_percentages(run)
        for col_idx, category in enumerate(categories):
            value = percentages[category]
            x0 = table_left + name_col_width + col_idx * value_col_width
            x1 = x0 + value_col_width - 12
            fill = _blend(color, 0.16 + 0.84 * (value / 100.0))
            draw.rounded_rectangle((x0, y0 + 12, x1, y1 - 12), radius=18, fill=fill)
            text_fill = "#FFFFFF" if value >= 58 else TEXT
            draw.text(((x0 + x1) / 2, (y0 + y1) / 2), f"{value:.0f}%", fill=text_fill, font=_load_font(24), anchor="mm")

    image.save(output_path)


def _combo_filtered_runs(runs: list[RunResult], x_mode: str) -> list[RunResult]:
    out: list[RunResult] = []
    for run in runs:
        if x_mode == "time":
            if run.elapsed_seconds is not None and run.elapsed_seconds >= 0:
                out.append(run)
        elif x_mode == "tokens":
            if run.total_tokens is not None and run.total_tokens >= 0:
                out.append(run)
    return out


def _x_value(run: RunResult, x_mode: str) -> float:
    if x_mode == "time":
        return float(run.elapsed_seconds or 0.0)
    return float(run.total_tokens or 0)


def plot_combination(runs: list[RunResult], output_path: Path, *, x_mode: str) -> None:
    """Scatter plot: core-set percent (y) vs elapsed seconds or total tokens (x)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filtered = _combo_filtered_runs(runs, x_mode)
    if not filtered:
        print(
            f"Skipping combination plot ({x_mode}): no runs with run_metrics.json "
            "(elapsed_seconds / total_tokens)."
        )
        return

    ordered = sorted(filtered, key=lambda run: (-run.percent, _family_rank(run.family), run.label))
    family_seen: dict[str, int] = {}

    width, height = 1600, 900
    image, draw = _create_canvas(width, height)
    box = _card_box(width, height)
    _draw_card(image, draw, box)
    x_label = "Wall time (s)" if x_mode == "time" else "Total tokens (reported)"
    subtitle = f"{BENCHMARK_NAME} v{BENCHMARK_VERSION}; each point is one run with logged metrics"
    _draw_header(draw, box, "SMARTS Test — score vs cost", subtitle)

    plot = (box[0] + 95, box[1] + 208, box[2] - 44, box[3] - 280)
    left, top, right, bottom = plot
    _draw_grid(draw, plot)
    draw.line((left, bottom, right, bottom), fill=GRID, width=2)
    draw.line((left, top, left, bottom), fill=GRID, width=2)

    xs = [_x_value(run, x_mode) for run in ordered]
    max_x = max(xs) if xs else 1.0
    min_x = min(xs) if xs else 0.0
    if max_x <= min_x:
        max_x = min_x + 1.0
    span = max_x - min_x
    pad = span * 0.06 if span > 0 else max_x * 0.06 or 1.0
    axis_left = max(0.0, min_x - pad)
    axis_right = max_x + pad

    # Axis ticks (x)
    for i in range(6):
        t = axis_left + (axis_right - axis_left) * i / 5
        x_pix = left + (t - axis_left) / (axis_right - axis_left) * (right - left)
        draw.line((int(x_pix), bottom, int(x_pix), bottom + 8), fill=MUTED, width=2)
        tick_txt = f"{t:.1f}" if x_mode == "time" else f"{t:.0f}"
        draw.text((int(x_pix), bottom + 14), tick_txt, fill=MUTED, font=_load_font(20), anchor="mt")

    draw.text(((left + right) / 2, bottom + 52), x_label, fill=MUTED, font=_load_font(24), anchor="mm")

    # Y axis (percent)
    for i in range(6):
        p = i * 20
        y_pix = bottom - (bottom - top) * (p / 100.0)
        draw.line((left - 8, int(y_pix), left, int(y_pix)), fill=MUTED, width=2)
        draw.text((left - 14, int(y_pix)), f"{p}", fill=MUTED, font=_load_font(20), anchor="rm")

    draw.text((left - 72, (top + bottom) / 2), "Core set %", fill=MUTED, font=_load_font(24), anchor="mm")

    for run in ordered:
        family_index = family_seen.get(run.family, 0)
        family_seen[run.family] = family_index + 1
        color = _bar_color(run, family_index)
        xv = _x_value(run, x_mode)
        x_pix = left + (xv - axis_left) / (axis_right - axis_left) * (right - left)
        y_pix = bottom - (bottom - top) * (run.percent / 100.0)
        r = 14
        draw.ellipse(
            (x_pix - r, y_pix - r, x_pix + r, y_pix + r),
            fill=color,
            outline=CARD_BORDER,
            width=2,
        )
        draw.text((x_pix, y_pix - 26), f"{run.percent:.0f}%", fill=TEXT, font=_load_font(22), anchor="mb")
        short = run.label if len(run.label) <= 28 else run.label[:25] + "…"
        draw.text((x_pix, y_pix + r + 10), short, fill=MUTED, font=_load_font(18), anchor="mt")

    image.save(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "runs",
        nargs="+",
        help="Run directories or summary/grade JSON files. Each must contain summary.json and grade_result.json.",
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        help="Optional labels matching the run order. Defaults to pretty model names.",
    )
    parser.add_argument(
        "--output-prefix",
        default="benchmark_percentages",
        help="Prefix for generated PNG files.",
    )
    parser.add_argument(
        "--allow-mixed-major",
        action="store_true",
        help="Allow mixed major benchmark versions in one graph.",
    )
    parser.add_argument(
        "--combination",
        action="append",
        choices=("percent-time", "percent-tokens"),
        help=(
            "Also emit a scatter plot of core-set percent vs wall time or total tokens "
            "(runs without outputs/.../run_metrics.json are omitted)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.labels and len(args.labels) != len(args.runs):
        raise SystemExit("--labels must match the number of runs")

    runs = [
        load_run(path_str, args.labels[idx] if args.labels else None)
        for idx, path_str in enumerate(args.runs)
    ]
    _ensure_major_compatibility(runs, args.allow_mixed_major)
    plot_overall(runs, Path(f"{args.output_prefix}_overall.png"))
    plot_categories(runs, Path(f"{args.output_prefix}_by_category.png"))
    print(f"Generated {args.output_prefix}_overall.png")
    print(f"Generated {args.output_prefix}_by_category.png")
    combination = args.combination or []
    for mode in combination:
        if mode == "percent-time":
            out = Path(f"{args.output_prefix}_percent_vs_time.png")
            plot_combination(runs, out, x_mode="time")
            if out.is_file():
                print(f"Generated {out}")
        elif mode == "percent-tokens":
            out = Path(f"{args.output_prefix}_percent_vs_tokens.png")
            plot_combination(runs, out, x_mode="tokens")
            if out.is_file():
                print(f"Generated {out}")


if __name__ == "__main__":
    main()
