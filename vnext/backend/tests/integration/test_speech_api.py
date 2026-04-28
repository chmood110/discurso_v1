from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def _speech_payload():
    return {
        "municipality_id": "TLX-APZ",
        "speech_goal": "Movilizar apoyo en la zona textil",
        "audience": "Trabajadoras y trabajadores textiles",
        "tone": "moderado",
        "channel": "mitin",
        "duration_minutes": 10,
        "priority_topics": ["agua", "empleo", "seguridad"],
        "force_refresh": True,
    }


def _run_stub():
    class RunStub:
        id = "speech-run-1"
        municipality_id = "TLX-APZ"
        analysis_run_id = "analysis-run-1"
        created_at = datetime.now(timezone.utc)
        status = "completed"
        speech_type = "creation"
        target_duration_minutes = 10
        target_word_count = 1300
        actual_word_count = 1260
        retry_count = 1
        parameter_hash = "abc123def456"
        ai_generated = True
        latency_ms = 1450.0
        overall_confidence = 0.84
        validation_passed = True
        validation_score = 0.97
        validation_rule_version = "1.1.0"
        validation_issues = []
        speech_data = {
            "title": "Movilizar apoyo en la zona textil — Apizaco",
            "speech_objective": "Movilizar apoyo en la zona textil",
            "target_audience": "Trabajadoras y trabajadores textiles",
            "opening": "Ciudadanas y ciudadanos de Apizaco, hoy vengo a hablar de trabajo digno.",
            "body_sections": [
                {
                    "title": "Diagnóstico",
                    "content": "Muchas familias siguen enfrentando empleos sin seguridad social.",
                    "persuasion_technique": "validación",
                },
                {
                    "title": "Propuesta",
                    "content": "Vamos a impulsar empleo formal, alumbrado y seguridad en colonias prioritarias.",
                    "persuasion_technique": "propuesta concreta",
                },
            ],
            "closing": "Juntos vamos a transformar Apizaco. Adelante.",
            "full_text": (
                "Ciudadanas y ciudadanos de Apizaco, hoy vengo a hablar de trabajo digno.\n\n"
                "Diagnóstico\n\n"
                "Muchas familias siguen enfrentando empleos sin seguridad social.\n\n"
                "Propuesta\n\n"
                "Vamos a impulsar empleo formal, alumbrado y seguridad en colonias prioritarias.\n\n"
                "Juntos vamos a transformar Apizaco. Adelante."
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
                "actual_word_count": 1260,
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
            "adaptation_notes": ["Discurso generado desde contexto territorial y análisis."],
        }

    return RunStub()


client = TestClient(app)


def test_speech_run_endpoint_returns_duration_and_plan():
    run_stub = _run_stub()

    with patch("app.api.v1.routes.speech.speech_orchestrator.run", new=AsyncMock(return_value=run_stub)):
        response = client.post("/api/v1/speech/run", json=_speech_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["speech_data"]["duration_verification"]["within_tolerance"] is True
    assert body["data"]["speech_data"]["generation_plan"]["body_sections"] == 3
    assert body["data"]["actual_word_count"] == 1260


def test_speech_run_endpoint_returns_source_processing_on_improvement():
    run_stub = _run_stub()
    run_stub.speech_type = "adaptation"
    run_stub.speech_data["source_processing"] = {
        "word_count": 1480,
        "paragraph_count": 18,
        "segments_count": 3,
        "estimated_minutes": 11.4,
        "alpha_ratio": 0.91,
        "prompt_ready_word_count": 1210,
        "segment_previews": [
            "Queridas vecinas y vecinos de Apizaco, hoy quiero hablarles del agua...",
            "No podemos seguir con calles oscuras y servicios irregulares...",
            "La salud y el empleo requieren una respuesta coordinada...",
        ],
    }

    payload = _speech_payload()
    payload["source_text"] = (
        "Queridas vecinas y vecinos de Apizaco. "
        "Hoy estamos aquí para hablar del agua, el empleo y la seguridad de nuestras familias. "
        "Necesitamos calles dignas, más oportunidades para jóvenes y mejor atención de salud. "
    ) * 10

    with patch("app.api.v1.routes.speech.speech_orchestrator.run", new=AsyncMock(return_value=run_stub)):
        response = client.post("/api/v1/speech/run", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["speech_type"] == "adaptation"
    assert body["data"]["speech_data"]["source_processing"]["segments_count"] == 3
    assert len(body["data"]["speech_data"]["source_processing"]["segment_previews"]) == 3


def test_speech_latest_endpoint_maps_summary():
    run_stub = _run_stub()

    with patch("app.api.v1.routes.speech.speech_orchestrator.get_latest", new=AsyncMock(return_value=run_stub)):
        response = client.get("/api/v1/speech/latest/TLX-APZ")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["target_duration_minutes"] == 10
    assert body["data"]["target_word_count"] == 1300
    assert body["data"]["actual_word_count"] == 1260
    assert body["data"]["parameter_hash"] == "abc123def456"