from app.core.exceptions import SourceTextValidationError
from app.services.speech.text_processing import text_processing_service


RAW_TEXT = """
DISCURSO 2026
Página 1 de 3

Queridas vecinas y vecinos de Apizaco:
Este texto fue extraído desde PDF y tiene saltos de lí-
nea que deben limpiarse.

En esta ciudad necesitamos empleo digno, seguridad y agua.

DISCURSO 2026
Página 2 de 3

Nuestra propuesta es invertir en alumbrado, calles y apoyo a comerciantes.
También vamos a fortalecer salud y oportunidades para jóvenes.

DISCURSO 2026
Página 3 de 3

Juntas y juntos vamos a recuperar la confianza.
"""

LONG_TEXT = "\n\n".join(
    [
        (
            f"Párrafo {i}. En Huamantla necesitamos fortalecer el empleo local, "
            f"mejorar el acceso al agua, ampliar la atención en salud, "
            f"y garantizar oportunidades reales para jóvenes y comerciantes. "
            f"Cada acción debe ser concreta, medible y cercana a la vida diaria."
        )
        for i in range(1, 25)
    ]
)


def test_prepare_source_text_cleans_noise_and_segments():
    prepared = text_processing_service.prepare_source_text(RAW_TEXT, channel="mitin")

    assert "Página" not in prepared.cleaned_text
    assert "línea" in prepared.cleaned_text
    assert prepared.word_count > 30
    assert prepared.paragraph_count >= 3
    assert prepared.estimated_minutes > 0
    assert prepared.prompt_ready_text
    assert len(prepared.segments) >= 1


def test_prepare_source_text_rejects_empty_text():
    try:
        text_processing_service.prepare_source_text("   ", channel="mitin")
        assert False, "Debe lanzar SourceTextValidationError"
    except SourceTextValidationError as exc:
        assert "vacío" in exc.message.lower()


def test_prepare_source_text_rejects_too_short_text():
    try:
        text_processing_service.prepare_source_text("Hola vecinas y vecinos.", channel="mitin")
        assert False, "Debe lanzar SourceTextValidationError"
    except SourceTextValidationError as exc:
        assert "demasiado corto" in exc.message.lower()


def test_segment_text_splits_large_input():
    prepared = text_processing_service.prepare_source_text(LONG_TEXT, channel="mitin")

    assert prepared.word_count > 200
    assert len(prepared.segments) >= 2
    assert all(seg.word_count > 0 for seg in prepared.segments)
    assert prepared.metadata["segments_count"] == len(prepared.segments)


def test_build_generation_plan_supports_long_form():
    plan = text_processing_service.build_generation_plan(60)

    assert plan.target_words >= 7800
    assert plan.body_sections >= 10
    assert len(plan.batches) >= 3
    assert plan.minimum_words < plan.target_words


def test_verify_duration_returns_bounds():
    text = "palabra " * 1300
    verification = text_processing_service.verify_duration(text, target_minutes=10, channel="mitin")

    assert verification.estimated_minutes > 0
    assert verification.lower_bound_minutes < verification.upper_bound_minutes
    assert verification.within_tolerance is True
    assert verification.actual_word_count == 1300


def test_verify_duration_flags_mismatch_for_short_text():
    text = "palabra " * 200
    verification = text_processing_service.verify_duration(text, target_minutes=10, channel="mitin")

    assert verification.within_tolerance is False
    assert verification.estimated_minutes < verification.lower_bound_minutes


def test_prompt_ready_text_respects_budget():
    prepared = text_processing_service.prepare_source_text(LONG_TEXT * 4, channel="mitin")

    assert prepared.metadata["prompt_ready_word_count"] <= 2600
    assert "[TRAMO" in prepared.prompt_ready_text