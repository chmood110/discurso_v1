"""PromptBuilder v2.0 — speech creator/improver + sectioned generation."""
from __future__ import annotations

from app.core.config import settings
from app.services.prompts.base import PromptContext, PromptTemplate
from app.services.prompts.templates import (
    SPEECH_CREATOR_SYSTEM,
    SPEECH_CREATOR_USER_TEMPLATE,
    SPEECH_IMPROVER_SYSTEM,
    SPEECH_IMPROVER_USER_TEMPLATE,
)
from app.services.territory.assembler import TerritoryContextAssembler

_WPM = settings.SPEECH_WORDS_PER_MINUTE
_MIN_FACTOR = settings.SPEECH_MIN_WORDS_FACTOR
_TOKENS_PER_WORD = 1.3
_JSON_OVERHEAD = 400
_MODEL_MAX = settings.SPEECH_MODEL_MAX_OUTPUT_TOKENS


def _compute_tokens(duration_minutes: int) -> int:
    words = duration_minutes * _WPM
    return min(int(words * _TOKENS_PER_WORD) + _JSON_OVERHEAD, _MODEL_MAX)


def _section_tokens(goal_words: int, json_output: bool = False) -> int:
    overhead = _JSON_OVERHEAD if json_output else 120
    return min(int(goal_words * _TOKENS_PER_WORD) + overhead, _MODEL_MAX)


def _structure_guide(duration_minutes: int) -> str:
    if duration_minutes <= 3:
        return (
            "ESTRUCTURA (breve):\n"
            "- Apertura impactante (1 párrafo)\n"
            "- Mensaje central con propuesta (1-2 párrafos)\n"
            "- Cierre con llamada a la acción (1 párrafo)"
        )
    if duration_minutes <= 8:
        return (
            "ESTRUCTURA (medio):\n"
            "- Apertura emocional territorial (2 párrafos)\n"
            "- Diagnóstico: dolores y causas (2-3 párrafos)\n"
            "- Propuestas concretas y verificables (2-3 párrafos)\n"
            "- Cierre movilizador (1-2 párrafos)"
        )
    if duration_minutes <= 20:
        return (
            "ESTRUCTURA (amplio — CADA SECCIÓN EXTENSA):\n"
            "- Apertura emocional con historia territorial (2-3 párrafos)\n"
            "- Reconocimiento del dolor y contexto actual (2-3 párrafos)\n"
            "- Desarrollo temático con propuestas concretas (3-5 párrafos)\n"
            "- Visión de futuro y cierre movilizador (2-3 párrafos)"
        )
    return (
        "ESTRUCTURA (extenso — MUY DESARROLLADO):\n"
        "- Apertura territorial potente (3-4 párrafos)\n"
        "- Contexto histórico y diagnóstico profundo (4-6 párrafos)\n"
        "- Desarrollo de múltiples temas con propuestas detalladas (8-12 párrafos)\n"
        "- Visión de largo plazo y llamado a la acción final (3-4 párrafos)"
    )


def _min_refs(duration_minutes: int) -> int:
    if duration_minutes <= 5:
        return 2
    if duration_minutes <= 15:
        return 4
    return 6


