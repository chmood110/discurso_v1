from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, Table, TableStyle

from app.models.db_models import AnalysisRunDB, EvidenceRecordDB
from app.services.export.pdf_common import (
    EMERALD,
    SLATE_50,
    SLATE_200,
    SLATE_500,
    SLATE_700,
    SLATE_900,
    UW,
    make_doc,
    page_footer,
    quality_disclaimer_block,
    rule,
    sp,
    styles,
)

RED = colors.HexColor("#DC2626")
BLUE = colors.HexColor("#2563EB")
VIOLET = colors.HexColor("#7C3AED")
AMBER = colors.HexColor("#D97706")
GREEN_BG = colors.HexColor("#EAF5F0")
GREEN_LINE = colors.HexColor("#CDE6D9")
BLUE_BG = colors.HexColor("#EEF4FF")
BLUE_LINE = colors.HexColor("#C8D8FF")
RED_BG = colors.HexColor("#FEECEC")
RED_LINE = colors.HexColor("#F4C7C7")
AMBER_BG = colors.HexColor("#FFF7E8")
AMBER_LINE = colors.HexColor("#F6D9A8")
GRAY_BAR = colors.HexColor("#CBD5E1")
PANEL_BG = colors.HexColor("#F8FAFC")
PANEL_LINE = colors.HexColor("#E2E8F0")
INK_DARK = colors.HexColor("#0F172A")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        clean = value.strip()
        return clean if clean else default
    clean = str(value).strip()
    return clean if clean else default


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _truncate(text: str, limit: int) -> str:
    clean = _text(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def _style_map() -> dict[str, ParagraphStyle]:
    base = styles()

    def ensure(name: str, style: ParagraphStyle) -> None:
        if name not in base:
            base[name] = style

    ensure(
        "tag",
        ParagraphStyle(
            "tag",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=EMERALD,
        ),
    )
    ensure(
        "h1",
        ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=INK_DARK,
        ),
    )
    ensure(
        "subtle",
        ParagraphStyle(
            "subtle",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=SLATE_500,
        ),
    )
    ensure(
        "section_title",
        ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=INK_DARK,
            spaceAfter=2,
        ),
    )
    ensure(
        "body",
        ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            textColor=SLATE_700,
        ),
    )
    ensure(
        "body_sm",
        ParagraphStyle(
            "body_sm",
            fontName="Helvetica",
            fontSize=8.2,
            leading=11,
            textColor=SLATE_500,
        ),
    )
    ensure(
        "bullet",
        ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=SLATE_700,
        ),
    )
    ensure(
        "table_h",
        ParagraphStyle(
            "table_h",
            fontName="Helvetica-Bold",
            fontSize=8.4,
            leading=10.5,
            textColor=INK_DARK,
        ),
    )
    ensure(
        "table_h_center",
        ParagraphStyle(
            "table_h_center",
            parent=base["table_h"],
            alignment=1,
        ),
    )
    ensure(
        "table_cell",
        ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=8.35,
            leading=10.3,
            textColor=SLATE_700,
        ),
    )
    ensure(
        "table_cell_center",
        ParagraphStyle(
            "table_cell_center",
            parent=base["table_cell"],
            alignment=1,
        ),
    )
    ensure(
        "metric_value",
        ParagraphStyle(
            "metric_value",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            alignment=1,
            textColor=INK_DARK,
        ),
    )
    ensure(
        "metric_label",
        ParagraphStyle(
            "metric_label",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=SLATE_500,
        ),
    )
    ensure(
        "kicker",
        ParagraphStyle(
            "kicker",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=SLATE_500,
        ),
    )
    ensure(
        "need_title",
        ParagraphStyle(
            "need_title",
            fontName="Helvetica-Bold",
            fontSize=10.8,
            leading=13,
            textColor=INK_DARK,
        ),
    )
    ensure(
        "need_meta",
        ParagraphStyle(
            "need_meta",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=SLATE_700,
        ),
    )
    return base


def _panel(flowables: list[Any], width: float, bg: colors.Color, border: colors.Color, pad: int = 10) -> Table:
    table = Table([[[item] for item in flowables]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.6, border),
                ("LEFTPADDING", (0, 0), (-1, -1), pad),
                ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                ("TOPPADDING", (0, 0), (-1, -1), pad),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
            ]
        )
    )
    return table


