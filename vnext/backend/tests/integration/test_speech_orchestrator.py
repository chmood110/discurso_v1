from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import SpeechRunRequest
from app.services.speech.speech_orchestrator import SpeechOrchestrator


@pytest.mark.asyncio
async def test_prepare_request_cleans_source_text():
    orchestrator = SpeechOrchestrator()
    request = SpeechRunRequest(
        municipality_id="TLX-APZ",
        speech_goal="Mejorar discurso",
        audience="Ciudadanía general",
        tone="moderado",
        channel="mitin",
        duration_minutes=10,
        source_text=(
            "Página 1 de 2\n\n"
            "Queridas vecinas y vecinos de Apizaco:\n"
            "Este texto tiene saltos de lí-\n"
            "nea que deben limpiarse.\n\n"
            "Página 2 de 2\n\n"
            "Necesitamos agua, empleo y seguridad.\n"
        ),
    )

    normalized, source_processing = orchestrator._prepare_request(request)

    assert source_processing is not None
    assert "Página" not in normalized.source_text
    assert "línea" in normalized.source_text
    assert source_processing.word_count >= 10


@pytest.mark.asyncio
async def test_build_prompt_context_uses_prompt_ready_text():
    orchestrator = SpeechOrchestrator()
    analysis = SimpleNamespace(
        critical_needs=[{"title": "Agua"}],
        opportunities=["Empleo"],
    )
    source_processing = SimpleNamespace(
        prompt_ready_text="[TRAMO 1 | 120 palabras]\nTexto limpio y segmentado",
    )
    request = SpeechRunRequest(
        municipality_id="TLX-APZ",
        speech_goal="Mejorar discurso",
        audience="Ciudadanía general",
        tone="moderado",
        channel="mitin",
        duration_minutes=10,
        source_text="Texto original",
    )

    context = orchestrator._build_prompt_context(
        request=request,
        analysis=analysis,
        territory_text="Municipio: Apizaco",
        municipality_name="Apizaco",
        neighborhood_name="Centro",
        source_processing=source_processing,
    )

    assert context.source_text == source_processing.prompt_ready_text
    assert context.neighborhood_name == "Centro"
    assert context.pain_points == ["Agua"]
    assert context.opportunities == ["Empleo"]


@pytest.mark.asyncio
async def test_should_use_sectioned_generation_for_long_speech():
    orchestrator = SpeechOrchestrator()
    request = SpeechRunRequest(
        municipality_id="TLX-APZ",
        speech_goal="Crear discurso largo",
        audience="Ciudadanía general",
        tone="moderado",
        channel="mitin",
        duration_minutes=20,
    )

    assert orchestrator._should_use_sectioned_generation(request, None) is True


@pytest.mark.asyncio
async def test_should_use_sectioned_generation_for_large_source_text():
    orchestrator = SpeechOrchestrator()
    request = SpeechRunRequest(
        municipality_id="TLX-APZ",
        speech_goal="Mejorar discurso",
        audience="Ciudadanía general",
        tone="moderado",
        channel="mitin",
        duration_minutes=4,
        source_text="Texto base",
    )
    source_processing = SimpleNamespace(word_count=1200)

    assert orchestrator._should_use_sectioned_generation(request, source_processing) is True


@pytest.mark.asyncio
async def test_enrich_speech_data_adds_duration_and_source_processing():
    orchestrator = SpeechOrchestrator()
    request = SpeechRunRequest(
        municipality_id="TLX-APZ",
        speech_goal="Mejorar discurso",
        audience="Ciudadanía general",
        tone="moderado",
        channel="mitin",
        duration_minutes=10,
    )
    context = SimpleNamespace(
        speech_goal="Mejorar discurso",
        audience="Ciudadanía general",
        territory_text="Municipio: Apizaco\nZona: Centro\nAgua\nEmpleo",
        pain_points=["Agua", "Seguridad"],
        opportunities=["Empleo", "Salud"],
        municipality_name="Apizaco",
        neighborhood_name="Centro",
    )
    plan = SimpleNamespace(
        to_dict=lambda: {
            "target_words": 1300,
            "minimum_words": 975,
            "opening_words": 180,
            "closing_words": 160,
            "body_sections": 3,
            "body_section_words": 320,
            "batches": [[1, 2], [3]],
        }
    )
    source_processing = SimpleNamespace(
        word_count=1480,
        paragraph_count=18,
        segments=[SimpleNamespace(preview="Tramo 1"), SimpleNamespace(preview="Tramo 2")],
        estimated_minutes=11.4,
        alpha_ratio=0.91,
        metadata={"prompt_ready_word_count": 1210},
    )
    speech_data = {
        "opening": "Buenas tardes Apizaco, hoy venimos a hablar del agua y del empleo.",
        "body_sections": [
            {
                "title": "Diagnóstico",
                "content": "Muchas familias enfrentan servicios inestables y empleos precarios.",
                "persuasion_technique": "validación",
            },
            {
                "title": "Propuesta",
                "content": "Impulsaremos inversión, alumbrado, salud y una agenda concreta para colonias prioritarias.",
                "persuasion_technique": "propuesta concreta",
            },
        ],
        "closing": "Juntos vamos a recuperar la confianza y a transformar el municipio.",
    }

    enriched = orchestrator._enrich_speech_data(
        speech_data=speech_data,
        context=context,
        request=request,
        plan=plan,
        source_processing=source_processing,
    )

    assert enriched["duration_verification"]["target_minutes"] == 10
    assert enriched["generation_plan"]["target_words"] == 1300
    assert enriched["source_processing"]["segments_count"] == 2
    assert enriched["source_processing"]["prompt_ready_word_count"] == 1210
    assert len(enriched["local_references"]) >= 1


@pytest.mark.asyncio
async def test_enforce_duration_target_expands_short_speech():
    orchestrator = SpeechOrchestrator()
    request = SpeechRunRequest(
        municipality_id="TLX-APZ",
        speech_goal="Crear discurso",
        audience="Ciudadanía general",
        tone="moderado",
        channel="mitin",
        duration_minutes=10,
    )
    context = SimpleNamespace()
    plan = SimpleNamespace(minimum_words=975)

    short_speech = {
        "opening": "Apizaco merece un mejor futuro.",
        "body_sections": [
            {"title": "Diagnóstico", "content": "Hay rezagos importantes.", "persuasion_technique": "validación"}
        ],
        "closing": "Vamos a cambiar juntos.",
        "full_text": "Apizaco merece un mejor futuro.\n\nHay rezagos importantes.\n\nVamos a cambiar juntos.",
    }

    expanded = dict(short_speech)
    expanded["body_sections"] = [
        {
            "title": "Diagnóstico",
            "content": ("Hay rezagos importantes en agua, empleo, seguridad y salud. " * 80).strip(),
            "persuasion_technique": "validación",
        }
    ]
    expanded["full_text"] = (
        expanded["opening"]
        + "\n\n"
        + expanded["body_sections"][0]["content"]
        + "\n\n"
        + expanded["closing"]
    )

    with patch.object(orchestrator, "_expand_short_sections", new=AsyncMock(return_value=(expanded, 120.0, 1))):
        result, latency_ms, retries = await orchestrator._enforce_duration_target(
            request=request,
            context=context,
            speech_type="creation",
            plan=plan,
            speech_data=short_speech,
        )

    assert result["duration_verification"]["estimated_minutes"] > 0
    assert latency_ms == 120.0
    assert retries == 1