"""
PDF export tests — structural validation for analysis and speech PDFs.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.models.db_models import AnalysisRunDB, EvidenceRecordDB, SpeechRunDB
from app.services.export._analysis_renderer import render_analysis_pdf
from app.services.export.pdf_speech import speech_pdf_builder


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


@pytest.fixture
def evidence_rec():
    return EvidenceRecordDB(
        id=_uuid(),
        municipality_id="TLX-APZ",
        municipality_name="Apizaco",
        snapshot_version="test_snap_1234abcd",
        created_at=_now(),
        collection_method="reference",
        overall_confidence=0.95,
        municipal_coverage_pct=80.0,
        state_coverage_pct=10.0,
        estimated_coverage_pct=10.0,
        can_cite_as_municipal=True,
        quality_label="Alta — datos oficiales municipales",
        methodology_disclaimer="",
        social_data={
            "poverty_rate_pct": {
                "value": 28.6,
                "available": True,
                "geographic_level": "municipal",
                "unit": "%",
                "source": "CONEVAL",
                "period": "2020",
            }
        },
        economic_data={},
        infrastructure_data={},
        sources_used=["INEGI Censo 2020", "CONEVAL 2020"],
        sources_failed=[],
        geographic_fallbacks=[],
    )


@pytest.fixture
def estimated_evidence_rec():
    return EvidenceRecordDB(
        id=_uuid(),
        municipality_id="TLX-AMA",
        municipality_name="Amaxac de Guerrero",
        snapshot_version="test_snap_5678efgh",
        created_at=_now(),
        collection_method="calibrated_estimate",
        overall_confidence=0.4,
        municipal_coverage_pct=0.0,
        state_coverage_pct=30.0,
        estimated_coverage_pct=70.0,
        can_cite_as_municipal=False,
        quality_label="Baja — estimaciones regionales calibradas",
        methodology_disclaimer=(
            "NOTA METODOLÓGICA IMPORTANTE: Este análisis utiliza estimaciones calibradas "
            "por región y categoría de municipio."
        ),
        social_data={},
        economic_data={},
        infrastructure_data={},
        sources_used=["Estimación regional"],
        sources_failed=[],
        geographic_fallbacks=[],
    )


@pytest.fixture
def analysis_run(evidence_rec):
    return AnalysisRunDB(
        id=_uuid(),
        municipality_id="TLX-APZ",
        evidence_record_id=evidence_rec.id,
        created_at=_now(),
        status="completed",
        executive_summary="Apizaco presenta alta informalidad laboral y oportunidades en manufactura textil.",
        demographic_profile={"population": {"value": 79196}},
        economic_engine={"employment": {"informal_employment_pct": {"value": 42.0, "available": True}}},
        infrastructure_gaps={"water": {"value": 91.0}},
        critical_needs=[
            {
                "title": "Seguridad social para trabajadores textiles",
                "severity": "alta",
                "description": "42% sin prestaciones",
            }
        ],
        opportunities=["Clúster textil certificable"],
        kpi_board={
            "kpis": [
                {
                    "name": "Pobreza multidimensional",
                    "baseline_value": 28.6,
                    "target_value": 22.0,
                    "baseline_unit": "%",
                }
            ]
        },
        speeches={},
        strategy_section={},
        overall_confidence=0.95,
        can_cite_as_municipal=True,
        validation_passed=True,
        validation_score=1.0,
        validation_issues=[],
    )


class TestAnalysisPDF:
    def test_pdf_generates_non_empty(self, analysis_run, evidence_rec):
        pdf = render_analysis_pdf(analysis_run, evidence_rec)
        assert len(pdf) > 1800
        assert pdf[:4] == b"%PDF"

    def test_analysis_pdf_with_disclaimer_generates(self, analysis_run, estimated_evidence_rec):
        pdf = render_analysis_pdf(analysis_run, estimated_evidence_rec)
        assert len(pdf) > 1800
        assert pdf[:4] == b"%PDF"


class TestSpeechPDF:
    def test_speech_pdf_generates(self, evidence_rec):
        run = SpeechRunDB(
            id=_uuid(),
            municipality_id="TLX-APZ",
            created_at=_now(),
            status="completed",
            speech_type="creation",
            parameters={"duration_minutes": 5},
            speech_data={
                "title": "Arranque de campaña Apizaco",
                "speech_objective": "Movilizar apoyo en la zona textil",
                "target_audience": "Trabajadoras y trabajadores textiles",
                "opening": (
                    "Ciudadanas y ciudadanos de Apizaco, hoy vengo a hablar de trabajo digno "
                    "y justicia social para quienes sostienen esta ciudad con su esfuerzo diario."
                ),
                "body_sections": [
                    {
                        "title": "Diagnóstico",
                        "content": (
                            "Muchas familias siguen enfrentando empleos sin seguridad social, "
                            "salarios inestables y servicios públicos insuficientes. "
                            "Esta realidad exige propuestas concretas y seguimiento real."
                        ),
                        "persuasion_technique": "validación",
                    },
                    {
                        "title": "Propuesta",
                        "content": (
                            "Vamos a impulsar empleo formal, mejor alumbrado, calles seguras "
                            "y atención más cercana en salud para las colonias con mayor rezago."
                        ),
                        "persuasion_technique": "propuesta concreta",
                    },
                ],
                "closing": "Juntos vamos a transformar Apizaco. ¡Adelante!",
                "full_text": (
                    "Ciudadanas y ciudadanos de Apizaco, hoy vengo a hablar de trabajo digno y justicia social "
                    "para quienes sostienen esta ciudad con su esfuerzo diario.\n\n"
                    "Diagnóstico\n\n"
                    "Muchas familias siguen enfrentando empleos sin seguridad social, salarios inestables "
                    "y servicios públicos insuficientes. Esta realidad exige propuestas concretas y seguimiento real.\n\n"
                    "Propuesta\n\n"
                    "Vamos a impulsar empleo formal, mejor alumbrado, calles seguras y atención más cercana "
                    "en salud para las colonias con mayor rezago.\n\n"
                    "Juntos vamos a transformar Apizaco. ¡Adelante!"
                ),
                "local_references": ["Municipio: Apizaco", "Zona textil", "Agua y empleo"],
                "adaptation_notes": ["Discurso generado desde contexto territorial y análisis."],
                "duration_verification": {
                    "target_minutes": 5,
                    "estimated_minutes": 4.8,
                    "lower_bound_minutes": 4.0,
                    "upper_bound_minutes": 6.0,
                    "within_tolerance": True,
                    "delta_minutes": -0.2,
                    "delta_pct": -0.04,
                    "words_per_minute": 130,
                    "actual_word_count": 624,
                },
                "generation_plan": {
                    "target_words": 650,
                    "minimum_words": 487,
                    "opening_words": 180,
                    "closing_words": 160,
                    "body_sections": 2,
                    "body_section_words": 155,
                    "batches": [[1, 2]],
                },
            },
            target_duration_minutes=5,
            target_word_count=650,
            actual_word_count=624,
            retry_count=1,
            ai_generated=True,
            latency_ms=1500.0,
            overall_confidence=0.95,
            validation_passed=True,
            validation_score=1.0,
            validation_issues=[],
        )
        pdf = speech_pdf_builder.build(run, evidence_rec)
        assert len(pdf) > 2200
        assert pdf[:4] == b"%PDF"

    def test_speech_pdf_with_source_processing_generates(self, estimated_evidence_rec):
        run = SpeechRunDB(
            id=_uuid(),
            municipality_id="TLX-AMA",
            created_at=_now(),
            status="completed",
            speech_type="adaptation",
            parameters={"duration_minutes": 10},
            speech_data={
                "title": "Mejora de discurso territorial",
                "speech_objective": "Fortalecer anclaje territorial",
                "target_audience": "Vecinas y vecinos",
                "opening": "Buenas tardes, Amaxac necesita una voz clara y una agenda concreta.",
                "body_sections": [
                    {
                        "title": "Territorio",
                        "content": "El texto base fue limpiado y reorganizado para evitar ruido, repeticiones y pérdida de contexto.",
                        "persuasion_technique": "clarificación",
                    }
                ],
                "closing": "Con organización y compromiso vamos a recuperar la confianza.",
                "full_text": (
                    "Buenas tardes, Amaxac necesita una voz clara y una agenda concreta.\n\n"
                    "Territorio\n\n"
                    "El texto base fue limpiado y reorganizado para evitar ruido, repeticiones y pérdida de contexto.\n\n"
                    "Con organización y compromiso vamos a recuperar la confianza."
                ),
                "source_processing": {
                    "word_count": 1480,
                    "paragraph_count": 18,
                    "segments_count": 3,
                    "estimated_minutes": 11.4,
                    "alpha_ratio": 0.91,
                    "prompt_ready_word_count": 1210,
                    "segment_previews": [
                        "Queridas vecinas y vecinos de Amaxac, hoy quiero hablarles del agua...",
                        "No podemos seguir con calles oscuras y servicios irregulares...",
                        "La salud y el empleo también requieren una respuesta coordinada...",
                    ],
                },
                "duration_verification": {
                    "target_minutes": 10,
                    "estimated_minutes": 9.7,
                    "lower_bound_minutes": 8.2,
                    "upper_bound_minutes": 11.8,
                    "within_tolerance": True,
                    "delta_minutes": -0.3,
                    "delta_pct": -0.03,
                    "words_per_minute": 130,
                    "actual_word_count": 1261,
                },
                "generation_plan": {
                    "target_words": 1300,
                    "minimum_words": 975,
                    "opening_words": 180,
                    "closing_words": 160,
                    "body_sections": 3,
                    "body_section_words": 320,
                    "batches": [[1, 2], [3]],
                },
                "adaptation_notes": [
                    "Texto fuente limpiado y validado.",
                    "Segmentación aplicada para preservar contexto.",
                ],
                "improvements_made": [
                    "Se eliminaron repeticiones innecesarias.",
                    "Se ajustó la longitud al tiempo solicitado.",
                ],
            },
            target_duration_minutes=10,
            target_word_count=1300,
            actual_word_count=1261,
            retry_count=2,
            ai_generated=True,
            latency_ms=2300.0,
            overall_confidence=0.4,
            validation_passed=True,
            validation_score=0.95,
            validation_issues=[],
        )
        pdf = speech_pdf_builder.build(run, estimated_evidence_rec)
        assert len(pdf) > 2500
        assert pdf[:4] == b"%PDF"

    def test_speech_pdf_no_placeholder_content(self, evidence_rec):
        run = SpeechRunDB(
            id=_uuid(),
            municipality_id="TLX-APZ",
            created_at=_now(),
            status="completed",
            speech_type="creation",
            parameters={},
            speech_data={
                "title": "Discurso válido",
                "opening": "Buenos días Apizaco, hoy estamos aquí para hablar con claridad y compromiso.",
                "body_sections": [],
                "closing": "Gracias por caminar juntos hacia un mejor municipio.",
            },
            target_duration_minutes=3,
            target_word_count=390,
            actual_word_count=24,
            retry_count=0,
            ai_generated=True,
            latency_ms=500.0,
            overall_confidence=0.9,
            validation_passed=True,
            validation_score=1.0,
            validation_issues=[],
        )
        pdf = speech_pdf_builder.build(run, evidence_rec)
        assert pdf[:4] == b"%PDF"
        for placeholder in [b"hallazgo 1 accionable", b"[INSERT", b"[Expansi"]:
            assert placeholder not in pdf