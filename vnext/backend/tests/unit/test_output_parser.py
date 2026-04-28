from app.services.llm.output_parser import output_parser


def test_parse_json_from_plain_object():
    raw = '{"title":"Discurso","opening":"Hola Apizaco","body_sections":[],"closing":"Gracias","full_text":"Hola Apizaco Gracias"}'
    data, ok = output_parser.parse_json(raw)

    assert ok is True
    assert data["title"] == "Discurso"


def test_parse_json_from_fenced_block():
    raw = """```json
{
  "title": "Discurso",
  "opening": "Hola Apizaco",
  "body_sections": [],
  "closing": "Gracias",
  "full_text": "Hola Apizaco Gracias"
}
```"""
    data, ok = output_parser.parse_json(raw)

    assert ok is True
    assert data["closing"] == "Gracias"


def test_validate_and_normalize_speech_builds_full_text_when_missing():
    normalized = output_parser.validate_and_normalize_speech(
        {
            "title": "Discurso territorial",
            "opening": "Buenas tardes Apizaco.",
            "body_sections": [
                {"title": "Diagnóstico", "content": "Hay retos en agua y empleo."},
                {"title": "Propuesta", "content": "Vamos a impulsar inversión y servicios."},
            ],
            "closing": "Juntos vamos a cambiar el municipio.",
        },
        channel="mitin",
    )

    assert normalized["full_text"]
    assert "Diagnóstico" in normalized["full_text"]
    assert normalized["estimated_word_count"] > 0
    assert normalized["estimated_duration_minutes"] > 0


def test_validate_and_normalize_speech_normalizes_string_sections():
    normalized = output_parser.validate_and_normalize_speech(
        {
            "opening": "Inicio",
            "body_sections": ["Primer bloque", "Segundo bloque"],
            "closing": "Final",
            "full_text": "",
        },
        channel="mitin",
    )

    assert len(normalized["body_sections"]) == 2
    assert normalized["body_sections"][0]["title"] == "Sección 1"
    assert normalized["body_sections"][1]["content"] == "Segundo bloque"


def test_validate_and_normalize_speech_preserves_duration_and_source_processing_dicts():
    normalized = output_parser.validate_and_normalize_speech(
        {
            "opening": "Inicio",
            "body_sections": [],
            "closing": "Final",
            "full_text": "Inicio Final",
            "duration_verification": {"target_minutes": 5, "within_tolerance": True},
            "generation_plan": {"target_words": 650},
            "source_processing": {"segments_count": 3},
        },
        channel="mitin",
    )

    assert normalized["duration_verification"]["target_minutes"] == 5
    assert normalized["generation_plan"]["target_words"] == 650
    assert normalized["source_processing"]["segments_count"] == 3