class PromptBuilder:
    def __init__(self):
        self.territory_assembler = TerritoryContextAssembler()

    def build_speech_creator_prompt(self, context: PromptContext) -> PromptTemplate:
        duration = context.duration_minutes or 10
        estimated = duration * _WPM
        min_words = int(estimated * _MIN_FACTOR)
        max_tokens = _compute_tokens(duration)

        user = SPEECH_CREATOR_USER_TEMPLATE.format(
            territory_context=context.territory_text or "Municipio de Tlaxcala",
            candidate_context=self._format_candidate(context),
            speech_goal=context.speech_goal or "Generar apoyo ciudadano",
            audience=context.audience or "Ciudadanía general",
            tone=context.tone or "moderado",
            channel=context.channel or "mitin",
            duration_minutes=duration,
            estimated_words=estimated,
            min_words=min_words,
            priority_topics=", ".join(context.priority_topics) or "No especificados",
            avoid_topics=", ".join(context.avoid_topics) or "Ninguno",
            electoral_moment=context.electoral_moment or "No especificado",
            structure_guide=_structure_guide(duration),
            min_local_refs=_min_refs(duration),
        )
        return PromptTemplate(
            system_prompt=SPEECH_CREATOR_SYSTEM,
            user_prompt=user,
            purpose="speech_creation",
            output_format="json",
            temperature=0.75,
            max_tokens=max_tokens,
        )

    def build_speech_improver_prompt(self, context: PromptContext) -> PromptTemplate:
        duration = context.duration_minutes or 10
        estimated = duration * _WPM
        min_words = int(estimated * _MIN_FACTOR)
        max_tokens = _compute_tokens(duration)

        source_section = (
            f"DISCURSO BASE LIMPIO / SEGMENTADO:\n---\n{context.source_text}\n---\n"
            if context.source_text
            else "INSTRUCCIÓN: No hay discurso base. Crea uno original con los parámetros dados.\n"
        )

        user = SPEECH_IMPROVER_USER_TEMPLATE.format(
            source_text_section=source_section,
            municipality_name=context.municipality_name or "Municipio",
            territory_context=context.territory_text or "Municipio de Tlaxcala",
            audience=context.audience or "Ciudadanía general",
            tone=context.tone or "moderado",
            channel=context.channel or "mitin",
            speech_goal=context.speech_goal or "Mejorar el discurso",
            duration_minutes=duration,
            estimated_words=estimated,
            min_words=min_words,
            priority_topics=", ".join(context.priority_topics) or "No especificados",
            avoid_topics=", ".join(context.avoid_topics) or "Ninguno",
        )
        return PromptTemplate(
            system_prompt=SPEECH_IMPROVER_SYSTEM,
            user_prompt=user,
            purpose="speech_improvement",
            output_format="json",
            temperature=0.70,
            max_tokens=max_tokens,
        )

    def build_speech_adapter_prompt(self, context: PromptContext) -> PromptTemplate:
        return self.build_speech_improver_prompt(context)

    def build_speech_outline_prompt(
        self,
        context: PromptContext,
        body_sections: int,
        opening_words: int,
        body_section_words: int,
        closing_words: int,
        speech_type: str,
    ) -> PromptTemplate:
        municipality = context.municipality_name or "Municipio"
        neighborhood = getattr(context, "neighborhood_name", "") or ""
        place = f"{municipality} — {neighborhood}" if neighborhood else municipality

        system = (
            "Eres un estratega de discurso político para Tlaxcala. "
            "Debes planear un discurso por secciones, NO redactarlo completo. "
            "Responde SOLO JSON válido."
        )

        user = f"""
CONTEXTO TERRITORIAL:
{context.territory_text or "Municipio de Tlaxcala"}

MUNICIPIO OBJETIVO: {place}
OBJETIVO: {context.speech_goal or "Generar apoyo ciudadano"}
AUDIENCIA: {context.audience or "Ciudadanía general"}
TONO: {context.tone or "moderado"}
CANAL: {context.channel or "mitin"}
TIPO: {speech_type}

DOLORES PRIORITARIOS:
{chr(10).join("- " + p for p in (context.pain_points or [])[:8]) or "- No especificados"}

OPORTUNIDADES:
{chr(10).join("- " + o for o in (context.opportunities or [])[:8]) or "- No especificadas"}

TEMAS PRIORITARIOS:
{chr(10).join("- " + t for t in (context.priority_topics or [])[:8]) or "- No especificados"}

Diseña un outline con:
- opening_focus
- sections (exactamente {body_sections})
- closing_focus

Cada section debe incluir:
- title
- focus
- goal_words (aprox {body_section_words})
- persuasion_technique

Longitudes objetivo:
- opening_words: {opening_words}
- body_section_words: {body_section_words}
- closing_words: {closing_words}

No repitas el mismo foco en distintas secciones.
Cada sección debe cubrir un ángulo distinto y complementario.

Responde EXACTAMENTE con este JSON:
{{
  "opening_focus": "string",
  "sections": [
    {{
      "title": "string",
      "focus": "string",
      "goal_words": {body_section_words},
      "persuasion_technique": "string"
    }}
  ],
  "closing_focus": "string"
}}
""".strip()

        return PromptTemplate(
            system_prompt=system,
            user_prompt=user,
            purpose="speech_outline",
            output_format="json",
            temperature=0.55,
            max_tokens=_section_tokens(body_section_words * body_sections + opening_words + closing_words, json_output=True),
        )

    def build_speech_opening_prompt(
        self,
        context: PromptContext,
        focus: str,
        goal_words: int,
    ) -> PromptTemplate:
        system = (
            "Redacta SOLO la APERTURA de un discurso político en español. "
            "No uses títulos, viñetas ni JSON. "
            "Debe sonar natural, persuasiva y territorial."
        )

        user = f"""
TERRITORIO:
{context.territory_text or "Municipio de Tlaxcala"}

MUNICIPIO: {context.municipality_name or "Municipio"}
AUDIENCIA: {context.audience or "Ciudadanía general"}
TONO: {context.tone or "moderado"}
CANAL: {context.channel or "mitin"}
OBJETIVO: {context.speech_goal or "Generar apoyo ciudadano"}

FOCO DE LA APERTURA:
{focus}

REQUISITOS:
- Escribe SOLO la apertura
- Longitud objetivo: {goal_words} palabras
- Debe conectar emocionalmente con el territorio
- Debe mencionar el municipio de forma natural
- No repitas listas de datos
- No cierres el discurso
- No uses frases genéricas de plantilla
""".strip()

        return PromptTemplate(
            system_prompt=system,
            user_prompt=user,
            purpose="speech_opening",
            output_format="text",
            temperature=0.75,
            max_tokens=_section_tokens(goal_words),
        )

    def build_speech_body_section_prompt(
        self,
        context: PromptContext,
        title: str,
        focus: str,
        goal_words: int,
    ) -> PromptTemplate:
        system = (
            "Redacta SOLO una sección de desarrollo de un discurso político en español. "
            "No uses títulos, viñetas ni JSON. "
            "Debe ser concreta, argumentativa y persuasiva."
        )

        user = f"""
TERRITORIO:
{context.territory_text or "Municipio de Tlaxcala"}

MUNICIPIO: {context.municipality_name or "Municipio"}
AUDIENCIA: {context.audience or "Ciudadanía general"}
TONO: {context.tone or "moderado"}
OBJETIVO: {context.speech_goal or "Generar apoyo ciudadano"}

TÍTULO DE LA SECCIÓN:
{title}

FOCO:
{focus}

TEMAS PRIORITARIOS:
{", ".join(context.priority_topics or []) or "No especificados"}

TEMAS A EVITAR:
{", ".join(context.avoid_topics or []) or "Ninguno"}

REQUISITOS:
- Escribe SOLO el contenido de esta sección
- Longitud objetivo: {goal_words} palabras
- Incluye propuestas o argumentos concretos
- Mantén anclaje territorial
- No abras ni cierres el discurso completo
- No repitas párrafos de otras secciones
- Desarrolla con densidad suficiente para discursos largos
""".strip()

        return PromptTemplate(
            system_prompt=system,
            user_prompt=user,
            purpose="speech_body_section",
            output_format="text",
            temperature=0.75,
            max_tokens=_section_tokens(goal_words),
        )

    def build_speech_closing_prompt(
        self,
        context: PromptContext,
        focus: str,
        goal_words: int,
    ) -> PromptTemplate:
        system = (
            "Redacta SOLO el CIERRE de un discurso político en español. "
            "No uses títulos, viñetas ni JSON. "
            "Debe ser movilizador, emotivo y con llamada a la acción."
        )

        user = f"""
TERRITORIO:
{context.territory_text or "Municipio de Tlaxcala"}

MUNICIPIO: {context.municipality_name or "Municipio"}
AUDIENCIA: {context.audience or "Ciudadanía general"}
TONO: {context.tone or "moderado"}
OBJETIVO: {context.speech_goal or "Generar apoyo ciudadano"}

FOCO DEL CIERRE:
{focus}

REQUISITOS:
- Escribe SOLO el cierre
- Longitud objetivo: {goal_words} palabras
- Debe cerrar con fuerza y llamado a la acción
- Debe sentirse específico al municipio
- No repitas literalmente la apertura
""".strip()

        return PromptTemplate(
            system_prompt=system,
            user_prompt=user,
            purpose="speech_closing",
            output_format="text",
            temperature=0.78,
            max_tokens=_section_tokens(goal_words),
        )

    def build_speech_expand_section_prompt(
        self,
        context: PromptContext,
        title: str,
        focus: str,
        current_text: str,
        goal_words: int,
        min_words: int,
    ) -> PromptTemplate:
        system = (
            "Expande una sección de discurso político en español. "
            "Debes conservar la idea base, pero volverla más desarrollada, específica y persuasiva. "
            "No uses viñetas ni JSON."
        )

        user = f"""
TERRITORIO:
{context.territory_text or "Municipio de Tlaxcala"}

MUNICIPIO: {context.municipality_name or "Municipio"}
TÍTULO: {title}
FOCO: {focus}

TEXTO ACTUAL:
---
{current_text}
---

INSTRUCCIÓN:
Reescribe y expande esta sección.

REQUISITOS:
- Longitud objetivo: {goal_words} palabras
- Longitud mínima aceptable: {min_words} palabras
- Debe quedar más específica y completa
- Debe mantener anclaje territorial
- Debe conservar la intención original
- No conviertas el texto en lista
- No cierres toda la pieza en esta sección
""".strip()

        return PromptTemplate(
            system_prompt=system,
            user_prompt=user,
            purpose="speech_expand_section",
            output_format="text",
            temperature=0.72,
            max_tokens=_section_tokens(goal_words),
        )

    def build_from_territory_context(self, territory_context: dict) -> PromptContext:
        territory_text = self.territory_assembler.to_prompt_context(territory_context)
        pain_points = self.territory_assembler.extract_pain_points(territory_context)
        opportunities = self.territory_assembler.extract_opportunities(territory_context)

        profile = territory_context.get("profile") or {}
        narrative = profile.get("narrative", {}) if isinstance(profile, dict) else {}
        political = profile.get("political", {}) if isinstance(profile, dict) else {}
        municipality = territory_context.get("municipality") or {}

        sensitive_topics = narrative.get("sensitive_topics", [])
        framing_suggestions = narrative.get("framing_suggestions", [])
        recommended_tone = narrative.get("recommended_tone", "moderado")

        evidence = territory_context.get("evidence_pack") or {}
        if evidence:
            ev_needs = (evidence.get("diagnosis") or {}).get("critical_needs") or []
            ev_opps = (evidence.get("diagnosis") or {}).get("opportunities") or []
            if ev_needs:
                evidence_pain = [
                    n.get("title", "") if isinstance(n, dict) else str(n)
                    for n in ev_needs if n
                ]
                if evidence_pain:
                    pain_points = evidence_pain
            if ev_opps:
                opportunities = ev_opps

            pov_dp = (evidence.get("social") or {}).get("poverty_rate_pct") or {}
            pov_val = pov_dp.get("value") if isinstance(pov_dp, dict) else None
            if pov_val:
                if pov_val >= 55:
                    recommended_tone = "urgente y solidario"
                elif pov_val >= 40:
                    recommended_tone = "combativo y propositivo"
                elif pov_val >= 28:
                    recommended_tone = "moderado y propositivo"
                else:
                    recommended_tone = "institucional y cercano"

        return PromptContext(
            territory_text=territory_text,
            municipality_name=municipality.get("name", ""),
            pain_points=pain_points,
            opportunities=opportunities,
            sensitive_topics=sensitive_topics,
            recommended_tone=recommended_tone,
            framing_suggestions=framing_suggestions,
            political_tendency=political.get("traditional_vote_tendency", ""),
        )

    def to_llm_request(self, template: PromptTemplate) -> "LLMRequest":
        from app.services.llm.models import LLMMessage, LLMRequest

        return LLMRequest(
            messages=[
                LLMMessage(role="system", content=template.system_prompt),
                LLMMessage(role="user", content=template.user_prompt),
            ],
            temperature=template.temperature,
            max_tokens=template.max_tokens,
            purpose=template.purpose,
            json_mode=(template.output_format == "json"),
        )

    @staticmethod
    def _format_candidate(context: PromptContext) -> str:
        if not any(
            [
                context.candidate_name,
                context.candidate_party,
                context.candidate_position,
                context.candidate_style,
                context.candidate_values,
            ]
        ):
            return "No se proporcionó información del candidato. Genera el discurso de forma neutra."

        parts: list[str] = []
        if context.candidate_name:
            parts.append(f"Nombre: {context.candidate_name}")
        if context.candidate_party:
            parts.append(f"Partido: {context.candidate_party}")
        if context.candidate_position:
            parts.append(f"Cargo: {context.candidate_position}")
        if context.candidate_style:
            parts.append(f"Estilo: {context.candidate_style}")
        if context.candidate_values:
            parts.append(f"Valores: {', '.join(context.candidate_values)}")
        return "\n".join(parts)