def _find_metric(container: dict[str, Any], aliases: list[str]) -> dict[str, Any]:
    for alias in aliases:
        value = container.get(alias)
        if isinstance(value, dict) and value:
            return value
    return {}


def _extract_population(evidence: EvidenceRecordDB | None, analysis: AnalysisRunDB) -> tuple[str | None, float | None]:
    if evidence:
        social = _as_dict(evidence.social_data)
        metric = _find_metric(social, ["population", "population_total", "total_population", "population_2020"])
        n = _num(metric.get("value"))
        if n is not None:
            return f"{n:,.1f}", n
    demo = _as_dict(analysis.demographic_profile)
    metric = _find_metric(demo, ["population", "population_total", "total_population", "population_2020"])
    n = _num(metric.get("value"))
    return (f"{n:,.1f}" if n is not None else None), n


def _extract_schooling(evidence: EvidenceRecordDB | None, analysis: AnalysisRunDB) -> tuple[str | None, float | None]:
    if evidence:
        social = _as_dict(evidence.social_data)
        metric = _find_metric(
            social,
            ["schooling_years_avg", "average_schooling_years", "schooling_avg_years", "avg_schooling_years"],
        )
        n = _num(metric.get("value"))
        if n is not None:
            return f"{n:.1f}", n
    demo = _as_dict(analysis.demographic_profile)
    metric = _find_metric(
        demo,
        ["schooling_years_avg", "average_schooling_years", "schooling_avg_years", "avg_schooling_years"],
    )
    n = _num(metric.get("value", metric.get("avg")))
    return (f"{n:.1f}" if n is not None else None), n


def _extract_confidence(evidence: EvidenceRecordDB | None, analysis: AnalysisRunDB) -> tuple[str, float | None]:
    confidence = evidence.overall_confidence if evidence else getattr(analysis, "overall_confidence", None)
    n = _num(confidence)
    if n is None:
        return "N/D", None
    if n <= 1:
        n *= 100
    return f"{n:.0f}%", n


def _extract_poverty(evidence: EvidenceRecordDB | None) -> tuple[str | None, float | None]:
    if not evidence:
        return None, None
    social = _as_dict(evidence.social_data)
    poverty = _find_metric(social, ["poverty_rate_pct", "poverty_pct", "multidimensional_poverty_pct"])
    n = _num(poverty.get("value"))
    return (f"{n:.1f}%" if n is not None else None), n


def _extract_internet(evidence: EvidenceRecordDB | None, analysis: AnalysisRunDB) -> tuple[str | None, float | None]:
    if evidence:
        infra = _as_dict(evidence.infrastructure_data)
        metric = _find_metric(infra, ["internet_households_pct", "internet_access_pct", "internet_pct"])
        n = _num(metric.get("value"))
        if n is not None:
            return f"{n:.1f}%", n
    infra = _as_dict(analysis.infrastructure_gaps)
    metric = _find_metric(infra, ["internet_households_pct", "internet_access_pct", "internet_pct"])
    n = _num(metric.get("value"))
    return (f"{n:.1f}%" if n is not None else None), n


def _extract_quality_label(evidence: EvidenceRecordDB | None) -> str:
    if not evidence:
        return "Sin evidencia adjunta"
    return _text(evidence.quality_label, "Sin etiqueta")


def _extract_municipal_coverage(evidence: EvidenceRecordDB | None) -> tuple[str, float | None]:
    if not evidence:
        return "N/D", None
    n = _num(evidence.municipal_coverage_pct)
    return (f"{n:.0f}%" if n is not None else "N/D"), n


def _extract_estimated_coverage(evidence: EvidenceRecordDB | None) -> tuple[str, float | None]:
    if not evidence:
        return "N/D", None
    n = _num(evidence.estimated_coverage_pct)
    return (f"{n:.0f}%" if n is not None else "N/D"), n


def _extract_economic_sectors_list(evidence: EvidenceRecordDB | None) -> list[str]:
    if not evidence:
        return []
    econ = _as_dict(evidence.economic_data)
    sectors = econ.get("main_sectors") or econ.get("sectors")
    if isinstance(sectors, list):
        return [_text(s) for s in sectors if _text(s)]
    if isinstance(sectors, str):
        return [s.strip() for s in sectors.split("·") if s.strip()]
    main_activity = _as_dict(econ.get("main_activity"))
    value = _text(main_activity.get("value"))
    return [value] if value else []


