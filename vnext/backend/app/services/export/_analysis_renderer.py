"""
Analysis PDF renderer.

This module composes the territorial analysis PDF.

Design direction:
    - Editorial, readable and paper-like.
    - Fewer colored boxes.
    - Clearer section titles for non-technical readers.
    - No methodology reading block.
    - No unclear KPI visual chart.
    - No forced page break between infrastructure and needs.
    - API/DENUE enrichments are used when available.
    - Legacy/reference data remains supported.

Public entry point:
    render_analysis_pdf(analysis, evidence) -> bytes
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

from app.models.db_models import AnalysisRunDB, EvidenceRecordDB

from app.services.export.pdf_common import (
    UW,
    make_doc,
    page_footer,
    rule,
    sp,
)

from app.services.export.content.categories import Severity
from app.services.export.content.narratives import (
    classify_need,
    kpi_rationale,
    need_implication,
    need_why_it_matters,
)
from app.services.export.domain.extractors import (
    extract_api_business_neighborhoods,
    extract_api_business_size_distribution,
    extract_api_business_units,
    extract_api_health_facilities,
    extract_api_schools_count,
    extract_api_sector_distribution,
    extract_api_top_activities,
    extract_economic_sectors,
    extract_estimated_coverage,
    extract_infra_rows,
    extract_metric,
    extract_municipal_coverage,
    extract_social_rows,
    extract_sources,
)
from app.services.export.domain.metric_specs import Metric
from app.services.export.domain.safe_access import (
    as_dict,
    as_float,
    as_list,
    as_text,
)
from app.services.export.layout.charts import build_bar_chart
from app.services.export.layout.styles import build_styles
from app.services.export.layout.tokens import METRIC_CARDS, PANEL, Palette


# ─────────────────────────────────────────────────────────────────────────────
# Editorial color system
# ─────────────────────────────────────────────────────────────────────────────

PAPER_INK = colors.HexColor("#0F172A")
PAPER_TEXT = colors.HexColor("#1E293B")
PAPER_MUTED = colors.HexColor("#64748B")
PAPER_LINE = colors.HexColor("#E2E8F0")
PAPER_SOFT = colors.HexColor("#F8FAFC")
PAPER_BLUE = colors.HexColor("#2563EB")
PAPER_BLUE_DARK = colors.HexColor("#1D4ED8")
PAPER_GREEN = colors.HexColor("#059669")
PAPER_RED = colors.HexColor("#B91C1C")
PAPER_AMBER = colors.HexColor("#B45309")


_SEVERITY_VISUALS: dict[Severity, tuple[colors.Color, colors.Color]] = {
    Severity.HIGH: (PAPER_RED, colors.HexColor("#FEF2F2")),
    Severity.MEDIUM: (PAPER_AMBER, colors.HexColor("#FFFBEB")),
    Severity.LOW: (PAPER_GREEN, colors.HexColor("#ECFDF5")),
}


# ─────────────────────────────────────────────────────────────────────────────
# Generic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _panel(
    flowables: list[Any],
    width: float,
    bg: colors.Color = colors.white,
    border: colors.Color = PAPER_LINE,
    pad: int = PANEL.default_padding,
) -> Table:
    """Wrap flowables in a true single-column panel."""
    table = Table(
        [[flowables]],
        colWidths=[width],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.45, border),
                ("LEFTPADDING", (0, 0), (-1, -1), pad),
                ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                ("TOPPADDING", (0, 0), (-1, -1), pad),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    return table


def _section_header(
    style_map: dict[str, ParagraphStyle],
    title: str,
    subtitle: str | None = None,
) -> list[Any]:
    """Editorial section header with optional explanatory subtitle."""
    title_style = ParagraphStyle(
        f"paper_section_{abs(hash(title))}",
        parent=style_map["section_title"],
        fontName="Helvetica-Bold",
        fontSize=9.2,
        leading=11.2,
        textColor=PAPER_INK,
        spaceAfter=3,
    )

    subtitle_style = ParagraphStyle(
        f"paper_section_subtitle_{abs(hash(title))}",
        parent=style_map["body_sm"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.4,
        textColor=PAPER_MUTED,
        spaceAfter=5,
    )

    items: list[Any] = [Paragraph(title, title_style)]

    if subtitle:
        items.append(Paragraph(subtitle, subtitle_style))

    items.append(rule(PAPER_LINE, 0.65, 0, 8))
    return items


def _resolve_municipality_name(
    analysis: AnalysisRunDB,
    evidence: EvidenceRecordDB | None,
) -> str:
    """Pick the best display name available."""
    candidates = (
        as_text(getattr(evidence, "municipality_name", "")),
        as_text(getattr(analysis, "municipality_name", "")),
        as_text(getattr(analysis, "municipality_id", "Municipio")),
    )

    return next((candidate for candidate in candidates if candidate), "Municipio")


def _safe_delta(
    baseline: float | None,
    target: float | None,
) -> str:
    """Return a human-readable gap between current value and target."""
    if baseline is None or target is None:
        return "Sin dato suficiente"

    delta = target - baseline
    abs_delta = abs(delta)

    if abs_delta < 0.05:
        return "Mantener nivel"

    direction = "Subir" if delta > 0 else "Reducir"
    return f"{direction} {abs_delta:.1f} pts."


def _fmt_int(value: int | None) -> str:
    if value is None:
        return "N/D"

    return f"{value:,}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/D"

    return f"{value:.1f}%"


def _truncate(text: str, limit: int = 42) -> str:
    if len(text) <= limit:
        return text

    return f"{text[:limit - 1]}…"


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

def _build_header(
    style_map: dict[str, ParagraphStyle],
    municipality_name: str,
) -> list[Any]:
    eyebrow_style = ParagraphStyle(
        "paper_eyebrow",
        parent=style_map["tag"],
        fontName="Helvetica-Bold",
        fontSize=7.4,
        leading=9,
        textColor=PAPER_BLUE,
        spaceAfter=6,
    )

    title_style = ParagraphStyle(
        "paper_title",
        parent=style_map["h1"],
        fontName="Helvetica-Bold",
        fontSize=27,
        leading=31,
        textColor=PAPER_INK,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "paper_subtitle",
        parent=style_map["subtle"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=11,
        textColor=PAPER_MUTED,
    )

    return [
        Paragraph("ANÁLISIS TERRITORIAL · VOXPOLÍTICA", eyebrow_style),
        Paragraph(municipality_name, title_style),
        Paragraph("Estado de Tlaxcala, México · Documento estratégico", subtitle_style),
        sp(12),
        rule(PAPER_LINE, 0.7, 0, 12),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Top metrics
# ─────────────────────────────────────────────────────────────────────────────

def _build_metric_cards(
    style_map: dict[str, ParagraphStyle],
    evidence: EvidenceRecordDB | None,
    analysis: AnalysisRunDB,
) -> Table:
    poverty = extract_metric(Metric.POVERTY.value, evidence, analysis)
    population = extract_metric(Metric.POPULATION.value, evidence, analysis)
    internet = extract_metric(Metric.INTERNET.value, evidence, analysis)
    schooling = extract_metric(Metric.SCHOOLING.value, evidence, analysis)

    candidates: list[tuple[str, str]] = []

    if poverty:
        candidates.append(("Pobreza", poverty.text))
    if population:
        candidates.append(("Población", population.text))
    if internet:
        candidates.append(("Internet en hogares", internet.text))
    if schooling:
        candidates.append(("Escolaridad", schooling.text))

    fallback_pool: list[tuple[str, str]] = [
        ("Cobertura municipal", extract_municipal_coverage(evidence)[0]),
        ("Estimación regional", extract_estimated_coverage(evidence)[0]),
    ]

    for fallback in fallback_pool:
        if len(candidates) >= METRIC_CARDS.cards_per_row:
            break
        candidates.append(fallback)

    selected = candidates[: METRIC_CARDS.cards_per_row]

    while len(selected) < METRIC_CARDS.cards_per_row:
        selected.append(("Indicador", "N/D"))

    label_style = ParagraphStyle(
        "paper_metric_label",
        parent=style_map["metric_label"],
        fontName="Helvetica-Bold",
        fontSize=6.7,
        leading=8,
        textColor=PAPER_MUTED,
    )

    value_style = ParagraphStyle(
        "paper_metric_value",
        parent=style_map["metric_value"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=PAPER_INK,
    )

    cells: list[list[Any]] = []

    for label, value in selected:
        cells.append(
            [
                Paragraph(label.upper(), label_style),
                sp(3),
                Paragraph(value, value_style),
            ]
        )

    table = Table(
        [cells],
        colWidths=[UW / METRIC_CARDS.cards_per_row] * METRIC_CARDS.cards_per_row,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEBELOW", (0, 0), (-1, -1), 0.45, PAPER_LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PAPER_LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    return table


# ─────────────────────────────────────────────────────────────────────────────
# Summary and territorial reading
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary_block(
    analysis: AnalysisRunDB,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    if not analysis.executive_summary:
        return []

    summary_style = ParagraphStyle(
        "paper_summary_body",
        parent=style_map["body"],
        fontName="Helvetica",
        fontSize=9.4,
        leading=13,
        textColor=PAPER_TEXT,
    )

    return [
        *_section_header(
            style_map,
            "Resumen territorial",
            "Panorama general del municipio y de sus principales condiciones sociales y económicas.",
        ),
        Paragraph(as_text(analysis.executive_summary), summary_style),
        sp(14),
    ]


def _build_story_block(
    analysis: AnalysisRunDB,
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    poverty = extract_metric(Metric.POVERTY.value, evidence, analysis)
    internet = extract_metric(Metric.INTERNET.value, evidence, analysis)

    sector_rows = extract_api_sector_distribution(evidence)
    legacy_sectors = extract_economic_sectors(evidence)

    if sector_rows:
        sectors_text = ", ".join(row["sector"] for row in sector_rows[:3])
    else:
        sectors_text = " · ".join(legacy_sectors) or "economía local diversificada"

    needs = as_list(analysis.critical_needs)
    top_need = (
        as_text(as_dict(needs[0]).get("title"), "la agenda social prioritaria")
        if needs
        else "la agenda social prioritaria"
    )

    municipality = as_text(
        getattr(analysis, "municipality_name", "")
        or getattr(analysis, "municipality_id", "El municipio")
    )

    poverty_text = poverty.text if poverty else "N/D"
    internet_text = internet.text if internet else "N/D"

    business_units = extract_api_business_units(evidence)

    if business_units is not None and sector_rows:
        main_sector = sector_rows[0]
        economic_sentence = (
            f"Además, la consulta DENUE identifica {_fmt_int(business_units)} unidades económicas en el área analizada, "
            f"con predominio de {main_sector['sector']} ({_fmt_pct(main_sector['share_pct'])})."
        )
    else:
        economic_sentence = f"La base económica se apoya en {sectors_text}."

    narrative = (
        f"{municipality} presenta una tensión entre actividad económica visible y bienestar social todavía limitado. "
        f"La pobreza se ubica en {poverty_text} y la conectividad en hogares en {internet_text}. "
        f"{economic_sentence} "
        f"El principal reto territorial identificado es {top_need}. "
        f"La lectura central es que el municipio cuenta con activos productivos, pero necesita convertirlos "
        f"con mayor eficacia en ingreso, protección social y servicios accesibles."
    )

    body_style = ParagraphStyle(
        "paper_story_body",
        parent=style_map["body"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12.8,
        textColor=PAPER_TEXT,
    )

    return [
        *_section_header(
            style_map,
            "Lectura estratégica",
            "Interpretación breve de los datos para orientar decisiones públicas y comunicación territorial.",
        ),
        Paragraph(narrative, body_style),
        sp(14),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Social and infrastructure charts
# ─────────────────────────────────────────────────────────────────────────────

def _build_social_chart(evidence: EvidenceRecordDB | None) -> Drawing | None:
    rows = extract_social_rows(evidence)

    if not rows:
        return None

    return build_bar_chart(
        title="Carencias sociales prioritarias",
        subtitle="Porcentaje estimado de población afectada",
        rows=rows,
        width=UW,
        accent=Palette.RED,
    )


def _build_infra_chart(evidence: EvidenceRecordDB | None) -> Drawing | None:
    rows = extract_infra_rows(evidence)

    if not rows:
        return None

    return build_bar_chart(
        title="Cobertura de servicios básicos",
        subtitle="Porcentaje de cobertura reportada en vivienda y servicios esenciales",
        rows=rows,
        width=UW,
        accent=Palette.EMERALD,
    )


def _build_profile_charts(
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    elems: list[Any] = []

    social_chart = _build_social_chart(evidence)
    infra_chart = _build_infra_chart(evidence)

    if social_chart is None and infra_chart is None:
        return elems

    elems.extend(
        _section_header(
            style_map,
            "Diagnóstico social y servicios básicos",
            "Indicadores que muestran presión social, carencias y condiciones de infraestructura.",
        )
    )

    if social_chart is not None:
        elems.extend([social_chart, sp(10)])

    if infra_chart is not None:
        elems.extend([infra_chart, sp(12)])

    return elems


# ─────────────────────────────────────────────────────────────────────────────
# API service availability: health / education
# ─────────────────────────────────────────────────────────────────────────────

def _build_api_service_context(
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    health_count = extract_api_health_facilities(evidence)
    schools_count = extract_api_schools_count(evidence)

    if health_count is None and schools_count is None:
        return []

    label_style = ParagraphStyle(
        "api_service_label",
        parent=style_map["metric_label"],
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=8.2,
        textColor=PAPER_MUTED,
    )

    value_style = ParagraphStyle(
        "api_service_value",
        parent=style_map["metric_value"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=PAPER_INK,
    )

    note_style = ParagraphStyle(
        "api_service_note",
        parent=style_map["body_sm"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.5,
        textColor=PAPER_MUTED,
    )

    rows = [
        [
            [
                Paragraph("REGISTROS RELACIONADOS CON SALUD", label_style),
                sp(3),
                Paragraph(_fmt_int(health_count), value_style),
            ],
            [
                Paragraph("REGISTROS EDUCATIVOS", label_style),
                sp(3),
                Paragraph(_fmt_int(schools_count), value_style),
            ],
        ]
    ]

    table = Table(
        rows,
        colWidths=[UW / 2, UW / 2],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.35, PAPER_LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, PAPER_LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    return [
        *_section_header(
            style_map,
            "Servicios observados en DENUE",
            "Conteo complementario de unidades relacionadas con salud y educación dentro del área consultada.",
        ),
        table,
        sp(6),
        Paragraph(
            "Nota: estos conteos provienen de registros DENUE y deben leerse como establecimientos o unidades económicas relacionadas, no como capacidad efectiva de atención.",
            note_style,
        ),
        sp(12),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Critical needs
# ─────────────────────────────────────────────────────────────────────────────

def _build_needs_cards(
    analysis: AnalysisRunDB,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    needs = as_list(analysis.critical_needs)

    if not needs:
        return []

    elems: list[Any] = list(
        _section_header(
            style_map,
            "Prioridades de atención",
            "Problemas que requieren intervención focalizada por su impacto social o territorial.",
        )
    )

    title_style_base = ParagraphStyle(
        "paper_need_title_base",
        parent=style_map["need_title"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11.5,
        textColor=PAPER_INK,
    )

    meta_style_base = ParagraphStyle(
        "paper_need_meta_base",
        parent=style_map["need_meta"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=9,
        textColor=PAPER_MUTED,
    )

    description_style = ParagraphStyle(
        "paper_need_description",
        parent=style_map["body"],
        fontName="Helvetica",
        fontSize=8.6,
        leading=11.6,
        textColor=PAPER_TEXT,
    )

    support_style = ParagraphStyle(
        "paper_need_support",
        parent=style_map["body_sm"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=9.2,
        textColor=PAPER_MUTED,
    )

    needs_to_render = needs[:4]

    for index, raw_need in enumerate(needs_to_render, start=1):
        need = as_dict(raw_need)

        title = as_text(need.get("title"), "Necesidad prioritaria")
        description = as_text(need.get("description"))
        urgency = as_text(need.get("urgency"))
        evidence_line = as_text(need.get("evidence"))
        affected = as_float(need.get("affected_population_pct"))
        severity = Severity.from_text(as_text(need.get("severity"), "media"))
        category = classify_need(title, description)

        severity_color, _ = _SEVERITY_VISUALS.get(
            severity,
            _SEVERITY_VISUALS[Severity.MEDIUM],
        )

        affected_text = (
            f"{affected:.0f}% de población afectada"
            if affected is not None
            else "Población afectada: N/D"
        )

        severity_label = f"Prioridad {severity.value.lower()}"

        if urgency:
            severity_label = f"{severity_label} · {urgency}"

        title_style = ParagraphStyle(
            f"paper_need_title_{index}",
            parent=title_style_base,
            textColor=PAPER_INK,
        )

        meta_style = ParagraphStyle(
            f"paper_need_meta_{index}",
            parent=meta_style_base,
            textColor=severity_color,
        )

        header = Table(
            [
                [
                    Paragraph(title, title_style),
                    Paragraph(affected_text, meta_style),
                ]
            ],
            colWidths=[UW * 0.67, UW * 0.23],
        )

        header.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ]
            )
        )

        parts: list[Any] = [
            header,
            sp(3),
            Paragraph(severity_label.upper(), meta_style),
        ]

        if description:
            parts.extend(
                [
                    sp(5),
                    Paragraph(description, description_style),
                ]
            )

        parts.extend(
            [
                sp(5),
                Paragraph(
                    f"<b>Por qué importa:</b> {need_why_it_matters(category)}",
                    support_style,
                ),
                sp(2),
                Paragraph(
                    need_implication(category, severity),
                    support_style,
                ),
            ]
        )

        if evidence_line:
            parts.extend(
                [
                    sp(2),
                    Paragraph(
                        f"<b>Evidencia complementaria:</b> {evidence_line}",
                        support_style,
                    ),
                ]
            )

        accent_line = Table(
            [
                [
                    "",
                    _panel(
                        parts,
                        UW - 10,
                        colors.white,
                        PAPER_LINE,
                        pad=10,
                    ),
                ]
            ],
            colWidths=[4, UW - 4],
        )

        accent_line.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), severity_color),
                    ("BACKGROUND", (1, 0), (1, 0), colors.white),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        elems.append(accent_line)

        if index < len(needs_to_render):
            elems.append(sp(7))

    elems.append(sp(12))
    return elems


# ─────────────────────────────────────────────────────────────────────────────
# Economic section with DENUE support
# ─────────────────────────────────────────────────────────────────────────────

def _build_horizontal_rank_chart(
    *,
    title: str,
    subtitle: str,
    rows: list[tuple[str, float, str]],
    width: float,
    accent: colors.Color = PAPER_BLUE,
) -> Drawing:
    """
    Draw a compact horizontal rank chart.

    rows:
        [
            ("label", numeric_value_for_bar, "right_label"),
            ...
        ]
    """
    if not rows:
        return Drawing(width, 1)

    row_h = 23
    top = 34
    left_label_w = 160
    right_label_w = 52
    bar_w = max(100, width - left_label_w - right_label_w - 12)
    height = top + len(rows) * row_h + 14

    drawing = Drawing(width, height)

    drawing.add(
        String(
            0,
            height - 12,
            title,
            fontName="Helvetica-Bold",
            fontSize=10,
            fillColor=PAPER_INK,
        )
    )

    drawing.add(
        String(
            0,
            height - 26,
            subtitle,
            fontName="Helvetica",
            fontSize=7.2,
            fillColor=PAPER_MUTED,
        )
    )

    max_value = max([value for _, value, _ in rows], default=100) or 100
    y = height - top - 12

    for index, (label, value, right_label) in enumerate(rows):
        normalized = max(0.0, min(1.0, value / max_value))
        current_bar_w = bar_w * normalized
        color = accent if index == 0 else colors.HexColor("#60A5FA")

        drawing.add(
            String(
                0,
                y + 3,
                _truncate(label, 36),
                fontName="Helvetica",
                fontSize=7.4,
                fillColor=PAPER_TEXT,
            )
        )

        drawing.add(
            Rect(
                left_label_w,
                y,
                bar_w,
                8,
                fillColor=PAPER_SOFT,
                strokeColor=PAPER_LINE,
                strokeWidth=0.3,
            )
        )

        drawing.add(
            Rect(
                left_label_w,
                y,
                current_bar_w,
                8,
                fillColor=color,
                strokeColor=color,
                strokeWidth=0,
            )
        )

        drawing.add(
            String(
                left_label_w + bar_w + 8,
                y + 1,
                right_label,
                fontName="Helvetica-Bold",
                fontSize=7.2,
                fillColor=PAPER_INK,
            )
        )

        y -= row_h

    return drawing


def _build_denue_economic_panel(
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    business_units = extract_api_business_units(evidence)
    sectors = extract_api_sector_distribution(evidence)
    sizes = extract_api_business_size_distribution(evidence)
    activities = extract_api_top_activities(evidence)
    neighborhoods = extract_api_business_neighborhoods(evidence)

    if business_units is None and not sectors and not sizes and not activities:
        return []

    elems: list[Any] = [
        *_section_header(
            style_map,
            "Actividad económica observada",
            "Lectura basada en registros de unidades económicas consultadas en DENUE.",
        )
    ]

    body_style = ParagraphStyle(
        "denue_economic_body",
        parent=style_map["body_sm"],
        fontName="Helvetica",
        fontSize=8.1,
        leading=10.7,
        textColor=PAPER_TEXT,
    )

    summary_parts: list[str] = []

    if business_units is not None:
        summary_parts.append(
            f"El área consultada concentra <b>{_fmt_int(business_units)}</b> unidades económicas registradas en DENUE."
        )

    if sectors:
        top_sector = sectors[0]
        summary_parts.append(
            f"La estructura económica observada está dominada por <b>{top_sector['sector']}</b> "
            f"({_fmt_pct(top_sector['share_pct'])} de los registros)."
        )

    if sizes:
        top_size = sizes[0]
        summary_parts.append(
            f"Predominan los establecimientos de <b>{top_size['size']}</b> "
            f"({_fmt_pct(top_size['share_pct'])}), lo que sugiere una economía local altamente atomizada."
        )

    if summary_parts:
        elems.append(Paragraph(" ".join(summary_parts), body_style))
        elems.append(sp(10))

    if sectors:
        sector_rows = [
            (
                row["sector"],
                float(row["share_pct"]),
                f"{row['share_pct']:.1f}%",
            )
            for row in sectors[:7]
        ]

        elems.append(
            _build_horizontal_rank_chart(
                title="Distribución por sector",
                subtitle="Participación porcentual de establecimientos observados en DENUE",
                rows=sector_rows,
                width=UW,
                accent=PAPER_BLUE,
            )
        )
        elems.append(sp(10))

    if activities:
        activity_rows = [
            (
                row["activity"],
                float(row["count"]),
                str(row["count"]),
            )
            for row in activities[:7]
        ]

        elems.append(
            _build_horizontal_rank_chart(
                title="Actividades con mayor presencia",
                subtitle="Número de establecimientos por actividad específica",
                rows=activity_rows,
                width=UW,
                accent=PAPER_GREEN,
            )
        )
        elems.append(sp(10))

    if sizes:
        size_rows = [
            (
                row["size"],
                float(row["share_pct"]),
                f"{row['share_pct']:.1f}%",
            )
            for row in sizes[:5]
        ]

        elems.append(
            _build_horizontal_rank_chart(
                title="Tamaño de los establecimientos",
                subtitle="Distribución porcentual por estrato de personal ocupado",
                rows=size_rows,
                width=UW,
                accent=PAPER_AMBER,
            )
        )
        elems.append(sp(10))

    if neighborhoods:
        neighborhood_rows = [
            (
                row["neighborhood"],
                float(row["count"]),
                str(row["count"]),
            )
            for row in neighborhoods[:6]
        ]

        elems.append(
            _build_horizontal_rank_chart(
                title="Concentración territorial de unidades económicas",
                subtitle="Colonias o zonas con mayor número de registros DENUE",
                rows=neighborhood_rows,
                width=UW,
                accent=PAPER_BLUE_DARK,
            )
        )
        elems.append(sp(12))

    return elems


def _build_legacy_economic_panel(
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    sectors = extract_economic_sectors(evidence)

    if not sectors:
        return []

    ranked = [
        (sector, float(max(35, 100 - index * 18)), str(max(35, 100 - index * 18)))
        for index, sector in enumerate(sectors[:5])
    ]

    interpretation_style = ParagraphStyle(
        "paper_economic_interpretation",
        parent=style_map["body_sm"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=PAPER_TEXT,
    )

    top_sectors = ", ".join([sector for sector, _, _ in ranked[:3]])

    interpretation = (
        f"La economía local se concentra principalmente en {top_sectors}. "
        f"Estos sectores deben leerse como puntos de entrada para empleo, formalización, capacitación "
        f"y vinculación con pequeños negocios."
    )

    return [
        *_section_header(
            style_map,
            "Actividad económica local",
            "Sectores que explican la base productiva del municipio y orientan posibles acciones de desarrollo.",
        ),
        _build_horizontal_rank_chart(
            title="Sectores económicos de referencia",
            subtitle="Ranking referencial cuando no existe consulta DENUE enriquecida",
            rows=ranked,
            width=UW,
            accent=PAPER_BLUE,
        ),
        sp(8),
        Paragraph(interpretation, interpretation_style),
        sp(14),
    ]


def _build_economic_panel(
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    denue_panel = _build_denue_economic_panel(evidence, style_map)

    if denue_panel:
        return denue_panel

    return _build_legacy_economic_panel(evidence, style_map)


# ─────────────────────────────────────────────────────────────────────────────
# Opportunities
# ─────────────────────────────────────────────────────────────────────────────

def _build_opportunities_section(
    analysis: AnalysisRunDB,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    opportunities = [
        as_text(item)
        for item in as_list(analysis.opportunities)
        if as_text(item)
    ]

    if not opportunities:
        return []

    bullet_style = ParagraphStyle(
        "paper_opportunity_bullet",
        parent=style_map["bullet"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.8,
        textColor=PAPER_TEXT,
        leftIndent=8,
        firstLineIndent=-6,
        spaceAfter=4,
    )

    elems: list[Any] = [
        *_section_header(
            style_map,
            "Oportunidades de acción",
            "Áreas donde los datos sugieren posibilidad de intervención, inversión o fortalecimiento institucional.",
        )
    ]

    for item in opportunities[:6]:
        elems.append(Paragraph(f"• {item}", bullet_style))

    elems.append(sp(12))
    return elems


# ─────────────────────────────────────────────────────────────────────────────
# Goals table
# ─────────────────────────────────────────────────────────────────────────────

def _build_goals_table(
    analysis: AnalysisRunDB,
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> tuple[list[Any], list[dict[str, Any]]]:
    board = as_dict(analysis.kpi_board)
    kpis = [as_dict(item) for item in as_list(board.get("kpis"))][:6]

    if not kpis:
        return [], []

    sectors_api = extract_api_sector_distribution(evidence)
    sectors_legacy = extract_economic_sectors(evidence)

    if sectors_api:
        sectors = [row["sector"] for row in sectors_api[:3]]
    else:
        sectors = sectors_legacy

    opportunities = [
        as_text(item)
        for item in as_list(analysis.opportunities)
        if as_text(item)
    ]

    header_style = ParagraphStyle(
        "paper_goals_header",
        parent=style_map["table_h"],
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=9.5,
        textColor=PAPER_INK,
    )

    cell_style = ParagraphStyle(
        "paper_goals_cell",
        parent=style_map["table_cell"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.8,
        textColor=PAPER_TEXT,
    )

    cell_center_style = ParagraphStyle(
        "paper_goals_cell_center",
        parent=style_map["table_cell_center"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.8,
        textColor=PAPER_TEXT,
        alignment=1,
    )

    emphasis_center_style = ParagraphStyle(
        "paper_goals_emphasis_center",
        parent=cell_center_style,
        fontName="Helvetica-Bold",
        textColor=PAPER_BLUE_DARK,
    )

    rows: list[list[Any]] = [
        [
            Paragraph("Indicador", header_style),
            Paragraph("Situación actual", header_style),
            Paragraph("Resultado esperado", header_style),
            Paragraph("Cambio necesario", header_style),
            Paragraph("Justificación", header_style),
        ]
    ]

    usable: list[dict[str, Any]] = []

    for kpi in kpis:
        name = as_text(kpi.get("name"), "Indicador")
        baseline = as_float(kpi.get("baseline_value"))
        target = as_float(kpi.get("target_value"))
        unit = as_text(kpi.get("baseline_unit"))

        rationale = kpi_rationale(
            name,
            baseline=baseline,
            target=target,
            unit=unit,
            sectors=sectors,
            opportunities=opportunities,
        )

        base_text = "N/D" if baseline is None else f"{baseline:,.1f} {unit}".strip()
        target_text = "N/D" if target is None else f"{target:,.1f} {unit}".strip()
        change_text = _safe_delta(baseline, target)

        rows.append(
            [
                Paragraph(name, cell_style),
                Paragraph(base_text, cell_center_style),
                Paragraph(target_text, emphasis_center_style),
                Paragraph(change_text, cell_center_style),
                Paragraph(rationale, cell_style),
            ]
        )

        if baseline is not None:
            usable.append(kpi)

    table = Table(
        rows,
        colWidths=[UW * 0.25, UW * 0.14, UW * 0.15, UW * 0.15, UW * 0.31],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PAPER_SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), PAPER_INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (3, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.35, PAPER_LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER_SOFT]),
            ]
        )
    )

    elems = [
        *_section_header(
            style_map,
            "Metas prioritarias",
            "Cada fila compara el punto de partida con el resultado esperado y explica por qué ese cambio importa.",
        ),
        table,
        sp(12),
    ]

    return elems, usable


# ─────────────────────────────────────────────────────────────────────────────
# Sources
# ─────────────────────────────────────────────────────────────────────────────

def _build_sources_panel(
    evidence: EvidenceRecordDB | None,
    analysis: AnalysisRunDB,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    sources = extract_sources(evidence)

    if not sources:
        return []

    source_text_style = ParagraphStyle(
        "paper_sources_text",
        parent=style_map["body_sm"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.4,
        textColor=PAPER_TEXT,
    )

    items: list[Any] = []

    for src in sources[:10]:
        items.append(Paragraph(f"• {src}", source_text_style))

    return [
        *_section_header(
            style_map,
            "Fuentes",
            "Bases utilizadas para construir el análisis territorial.",
        ),
        _panel(
            items,
            UW,
            colors.white,
            PAPER_LINE,
            pad=12,
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_analysis_pdf(
    analysis: AnalysisRunDB,
    evidence: EvidenceRecordDB | None,
) -> bytes:
    """Build the full analysis PDF and return its bytes."""
    municipality_name = _resolve_municipality_name(analysis, evidence)
    style_map = build_styles()

    buf = BytesIO()
    doc = make_doc(buf, f"Analisis territorial - {municipality_name}")

    elems: list[Any] = []

    elems.extend(_build_header(style_map, municipality_name))

    elems.extend(
        [
            _build_metric_cards(style_map, evidence, analysis),
            sp(16),
        ]
    )

    elems.extend(_build_summary_block(analysis, style_map))
    elems.extend(_build_story_block(analysis, evidence, style_map))
    elems.extend(_build_profile_charts(evidence, style_map))
    elems.extend(_build_api_service_context(evidence, style_map))
    elems.extend(_build_needs_cards(analysis, style_map))
    elems.extend(_build_economic_panel(evidence, style_map))
    elems.extend(_build_opportunities_section(analysis, style_map))

    goal_elems, _ = _build_goals_table(analysis, evidence, style_map)
    elems.extend(goal_elems)

    elems.extend(_build_sources_panel(evidence, analysis, style_map))

    doc.build(
        elems,
        onFirstPage=page_footer,
        onLaterPages=page_footer,
    )

    return buf.getvalue()