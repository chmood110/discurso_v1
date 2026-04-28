from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _speech_run_stub():
    class RunStub:
        id = "speech-run-export-1"
        municipality_id = "TLX-APZ"
        created_at = datetime.now(timezone.utc)
        title = "Discurso exportable"
        speech_type = "adaptation"
        target_duration_minutes = 10
        target_word_count = 1300
        actual_word_count = 1261
        retry_count = 2
        ai_generated = True
        latency_ms = 2100.0
        overall_confidence = 0.72
        validation_passed = True
        validation_score = 0.96
        validation_issues = []
        speech_data = {
            "title": "Discurso exportable",
            "speech_objective": "Fortalecer anclaje territorial",
            "target_audience": "Vecinas y vecinos",
            "opening": "Buenas tardes Apizaco.",
            "body_sections": [
                {
                    "title": "Diagnóstico",
                    "content": "Hay retos en agua, empleo y seguridad que deben atenderse con propuestas serias.",
                    "persuasion_technique": "validación",
                }
            ],
            "closing": "Juntos vamos a transformar el municipio.",
            "full_text": (
                "Buenas tardes Apizaco.\n\n"
                "Diagnóstico\n\n"
                "Hay retos en agua, empleo y seguridad que deben atenderse con propuestas serias.\n\n"
                "Juntos vamos a transformar el municipio."
            ),
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
            "source_processing": {
                "word_count": 1480,
                "paragraph_count": 18,
                "segments_count": 3,
                "estimated_minutes": 11.4,
                "alpha_ratio": 0.91,
                "prompt_ready_word_count": 1210,
                "segment_previews": [
                    "Queridas vecinas y vecinos de Apizaco...",
                    "No podemos seguir con servicios irregulares...",
                    "La salud y el empleo requieren una respuesta concreta...",
                ],
            },
            "adaptation_notes": [
                "Texto fuente limpiado y validado.",
                "Segmentación aplicada para preservar contexto.",
            ],
        }

    return RunStub()


def _evidence_stub():
    class EvidenceStub:
        can_cite_as_municipal = False
        methodology_disclaimer = (
            "NOTA METODOLÓGICA IMPORTANTE: Este análisis utiliza estimaciones calibradas."
        )
        quality_label = "Baja — estimaciones regionales calibradas"

    return EvidenceStub()


def test_export_speech_pdf_returns_pdf_response():
    run_stub = _speech_run_stub()
    evidence_stub = _evidence_stub()

    with patch(
        "app.api.v1.routes.exports.SpeechRepository.get_by_id",
        new=AsyncMock(return_value=run_stub),
    ), patch(
        "app.api.v1.routes.exports.EvidenceRepository.get_latest_by_municipality",
        new=AsyncMock(return_value=evidence_stub),
    ):
        response = client.get("/api/v1/exports/speech/speech-run-export-1.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
    assert len(response.content) > 2000