def _extract_social_profile_rows(evidence: EvidenceRecordDB | None) -> list[tuple[str, float]]:
    if not evidence:
        return []

    social = _as_dict(evidence.social_data)
    alias_sets = [
        ("Carencia seguridad social", ["lack_social_security_pct", "social_security_lack_pct"]),
        ("Carencia acceso a salud", ["lack_health_access_pct", "health_access_lack_pct"]),
        ("Inseguridad alimentaria", ["food_insecurity_pct", "food_lack_pct"]),
        ("Rezago educativo", ["educational_lag_pct", "education_lag_pct"]),
        ("Calidad de vivienda", ["housing_quality_pct", "housing_quality_lack_pct"]),
        ("Servicios básicos vivienda", ["basic_services_housing_pct", "housing_services_lack_pct"]),
    ]

    rows: list[tuple[str, float]] = []
    for label, aliases in alias_sets:
        raw_dict = _find_metric(social, aliases)
        value = _num(raw_dict.get("value"))
        if value is not None:
            rows.append((label, value))
    return rows


def _extract_infra_rows(evidence: EvidenceRecordDB | None) -> list[tuple[str, float]]:
    if not evidence:
        return []

    infra = _as_dict(evidence.infrastructure_data)
    alias_sets = [
        ("Internet en hogares", ["internet_households_pct", "internet_access_pct", "internet_pct"]),
        ("Agua potable", ["water_households_pct", "water_access_pct"]),
        ("Drenaje", ["drainage_households_pct", "drainage_access_pct"]),
        ("Electricidad", ["electricity_households_pct", "electricity_access_pct"]),
    ]

    rows: list[tuple[str, float]] = []
    for label, aliases in alias_sets:
        raw_dict = _find_metric(infra, aliases)
        value = _num(raw_dict.get("value"))
        if value is not None:
            rows.append((label, value))
    return rows


def _extract_sources(evidence: EvidenceRecordDB | None) -> list[str]:
    if not evidence:
        return []
    values = [_text(x) for x in _as_list(evidence.sources_used) if _text(x)]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _need_why_it_matters(title: str, description: str) -> str:
    low = f"{title} {description}".lower()
    if "pobreza" in low:
        return "Condiciona ingreso, consumo, continuidad educativa y capacidad de respuesta del hogar ante shocks."
    if "informal" in low or "seguridad social" in low:
        return "Eleva vulnerabilidad laboral y reduce protección frente a enfermedad, desempleo y vejez."
    if "salud" in low:
        return "Afecta atención oportuna, gasto de bolsillo y resiliencia del hogar ante episodios críticos."
    if "internet" in low or "conectividad" in low:
        return "Limita acceso a educación, empleo, trámites y servicios digitales."
    return "Concentra impacto cotidiano sobre bienestar, acceso a servicios y estabilidad económica del hogar."


def _need_implication(title: str, severity: str) -> str:
    sev = severity.upper()
    low = title.lower()
    if "pobreza" in low:
        return f"Implicación estratégica ({sev}): requiere paquete integral de ingreso, servicios y focalización territorial."
    if "informal" in low or "seguridad social" in low:
        return f"Implicación estratégica ({sev}): conviene articular formalización, empleo local y protección social."
    if "salud" in low:
        return f"Implicación estratégica ({sev}): debe priorizarse cobertura efectiva, cercanía operativa y continuidad."
    return f"Implicación estratégica ({sev}): requiere intervención pública focalizada y seguimiento verificable."


def _kpi_rationale(name: str, baseline: float | None, target: float | None, unit: str, sectors: list[str], opportunities: list[str]) -> str:
    low = name.lower()
    sectors_text = ", ".join(sectors[:2]) if sectors else "la economía local"
    opp_text = opportunities[0] if opportunities else ""

    if "pobreza" in low:
        return "La mejora depende de combinar ingreso, acceso a servicios y reducción de vulnerabilidad social."
    if "informal" in low or "empleo" in low:
        return f"El avance exige formalización productiva y encadenamientos con {sectors_text}."
    if "salud" in low:
        return "La reducción exige cobertura efectiva, menor fricción de acceso y continuidad en la atención."
    if "internet" in low or "conectividad" in low:
        return "La conectividad tiene efecto multiplicador en educación, empleo, trámites y acceso a servicios."
    if "agua" in low:
        return "La meta debe leerse como sostenimiento de cobertura con mejora de calidad y continuidad."
    if opp_text:
        return opp_text
    if baseline is not None and target is not None and unit:
        return f"Se propone mover el indicador desde {baseline:,.1f} hasta {target:,.1f} {unit} con una meta verificable."
    return "Meta alineada al diagnóstico territorial y diseñada para seguimiento verificable."


