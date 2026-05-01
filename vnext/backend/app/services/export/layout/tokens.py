"""
Visual tokens — palette + layout constants.

This module is the *single source of truth* for visual constants used by
the analysis PDF renderer. No business logic lives here; only colors,
sizes, paddings, and offsets.

Importing rule of thumb:
    - Colors live in `Palette`.
    - Numeric layout constants live in dataclasses (`BAR_CHART`, `KPI_CHART`, `PANEL`).

Adding a new constant? Put it here. Never inline a hex code or a magic
number in a section/chart module.
"""
from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib import colors

# Re-export from pdf_common to avoid divergence in the brand palette.
from app.services.export.pdf_common import (
    EMERALD,
    SLATE_50,
    SLATE_200,
    SLATE_500,
    SLATE_700,
    SLATE_900,
)


class Palette:
    """Brand + accent palette. Keep names short and stable."""

    # Brand
    EMERALD = EMERALD
    SLATE_50 = SLATE_50
    SLATE_200 = SLATE_200
    SLATE_500 = SLATE_500
    SLATE_700 = SLATE_700
    SLATE_900 = SLATE_900

    # Accents
    RED = colors.HexColor("#DC2626")
    BLUE = colors.HexColor("#2563EB")
    VIOLET = colors.HexColor("#7C3AED")
    AMBER = colors.HexColor("#D97706")
    INK_DARK = colors.HexColor("#0F172A")
    GRAY_BAR = colors.HexColor("#CBD5E1")

    # Panel backgrounds + borders
    GREEN_BG = colors.HexColor("#EAF5F0")
    GREEN_LINE = colors.HexColor("#CDE6D9")
    BLUE_BG = colors.HexColor("#EEF4FF")
    BLUE_LINE = colors.HexColor("#C8D8FF")
    RED_BG = colors.HexColor("#FEECEC")
    RED_LINE = colors.HexColor("#F4C7C7")
    AMBER_BG = colors.HexColor("#FFF7E8")
    AMBER_LINE = colors.HexColor("#F6D9A8")
    PANEL_BG = colors.HexColor("#F8FAFC")
    PANEL_LINE = colors.HexColor("#E2E8F0")

    # Severity-derived darker title colors (used for need cards)
    SEVERITY_HIGH_TITLE = colors.HexColor("#991B1B")
    SEVERITY_MED_TITLE = colors.HexColor("#92400E")
    SEVERITY_LOW_TITLE = colors.HexColor("#334155")


# ── Chart layouts ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BarChartLayout:
    """Geometry for `build_bar_chart`."""

    label_col_width: float = 154
    right_margin: float = 46
    row_height: float = 22
    top_padding: float = 42
    bottom_padding: float = 16
    bar_height: float = 10
    title_offset_y: float = 11
    subtitle_offset_y: float = 24
    value_label_gap: float = 6
    value_label_y_nudge: float = 1.5
    label_y_nudge: float = 4
    title_font_size: float = 11
    subtitle_font_size: float = 8
    label_font_size: float = 8.2
    value_font_size: float = 8.2
    bar_stroke_width: float = 0.4
    label_truncate_chars: int = 28


@dataclass(frozen=True)
class KpiChartLayout:
    """Geometry for `build_kpi_story_chart`."""

    label_col_width: float = 166
    actual_col_width: float = 52
    target_col_width: float = 52
    column_gap: float = 8
    row_height: float = 30
    top_padding: float = 62
    bottom_padding: float = 20
    dot_radius: float = 3.2
    title_offset_y: float = 12
    subtitle_offset_y: float = 26
    column_header_offset_y: float = 42
    title_font_size: float = 11
    subtitle_font_size: float = 8
    column_header_font_size: float = 7.6
    label_font_size: float = 8.2
    value_font_size: float = 8.2
    track_stroke_width: float = 1
    span_stroke_width: float = 1.3
    label_truncate_chars: int = 30
    label_y_nudge: float = 4
    track_y_nudge: float = 8


@dataclass(frozen=True)
class PanelLayout:
    """Default geometry for the inner panels (`_panel` helper)."""

    default_padding: int = 10
    border_width: float = 0.6


@dataclass(frozen=True)
class MetricCardLayout:
    """Top metric strip + quality band."""

    metric_top_padding: int = 14
    metric_bottom_padding: int = 12
    quality_top_padding: int = 10
    quality_bottom_padding: int = 9
    inner_grid_width: float = 0.35
    cards_per_row: int = 4


# ── Singletons ────────────────────────────────────────────────────────────────
# Tokens are immutable; using module-level singletons makes call sites short.
BAR_CHART = BarChartLayout()
KPI_CHART = KpiChartLayout()
PANEL = PanelLayout()
METRIC_CARDS = MetricCardLayout()
