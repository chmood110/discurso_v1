"""Speech PDF builder — reads from SpeechRunDB."""
from io import BytesIO

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

from app.models.db_models import EvidenceRecordDB, SpeechRunDB
from app.services.export.pdf_common import (
    AMBER_600,
    EMERALD,
    EMERALD_LT,
    SLATE_50,
    SLATE_200,
    SLATE_500,
    SLATE_700,
    SLATE_900,
    UW,
    highlight_box,
    make_doc,
    page_footer,
    quality_disclaimer_block,
    rule,
    sp,
    styles,
)


class SpeechPDFBuilder:
    def build(self, run: SpeechRunDB, evidence: EvidenceRecordDB | None) -> bytes:
        buf = BytesIO()
        d = run.speech_data or {}
        title = d.get("title", "Discurso Político")
        doc = make_doc(buf, title)
        s = styles()
        els = []

        cover = Table(
            [[
                [
                    Paragraph("DISCURSO POLÍTICO", s["tag"]),
                    sp(3),
                    Paragraph(title, s["h1"]),
                ],
                Paragraph("VoxPolítica Tlaxcala", s["caption"]),
            ]],
            colWidths=[UW * 0.78, UW * 0.22],
        )
        cover.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                    ("LINEABOVE", (0, 0), (-1, 0), 3, EMERALD),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        els.extend([cover, sp(10)])

        meta_items: list[tuple[str, str]] = []
        if run.municipality_id:
            meta_items.append(("Territorio", run.municipality_id))

        obj = str(d.get("speech_objective", "") or "")
        if obj:
            meta_items.append(("Objetivo", obj[:44] + ("…" if len(obj) > 44 else "")))

        aud = str(d.get("target_audience", "") or "")
        if aud:
            meta_items.append(("Audiencia", aud[:44] + ("…" if len(aud) > 44 else "")))

        duration_meta = d.get("duration_verification") or {}
        estimated_minutes = duration_meta.get("estimated_minutes") or d.get("estimated_duration_minutes") or run.target_duration_minutes
        actual_words = run.actual_word_count or d.get("estimated_word_count") or 0
        meta_items.append(("Duración", f"{estimated_minutes} min (~{int(actual_words):,} palabras)"))

        if meta_items:
            cw = UW / len(meta_items)
            cells = []
            for lbl, val in meta_items:
                cells.append(
                    [
                        Paragraph(
                            str(val),
                            ParagraphStyle(
                                "MV",
                                fontName="Helvetica-Bold",
                                fontSize=10,
                                textColor=SLATE_900,
                                alignment=1,
                                leading=14,
                            ),
                        ),
                        Paragraph(
                            lbl,
                            ParagraphStyle(
                                "ML",
                                fontName="Helvetica",
                                fontSize=8,
                                textColor=SLATE_500,
                                alignment=1,
                            ),
                        ),
                    ]
                )
            mt = Table([cells], colWidths=[cw] * len(cells))
            mt.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), EMERALD_LT),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            els.extend([mt, sp(16)])

        if evidence and not evidence.can_cite_as_municipal and evidence.methodology_disclaimer:
            disclaimer = quality_disclaimer_block(s, evidence.methodology_disclaimer)
            if disclaimer:
                els.extend([disclaimer, sp(10)])

        verification = d.get("duration_verification") or {}
        if verification:
            els.extend([Paragraph("VERIFICACIÓN DE DURACIÓN", s["speech_h"]), rule(EMERALD, 1.5, 2, 8)])
            vt = Table(
                [[
                    self._metric_cell("Objetivo", f"{verification.get('target_minutes', '—')} min"),
                    self._metric_cell("Estimado", f"{verification.get('estimated_minutes', '—')} min"),
                    self._metric_cell(
                        "Rango aceptable",
                        f"{verification.get('lower_bound_minutes', '—')} – {verification.get('upper_bound_minutes', '—')} min",
                    ),
                    self._metric_cell(
                        "Estado",
                        "Dentro de tolerancia" if verification.get("within_tolerance") else "Fuera de tolerancia",
                        color=EMERALD if verification.get("within_tolerance") else AMBER_600,
                    ),
                ]],
                colWidths=[UW / 4] * 4,
            )
            vt.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("BOX", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            els.extend([vt, sp(14)])

        source_processing = d.get("source_processing") or {}
        if source_processing:
            els.extend([Paragraph("PROCESAMIENTO DEL TEXTO FUENTE", s["speech_h"]), rule(EMERALD, 1.5, 2, 8)])
            st = Table(
                [[
                    self._metric_cell("Palabras", f"{int(source_processing.get('word_count', 0)):,}"),
                    self._metric_cell("Párrafos", str(source_processing.get("paragraph_count", "—"))),
                    self._metric_cell("Tramos", str(source_processing.get("segments_count", "—"))),
                    self._metric_cell("Tiempo base", f"{source_processing.get('estimated_minutes', '—')} min"),
                ]],
                colWidths=[UW / 4] * 4,
            )
            st.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("BOX", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            els.extend([st, sp(10)])

            previews = source_processing.get("segment_previews") or []
            if previews:
                els.append(Paragraph("Vista previa de tramos procesados", s["body_sm"]))
                for idx, preview in enumerate(previews[:6], start=1):
                    els.append(
                        highlight_box(
                            [
                                Paragraph(
                                    f"TRAMO {idx}",
                                    ParagraphStyle(
                                        "SegTag",
                                        fontName="Helvetica-Bold",
                                        fontSize=8,
                                        textColor=SLATE_500,
                                        tracking=40,
                                    ),
                                ),
                                sp(3),
                                Paragraph(str(preview), s["body"]),
                            ],
                            bg=SLATE_50,
                            border=SLATE_200,
                            pad=10,
                        )
                    )
                    els.append(sp(6))
                els.append(sp(4))

        generation_plan = d.get("generation_plan") or {}
        if generation_plan:
            els.extend([Paragraph("PLAN DE GENERACIÓN", s["speech_h"]), rule(EMERALD, 1.5, 2, 8)])
            gt = Table(
                [[
                    self._metric_cell("Objetivo", f"{int(generation_plan.get('target_words', 0)):,} palabras"),
                    self._metric_cell("Mínimo", f"{int(generation_plan.get('minimum_words', 0)):,} palabras"),
                    self._metric_cell("Secciones", str(generation_plan.get("body_sections", "—"))),
                    self._metric_cell("Palabras/Sección", f"{int(generation_plan.get('body_section_words', 0)):,}"),
                ]],
                colWidths=[UW / 4] * 4,
            )
            gt.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("BOX", (0, 0), (-1, -1), 0.3, SLATE_200),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            els.extend([gt, sp(10)])

            batches = generation_plan.get("batches") or []
            if batches:
                batch_text = " · ".join([f"Lote {idx + 1}: {', '.join(str(n) for n in batch)}" for idx, batch in enumerate(batches)])
                els.append(Paragraph(f"Lotes de segmentación: {batch_text}", s["caption"]))
                els.append(sp(8))

        opening = d.get("opening", "")
        if opening:
            els.append(Paragraph("APERTURA", s["speech_h"]))
            els.append(rule(EMERALD, 1.5, 2, 8))
            for para in [p.strip() for p in str(opening).split("\n\n") if p.strip()]:
                els.append(Paragraph(para, s["speech"]))
            els.append(sp(8))

        sections = d.get("body_sections", []) or []
        full_text = d.get("full_text", "") or ""

        if sections:
            els.append(Paragraph("DESARROLLO", s["speech_h"]))
            els.append(rule(EMERALD, 1.5, 2, 8))
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                sec_title = str(sec.get("title", "") or "")
                sec_content = str(sec.get("content", "") or "")
                technique = str(sec.get("persuasion_technique", "") or "")

                if sec_title:
                    els.append(
                        Paragraph(
                            sec_title,
                            ParagraphStyle(
                                "SecT",
                                fontName="Helvetica-Bold",
                                fontSize=10,
                                textColor=SLATE_500,
                                spaceBefore=10,
                                spaceAfter=4,
                            ),
                        )
                    )
                for para in [p.strip() for p in sec_content.split("\n\n") if p.strip()]:
                    els.append(Paragraph(para, s["speech"]))
                if technique:
                    els.append(
                        Paragraph(
                            f"Técnica de persuasión: {technique}",
                            ParagraphStyle(
                                "Tech",
                                fontName="Helvetica-Oblique",
                                fontSize=8,
                                textColor=SLATE_500,
                                spaceAfter=5,
                            ),
                        )
                    )
                els.append(sp(4))
        elif full_text and not opening:
            els.append(Paragraph("DISCURSO", s["speech_h"]))
            els.append(rule(EMERALD, 1.5, 2, 8))
            for para in [p.strip() for p in str(full_text).split("\n\n") if p.strip()]:
                els.append(Paragraph(para, s["speech"]))

        closing = d.get("closing", "")
        if closing:
            els.extend([sp(4), Paragraph("CIERRE", s["speech_h"]), rule(EMERALD, 1.5, 2, 8)])
            closing_parts = [Paragraph(p.strip(), s["speech"]) for p in str(closing).split("\n\n") if p.strip()]
            if closing_parts:
                els.append(highlight_box(closing_parts))
            els.append(sp(10))

        improvements = d.get("improvements_made") or []
        if improvements:
            els.extend([Paragraph("MEJORAS APLICADAS", s["speech_h"]), rule(EMERALD, 1.5, 2, 8)])
            for item in improvements[:8]:
                els.append(Paragraph(f"• {item}", s["bullet_green"]))
            els.append(sp(8))

        adaptation_notes = d.get("adaptation_notes") or []
        if adaptation_notes:
            els.extend([Paragraph("NOTAS DE ADAPTACIÓN", s["speech_h"]), rule(EMERALD, 1.5, 2, 8)])
            for item in adaptation_notes[:8]:
                els.append(Paragraph(f"• {item}", s["bullet"]))
            els.append(sp(8))

        local_refs = d.get("local_references", []) or []
        if local_refs:
            els.extend([rule(), Paragraph("Referencias locales: " + " · ".join([str(x) for x in local_refs[:8]]), s["caption"])])

        els.extend([sp(16), rule()])
        if evidence:
            els.append(Paragraph(f"Calidad de datos: {evidence.quality_label}", s["caption"]))

        doc.build(els, onFirstPage=page_footer, onLaterPages=page_footer)
        return buf.getvalue()

    def _metric_cell(self, label: str, value: str, color=SLATE_900):
        return [
            Paragraph(
                str(value),
                ParagraphStyle(
                    "CellValue",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=color,
                    alignment=1,
                    leading=14,
                ),
            ),
            Paragraph(
                label,
                ParagraphStyle(
                    "CellLabel",
                    fontName="Helvetica",
                    fontSize=8,
                    textColor=SLATE_500,
                    alignment=1,
                ),
            ),
        ]


speech_pdf_builder = SpeechPDFBuilder()