def _build_metric_cards(style_map: dict[str, ParagraphStyle], evidence: EvidenceRecordDB | None, analysis: AnalysisRunDB) -> Table:
    poverty_text, _ = _extract_poverty(evidence)
    population_text, _ = _extract_population(evidence, analysis)
    internet_text, _ = _extract_internet(evidence, analysis)
    confidence_text, confidence_num = _extract_confidence(evidence, analysis)
    schooling_text, _ = _extract_schooling(evidence, analysis)

    candidates: list[tuple[str, str, colors.Color]] = []
    if poverty_text:
        candidates.append(("Pobreza", poverty_text, RED))
    if population_text:
        candidates.append(("Población", population_text, BLUE))
    if internet_text:
        candidates.append(("Internet", internet_text, EMERALD))
    if schooling_text:
        candidates.append(("Escolaridad", schooling_text, VIOLET))
    if confidence_num is not None:
        candidates.append(("Confianza", confidence_text, EMERALD))

    selected = candidates[:4]
    fallback_pool = [
        ("Cobertura municipal", _extract_municipal_coverage(evidence)[0], EMERALD),
        ("Estimado regional", _extract_estimated_coverage(evidence)[0], AMBER),
    ]
    idx = 0
    while len(selected) < 4 and idx < len(fallback_pool):
        selected.append(fallback_pool[idx])
        idx += 1

    cells = []
    for label, value, accent in selected:
        cells.append(
            [
                Paragraph(
                    value,
                    ParagraphStyle(
                        f"metric_value_{label}",
                        parent=style_map["metric_value"],
                        textColor=accent,
                    ),
                ),
                Paragraph(label, style_map["metric_label"]),
            ]
        )

    table = Table([cells], colWidths=[UW / 4] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, SLATE_200),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return table


def _build_quality_band(style_map: dict[str, ParagraphStyle], evidence: EvidenceRecordDB | None, analysis: AnalysisRunDB) -> Table:
    confidence_text, _ = _extract_confidence(evidence, analysis)
    municipal_text, _ = _extract_municipal_coverage(evidence)
    estimated_text, _ = _extract_estimated_coverage(evidence)
    quality_text = _extract_quality_label(evidence)

    rows = [[
        [
            Paragraph(
                confidence_text,
                ParagraphStyle("qv1", parent=style_map["metric_value"], textColor=EMERALD, fontSize=15, leading=17),
            ),
            Paragraph("Confianza", style_map["metric_label"]),
        ],
        [
            Paragraph(
                municipal_text,
                ParagraphStyle("qv2", parent=style_map["metric_value"], textColor=EMERALD, fontSize=15, leading=17),
            ),
            Paragraph("Cobertura municipal", style_map["metric_label"]),
        ],
        [
            Paragraph(
                estimated_text,
                ParagraphStyle("qv3", parent=style_map["metric_value"], textColor=AMBER, fontSize=15, leading=17),
            ),
            Paragraph("Estimado regional", style_map["metric_label"]),
        ],
        [
            Paragraph(
                quality_text,
                ParagraphStyle(
                    "qv4",
                    parent=style_map["metric_label"],
                    alignment=1,
                    fontName="Helvetica-Bold",
                    textColor=INK_DARK,
                ),
            ),
            Paragraph("Calidad metodológica", style_map["metric_label"]),
        ],
    ]]

    table = Table(rows, colWidths=[UW / 4] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GREEN_BG),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, GREEN_LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return table


