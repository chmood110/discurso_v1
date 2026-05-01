"""
Chart builders driven entirely by ``layout/tokens`` — no business logic,
no hex codes, no magic numbers.

Public functions:
    - build_bar_chart(...)    → horizontal labelled bars (0–100% scale)
    - build_kpi_story_chart() → "actual → target" travel chart
"""
from __future__ import annotations

from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors

from app.services.export.domain.safe_access import as_float, as_text, truncate
from app.services.export.layout.tokens import (
    BAR_CHART,
    KPI_CHART,
    BarChartLayout,
    KpiChartLayout,
    Palette,
)


def build_bar_chart(
    *,
    title: str,
    subtitle: str,
    rows: list[tuple[str, float]],
    width: float,
    accent: colors.Color,
    layout: BarChartLayout = BAR_CHART,
) -> Drawing:
    """Horizontal labelled bar chart for percentages on a 0–100 scale.

    ``rows`` is a list of ``(label, value)``. ``value`` is interpreted as a
    percentage (0..100). Anything outside that range is clipped on the bar
    while the numeric label still shows the raw value.
    """
    chart_w = width - layout.label_col_width - layout.right_margin
    height = (
        layout.top_padding
        + layout.bottom_padding
        + layout.row_height * max(1, len(rows))
    )

    drawing = Drawing(width, height)

    # Title + subtitle
    drawing.add(String(
        0, height - layout.title_offset_y, title,
        fontName="Helvetica-Bold",
        fontSize=layout.title_font_size,
        fillColor=Palette.INK_DARK,
    ))
    drawing.add(String(
        0, height - layout.subtitle_offset_y, subtitle,
        fontName="Helvetica",
        fontSize=layout.subtitle_font_size,
        fillColor=Palette.SLATE_500,
    ))

    y0 = height - layout.top_padding
    for idx, (label, value) in enumerate(rows):
        y = y0 - idx * layout.row_height

        # Label on the left
        drawing.add(String(
            0, y + layout.label_y_nudge,
            truncate(label, layout.label_truncate_chars),
            fontName="Helvetica",
            fontSize=layout.label_font_size,
            fillColor=Palette.SLATE_700,
        ))

        # Track
        drawing.add(Rect(
            layout.label_col_width, y, chart_w, layout.bar_height,
            fillColor=Palette.SLATE_50,
            strokeColor=Palette.SLATE_200,
            strokeWidth=layout.bar_stroke_width,
        ))

        # Filled bar
        fill_w = max(0.0, min(chart_w, (value / 100.0) * chart_w))
        drawing.add(Rect(
            layout.label_col_width, y, fill_w, layout.bar_height,
            fillColor=accent, strokeColor=accent, strokeWidth=0,
        ))

        # Value label
        drawing.add(String(
            layout.label_col_width + chart_w + layout.value_label_gap,
            y + layout.value_label_y_nudge,
            f"{value:.1f}%",
            fontName="Helvetica-Bold",
            fontSize=layout.value_font_size,
            fillColor=Palette.INK_DARK,
        ))

    return drawing


def build_kpi_story_chart(
    kpis: list[dict[str, Any]],
    width: float,
    *,
    layout: KpiChartLayout = KPI_CHART,
) -> Drawing:
    """Story chart showing each KPI moving from its current to its target value.

    Only KPIs with a numeric ``baseline_value`` are drawn (max 5).
    ``target_value`` falls back to baseline when missing, producing a
    zero-length segment that still renders cleanly.
    """
    usable = []
    for k in kpis:
        if as_float(k.get("baseline_value")) is not None:
            usable.append(k)
        if len(usable) == 5:
            break

    graph_x = layout.label_col_width + layout.actual_col_width + layout.column_gap
    graph_w = width - graph_x - layout.target_col_width - layout.column_gap
    height = (
        layout.top_padding
        + layout.bottom_padding
        + layout.row_height * max(1, len(usable))
    )

    drawing = Drawing(width, height)

    # Title + subtitle
    drawing.add(String(
        0, height - layout.title_offset_y, "Lectura visual de metas",
        fontName="Helvetica-Bold",
        fontSize=layout.title_font_size,
        fillColor=Palette.INK_DARK,
    ))
    drawing.add(String(
        0, height - layout.subtitle_offset_y,
        "Interpretación simple: la barra conecta el valor actual con la meta "
        "y permite ver la distancia que debe cerrarse.",
        fontName="Helvetica",
        fontSize=layout.subtitle_font_size,
        fillColor=Palette.SLATE_500,
    ))

    # Column headers
    drawing.add(String(
        layout.label_col_width - 6, height - layout.column_header_offset_y, "Actual",
        fontName="Helvetica-Bold",
        fontSize=layout.column_header_font_size,
        fillColor=Palette.SLATE_500,
    ))
    drawing.add(String(
        graph_x + graph_w + 10, height - layout.column_header_offset_y, "Meta",
        fontName="Helvetica-Bold",
        fontSize=layout.column_header_font_size,
        fillColor=Palette.SLATE_500,
    ))

    y0 = height - layout.top_padding
    for idx, kpi in enumerate(usable):
        baseline = as_float(kpi.get("baseline_value"))
        if baseline is None:
            continue
        target = as_float(kpi.get("target_value"))
        final_target = target if target is not None else baseline
        reference = max(abs(baseline), abs(final_target), 1.0)

        actual_x = graph_x + (abs(baseline) / reference) * graph_w
        target_x = graph_x + (abs(final_target) / reference) * graph_w
        y = y0 - idx * layout.row_height

        # Label
        drawing.add(String(
            0, y + layout.label_y_nudge,
            truncate(as_text(kpi.get("name"), "Indicador"), layout.label_truncate_chars),
            fontName="Helvetica",
            fontSize=layout.label_font_size,
            fillColor=Palette.SLATE_700,
        ))

        # Numeric "actual"
        drawing.add(String(
            layout.label_col_width - 6, y + layout.label_y_nudge,
            f"{baseline:,.1f}",
            fontName="Helvetica-Bold",
            fontSize=layout.value_font_size,
            fillColor=Palette.SLATE_700,
        ))

        # Track + travel segment
        drawing.add(Line(
            graph_x, y + layout.track_y_nudge,
            graph_x + graph_w, y + layout.track_y_nudge,
            strokeColor=Palette.SLATE_200,
            strokeWidth=layout.track_stroke_width,
        ))
        drawing.add(Line(
            min(actual_x, target_x), y + layout.track_y_nudge,
            max(actual_x, target_x), y + layout.track_y_nudge,
            strokeColor=Palette.SLATE_500,
            strokeWidth=layout.span_stroke_width,
        ))

        # Dots: actual (gray), target (emerald)
        drawing.add(Circle(
            actual_x, y + layout.track_y_nudge, layout.dot_radius,
            fillColor=Palette.GRAY_BAR, strokeColor=Palette.GRAY_BAR,
        ))
        drawing.add(Circle(
            target_x, y + layout.track_y_nudge, layout.dot_radius,
            fillColor=Palette.EMERALD, strokeColor=Palette.EMERALD,
        ))

        # Numeric "target"
        drawing.add(String(
            graph_x + graph_w + 10, y + layout.label_y_nudge,
            f"{final_target:,.1f}",
            fontName="Helvetica-Bold",
            fontSize=layout.value_font_size,
            fillColor=Palette.EMERALD,
        ))

    return drawing