def _build_story_block(analysis: AnalysisRunDB, evidence: EvidenceRecordDB | None, style_map: dict[str, ParagraphStyle]) -> list[Any]:
    poverty_text, _ = _extract_poverty(evidence)
    internet_text, _ = _extract_internet(evidence, analysis)
    sectors = " · ".join(_extract_economic_sectors_list(evidence)) or "economía local diversificada"
    needs = _as_list(analysis.critical_needs)
    top_need = _text(_as_dict(needs[0]).get("title"), "la agenda social prioritaria") if needs else "la agenda social prioritaria"
    municipality = _text(getattr(analysis, "municipality_id", "El municipio"))

    narrative = (
        f"{municipality} presenta una tensión clara entre actividad económica visible y bienestar social limitado. "
        f"La pobreza se ubica en {poverty_text or 'N/D'} y la conectividad en hogares en {internet_text or 'N/D'}, "
        f"por lo que el territorio combina presión social alta con capacidad productiva incompleta. La base económica se "
        f"apoya en {sectors}, pero el principal cuello de botella es {top_need}. En términos analíticos, la historia del "
        f"municipio es simple: existen activos productivos, pero todavía no se transforman de forma suficiente en bienestar verificable."
    )

    return [
        Paragraph("LECTURA TERRITORIAL", style_map["section_title"]),
        rule(EMERALD, 1.5, 2, 8),
        _panel([Paragraph(narrative, style_map["body"])], UW, BLUE_BG, BLUE_LINE, pad=12),
        sp(12),
    ]


def _build_needs_cards(analysis: AnalysisRunDB, style_map: dict[str, ParagraphStyle]) -> list[Any]:
    needs = _as_list(analysis.critical_needs)
    if not needs:
        return []

    elems: list[Any] = [
        Paragraph("NECESIDADES CRÍTICAS", style_map["section_title"]),
        rule(EMERALD, 1.5, 2, 8),
    ]

    severity_map = {
        "alta": (RED_BG, RED_LINE, colors.HexColor("#991B1B")),
        "media": (AMBER_BG, AMBER_LINE, colors.HexColor("#92400E")),
        "baja": (SLATE_50, SLATE_200, colors.HexColor("#334155")),
    }

    for index, raw_need in enumerate(needs[:4], start=1):
        need = _as_dict(raw_need)
        title = _text(need.get("title"), "Necesidad prioritaria")
        severity = _text(need.get("severity"), "media").lower()
        description = _text(need.get("description"))
        urgency = _text(need.get("urgency"))
        evidence_line = _text(need.get("evidence"))
        affected = _num(need.get("affected_population_pct"))

        bg, border, title_color = severity_map.get(severity, severity_map["media"])

        title_left = Paragraph(title, ParagraphStyle(f"need_title_{index}", parent=style_map["need_title"], textColor=title_color))
        meta_right_text = f"{affected:.0f}% población afectada" if affected is not None else "Población afectada: N/D"
        meta_right = Paragraph(
            meta_right_text,
            ParagraphStyle(f"need_topright_{index}", parent=style_map["need_meta"], alignment=2),
        )

        header_table = Table([[title_left, meta_right]], colWidths=[UW * 0.60, UW * 0.25])
        header_table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        meta_left = Paragraph(
            f"Severidad: {severity.upper()}",
            ParagraphStyle(f"need_meta_left_{index}", parent=style_map["need_meta"], textColor=title_color),
        )
        meta_right_2 = Paragraph(
            f"Urgencia: {urgency}" if urgency else "",
            ParagraphStyle(f"need_meta_right_{index}", parent=style_map["need_meta"], alignment=2),
        )
        meta_table = Table([[meta_left, meta_right_2]], colWidths=[UW * 0.30, UW * 0.55])
        meta_table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        parts: list[Any] = [header_table, sp(4), meta_table]
        if description:
            parts.extend([sp(6), Paragraph(description, style_map["body"])])
        parts.extend(
            [
                sp(5),
                Paragraph(f"Por qué importa: {_need_why_it_matters(title, description)}", style_map["body_sm"]),
                sp(3),
                Paragraph(_need_implication(title, severity), style_map["body_sm"]),
            ]
        )
        if evidence_line:
            parts.extend([sp(3), Paragraph(f"Evidencia complementaria: {evidence_line}", style_map["body_sm"])])

        elems.append(_panel(parts, UW, bg, border, pad=11))
        if index < min(4, len(needs)):
            elems.append(sp(8))

    return elems


def _build_bar_chart(
    title: str,
    subtitle: str,
    rows: list[tuple[str, float]],
    width: float,
    accent: colors.Color,
) -> Drawing:
    label_col = 154
    chart_w = width - label_col - 46
    row_h = 22
    top_pad = 42
    bottom_pad = 16
    height = top_pad + bottom_pad + row_h * max(1, len(rows))

    drawing = Drawing(width, height)
    drawing.add(String(0, height - 11, title, fontName="Helvetica-Bold", fontSize=11, fillColor=INK_DARK))
    drawing.add(String(0, height - 24, subtitle, fontName="Helvetica", fontSize=8, fillColor=SLATE_500))

    y0 = height - top_pad
    for idx, (label, value) in enumerate(rows):
        y = y0 - idx * row_h
        drawing.add(String(0, y + 4, _truncate(label, 28), fontName="Helvetica", fontSize=8.2, fillColor=SLATE_700))
        drawing.add(Rect(label_col, y, chart_w, 10, fillColor=SLATE_50, strokeColor=SLATE_200, strokeWidth=0.4))
        fill_w = max(0, min(chart_w, (value / 100.0) * chart_w))
        drawing.add(Rect(label_col, y, fill_w, 10, fillColor=accent, strokeColor=accent, strokeWidth=0))
        drawing.add(String(label_col + chart_w + 6, y + 1.5, f"{value:.1f}%", fontName="Helvetica-Bold", fontSize=8.2, fillColor=INK_DARK))

    return drawing


def _build_kpi_table(
    analysis: AnalysisRunDB,
    evidence: EvidenceRecordDB | None,
    style_map: dict[str, ParagraphStyle],
) -> tuple[list[Any], list[dict[str, Any]]]:
    board = _as_dict(analysis.kpi_board)
    kpis = [_as_dict(x) for x in _as_list(board.get("kpis"))][:6]
    if not kpis:
        return [], []

    sectors = _extract_economic_sectors_list(evidence)
    opportunities = [_text(x) for x in _as_list(analysis.opportunities) if _text(x)]

    rows: list[list[Any]] = [
        [
            Paragraph("Indicador", style_map["table_h"]),
            Paragraph("Línea base", style_map["table_h_center"]),
            Paragraph("Meta", style_map["table_h_center"]),
            Paragraph("Fundamento", style_map["table_h"]),
        ]
    ]

    usable: list[dict[str, Any]] = []
    for kpi in kpis:
        name = _text(kpi.get("name"), "Indicador")
        baseline = _num(kpi.get("baseline_value"))
        target = _num(kpi.get("target_value"))
        unit = _text(kpi.get("baseline_unit"))
        rationale = _kpi_rationale(name, baseline, target, unit, sectors, opportunities)

        base_text = "N/D" if baseline is None else f"{baseline:,.1f} {unit}".strip()
        target_text = "N/D" if target is None else f"{target:,.1f} {unit}".strip()

        rows.append(
            [
                Paragraph(name, style_map["table_cell"]),
                Paragraph(base_text, style_map["table_cell_center"]),
                Paragraph(target_text, style_map["table_cell_center"]),
                Paragraph(rationale, style_map["table_cell"]),
            ]
        )

        if baseline is not None:
            usable.append(kpi)

    table = Table(
        rows,
        colWidths=[UW * 0.31, UW * 0.16, UW * 0.16, UW * 0.37],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK_DARK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("LEADING", (0, 0), (-1, -1), 10.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (2, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.35, SLATE_200),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SLATE_50]),
            ]
        )
    )

    elems = [
        Paragraph("KPIS SMART — METAS VERIFICABLES", style_map["section_title"]),
        rule(EMERALD, 1.5, 2, 8),
        table,
        sp(10),
    ]
    return elems, usable


def _build_kpi_story_chart(kpis: list[dict[str, Any]], width: float) -> Drawing:
    usable = [k for k in kpis if _num(k.get("baseline_value")) is not None][:5]

    left_label_w = 166
    actual_col_w = 52
    target_col_w = 52
    graph_x = left_label_w + actual_col_w + 8
    graph_w = width - graph_x - target_col_w - 8

    row_h = 30
    top_pad = 62
    bottom_pad = 20
    height = top_pad + bottom_pad + row_h * max(1, len(usable))

    drawing = Drawing(width, height)
    drawing.add(String(0, height - 12, "Lectura visual de metas", fontName="Helvetica-Bold", fontSize=11, fillColor=INK_DARK))
    drawing.add(String(0, height - 26, "Interpretación simple: la barra conecta el valor actual con la meta y permite ver la distancia que debe cerrarse.", fontName="Helvetica", fontSize=8, fillColor=SLATE_500))
    drawing.add(String(left_label_w - 6, height - 42, "Actual", fontName="Helvetica-Bold", fontSize=7.6, fillColor=SLATE_500))
    drawing.add(String(graph_x + graph_w + 10, height - 42, "Meta", fontName="Helvetica-Bold", fontSize=7.6, fillColor=SLATE_500))

    y0 = height - top_pad
    for idx, item in enumerate(usable):
        name = _truncate(_text(item.get("name"), "Indicador"), 30)
        baseline = _num(item.get("baseline_value"))
        target = _num(item.get("target_value"))
        if baseline is None:
            continue
        final_target = target if target is not None else baseline
        reference = max(abs(baseline), abs(final_target), 1.0)

        actual_x = graph_x + (abs(baseline) / reference) * graph_w
        target_x = graph_x + (abs(final_target) / reference) * graph_w
        y = y0 - idx * row_h

        drawing.add(String(0, y + 4, name, fontName="Helvetica", fontSize=8.2, fillColor=SLATE_700))
        drawing.add(String(left_label_w - 6, y + 4, f"{baseline:,.1f}", fontName="Helvetica-Bold", fontSize=8.2, fillColor=SLATE_700))
        drawing.add(Line(graph_x, y + 8, graph_x + graph_w, y + 8, strokeColor=SLATE_200, strokeWidth=1))
        drawing.add(Line(min(actual_x, target_x), y + 8, max(actual_x, target_x), y + 8, strokeColor=SLATE_500, strokeWidth=1.3))
        drawing.add(Circle(actual_x, y + 8, 3.2, fillColor=GRAY_BAR, strokeColor=GRAY_BAR))
        drawing.add(Circle(target_x, y + 8, 3.2, fillColor=EMERALD, strokeColor=EMERALD))
        drawing.add(String(graph_x + graph_w + 10, y + 4, f"{final_target:,.1f}", fontName="Helvetica-Bold", fontSize=8.2, fillColor=EMERALD))

    return drawing


def _build_economic_panel(evidence: EvidenceRecordDB | None, style_map: dict[str, ParagraphStyle]) -> list[Any]:
    sectors = _extract_economic_sectors_list(evidence)
    if not sectors:
        return []

    elems: list[Any] = [
        Paragraph("MOTOR ECONÓMICO", style_map["section_title"]),
        rule(EMERALD, 1.5, 2, 8),
    ]

    ranked = [(sector, max(35, 100 - i * 18)) for i, sector in enumerate(sectors[:4])]
    chart = _build_bar_chart(
        "Sectores con capacidad de tracción",
        "Lectura rápida de los motores productivos que sostienen empleo y encadenamientos locales",
        ranked,
        UW,
        BLUE,
    )

    story = (
        "Estos sectores representan la base desde la cual puede construirse una narrativa de crecimiento con impacto local. "
        "La prioridad no es solo producir más, sino traducir esta base económica en empleo, formalización y bienestar."
    )

    elems.extend([chart, sp(6), Paragraph(story, style_map["body_sm"]), sp(12)])
    return elems


def _build_sources_panel(
    evidence: EvidenceRecordDB | None,
    analysis: AnalysisRunDB,
    style_map: dict[str, ParagraphStyle],
) -> list[Any]:
    sources = _extract_sources(evidence)
    if not sources:
        return []

    left_items: list[Any] = [Paragraph("Fuentes utilizadas", ParagraphStyle("src_head_l", parent=style_map["kicker"], textColor=INK_DARK))]
    for src in sources[:8]:
        left_items.append(Paragraph(f"• {src}", style_map["bullet"]))

    confidence_text, _ = _extract_confidence(evidence, analysis)
    municipal_text, _ = _extract_municipal_coverage(evidence)
    estimated_text, _ = _extract_estimated_coverage(evidence)
    quality_text = _extract_quality_label(evidence)

    methodology: list[Any] = [
        Paragraph("Lectura metodológica", ParagraphStyle("src_head_r", parent=style_map["kicker"], textColor=INK_DARK)),
        Paragraph(f"Confianza general: {confidence_text}", style_map["body_sm"]),
        Paragraph(f"Cobertura municipal: {municipal_text}", style_map["body_sm"]),
        Paragraph(f"Estimación regional: {estimated_text}", style_map["body_sm"]),
        Paragraph(f"Calidad: {quality_text}", style_map["body_sm"]),
    ]
    if evidence and evidence.methodology_disclaimer:
        methodology.append(Paragraph(_text(evidence.methodology_disclaimer), style_map["body_sm"]))

    left_table = _panel(left_items, UW * 0.43, PANEL_BG, PANEL_LINE, pad=10)
    right_table = _panel(methodology, UW * 0.43, GREEN_BG, GREEN_LINE, pad=10)

    wrapper = Table([[left_table, right_table]], colWidths=[UW * 0.47, UW * 0.47])
    wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [
        Paragraph("FUENTES Y METODOLOGÍA", style_map["section_title"]),
        rule(EMERALD, 1.5, 2, 8),
        wrapper,
    ]


def render_analysis_pdf(analysis: AnalysisRunDB, evidence: EvidenceRecordDB | None) -> bytes:
    municipality_name = (
        _text(getattr(evidence, "municipality_name", "")) or
        _text(getattr(analysis, "municipality_name", "")) or
        _text(getattr(analysis, "municipality_id", "Municipio"))
    )

    style_map = _style_map()
    buf = BytesIO()
    doc = make_doc(buf, f"Analisis territorial - {municipality_name}")
    elems: list[Any] = []

    elems.extend(
        [
            Paragraph("ANÁLISIS TERRITORIAL", style_map["tag"]),
            sp(4),
            Paragraph(municipality_name, style_map["h1"]),
            Paragraph("Estado de Tlaxcala, México · VoxPolítica 2.0", style_map["subtle"]),
            sp(12),
            rule(EMERALD, 2.0, 0, 10),
            _build_metric_cards(style_map, evidence, analysis),
            sp(10),
            _build_quality_band(style_map, evidence, analysis),
            sp(12),
        ]
    )

    if evidence and not evidence.can_cite_as_municipal and evidence.methodology_disclaimer:
        disclaimer = quality_disclaimer_block(style_map, evidence.methodology_disclaimer)
        if disclaimer:
            elems.extend([disclaimer, sp(10)])

    if analysis.executive_summary:
        elems.extend(
            [
                Paragraph("SÍNTESIS TERRITORIAL", style_map["section_title"]),
                rule(EMERALD, 1.5, 2, 8),
                _panel([Paragraph(_text(analysis.executive_summary), style_map["body"])], UW, GREEN_BG, GREEN_LINE, pad=12),
                sp(12),
            ]
        )

    elems.extend(_build_story_block(analysis, evidence, style_map))

    social_rows = _extract_social_profile_rows(evidence)
    if social_rows:
        elems.extend(
            [
                _build_bar_chart(
                    "Perfil de carencias sociales",
                    "% de población afectada — CONEVAL 2020",
                    social_rows,
                    UW,
                    RED,
                ),
                sp(14),
            ]
        )

    infra_rows = _extract_infra_rows(evidence)
    if infra_rows:
        elems.extend(
            [
                _build_bar_chart(
                    "Cobertura de infraestructura básica",
                    "% de cobertura en vivienda y servicios esenciales",
                    infra_rows,
                    UW,
                    EMERALD,
                ),
                sp(14),
            ]
        )

    elems.append(PageBreak())

    needs_section = _build_needs_cards(analysis, style_map)
    if needs_section:
        elems.extend(needs_section)
        elems.append(sp(10))

    economic_section = _build_economic_panel(evidence, style_map)
    if economic_section:
        elems.extend(economic_section)

    opportunities = [_text(x) for x in _as_list(analysis.opportunities) if _text(x)]
    if opportunities:
        elems.extend(
            [
                Paragraph("OPORTUNIDADES ESTRATÉGICAS", style_map["section_title"]),
                rule(EMERALD, 1.5, 2, 8),
            ]
        )
        for item in opportunities[:6]:
            elems.append(Paragraph(f"• {item}", style_map["bullet"]))
        elems.append(sp(12))

    kpi_elems, valid_kpis = _build_kpi_table(analysis, evidence, style_map)
    elems.extend(kpi_elems)

    if valid_kpis:
        elems.extend([_build_kpi_story_chart(valid_kpis, UW), sp(12)])

    elems.extend(_build_sources_panel(evidence, analysis, style_map))

    doc.build(elems, onFirstPage=page_footer, onLaterPages=page_footer)
    return buf.getvalue()