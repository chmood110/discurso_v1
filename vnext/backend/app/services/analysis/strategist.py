"""
AnalysisStrategist — genera la sección estratégica integrada al análisis territorial.

El DiagnosisGenerator produce datos estructurados (sin LLM).
El AnalysisStrategist convierte esos datos en estrategia política (con LLM, 1 llamada).

La capa LLM NO describe datos — los prioriza, encuadra y convierte en mensajes.
"""
from __future__ import annotations
import logging
import time
from typing import Optional

from app.services.llm.groq_client import GroqClient
from app.services.llm.models import LLMMessage, LLMRequest
from app.services.llm.output_parser import output_parser

logger = logging.getLogger(__name__)
_groq = GroqClient()

_SYSTEM = """\
Eres un estratega político senior especialista en comunicación para municipios de Tlaxcala, México.

Recibes un diagnóstico territorial COMPLETO ya elaborado con datos reales de INEGI y CONEVAL.
Tu tarea NO es describir ni repetir los datos. Ya están ahí.

Tu tarea ES:
1. Seleccionar los 2-3 hallazgos más movilizadores políticamente (no los más graves, los más movibles)
2. Construir ejes de mensaje que conecten datos con emociones del electorado
3. Proponer un posicionamiento estratégico único para ESTE municipio — no para cualquier candidato
4. Identificar riesgos comunicacionales concretos y cómo mitigarlos
5. Recomendar tono y canales exactos para este perfil territorial

REGLAS ANTI-REDUNDANCIA:
- Cada eje de mensaje debe ser distinto a los demás
- El posicionamiento no puede ser genérico ("candidato que escucha")
- Los framings deben tener frases literales entre comillas, no descripciones
- No repitas palabras del diagnóstico literal — reformula con perspectiva estratégica

Responde ÚNICAMENTE con JSON válido. Sin texto antes ni después.

{
  "executive_strategic": "2-3 líneas de síntesis estratégica: qué está en juego y qué diferencia puede hacer el candidato",
  "messaging_axes": [
    {
      "axis": "nombre corto del eje",
      "message": "mensaje que cabe en un titular de periódico",
      "rationale": "por qué funciona en este municipio específico",
      "emotional_hook": "emoción que activa en el elector",
      "data_anchor": "1 cifra del diagnóstico que lo sustenta"
    }
  ],
  "pain_points_ranked": ["dolor más movilizador políticamente", "segundo", "tercero"],
  "opportunities_ranked": ["oportunidad con mayor potencial electoral", "segunda", "tercera"],
  "candidate_positioning": "3-4 líneas de posicionamiento único para este municipio",
  "recommended_tone": "tono específico y por qué funciona aquí",
  "risk_flags": ["riesgo comunicacional concreto — cómo evitarlo"],
  "framing_suggestions": ["'frase literal de framing entre comillas'"],
  "communication_channels_priority": ["canal 1", "canal 2", "canal 3"]
}
"""

_USER_TEMPLATE = """\
MUNICIPIO: {name} — {region}, Tlaxcala
CATEGORÍA: {category}

DIAGNÓSTICO COMPUTADO (no repetir — usar como insumo):
{diagnosis_summary}

NECESIDADES CRÍTICAS (severidad y título):
{needs_text}

OPORTUNIDADES IDENTIFICADAS:
{opps_text}

PERFIL POLÍTICO TERRITORIAL:
{political_text}

KPIS PROPUESTOS (líneas base reales):
{kpi_text}

Genera la sección estratégica. Cada campo debe ser específico a este municipio.
"""


async def generate_strategy(
    municipality_name: str,
    region: str,
    category: str,
    diagnosis_summary: str,
    critical_needs: list[dict],
    opportunities: list[str],
    kpi_board: dict,
    territorial_profile: Optional[dict] = None,
) -> dict:
    needs_text = "\n".join(
        f"  [{n.get('severity','').upper()}] {n.get('title','')}"
        for n in critical_needs[:5]
    ) or "  Sin datos de necesidades"

    opps_text = "\n".join(f"  • {o[:120]}" for o in opportunities[:4]) or "  Sin oportunidades"

    kpis = kpi_board.get("kpis", []) if isinstance(kpi_board, dict) else []
    kpi_text = "\n".join(
        f"  {k.get('name','')}: {k.get('baseline_value','?')} {k.get('baseline_unit','')} → {k.get('target_value','?')}"
        for k in kpis[:4]
    ) or "  Sin KPIs"

    political_text = "  Sin perfil disponible"
    if territorial_profile:
        pol = territorial_profile.get("political", {})
        narr = territorial_profile.get("narrative", {})
        political_text = (
            f"  Tendencia: {pol.get('traditional_vote_tendency', 'N/D')}\n"
            f"  Competitividad: {pol.get('competitive_level', 'N/D')}\n"
            f"  Swing vote: {pol.get('swing_vote_pct', '?')}%\n"
            f"  Grupos clave: {', '.join(pol.get('key_electoral_groups', [])[:3])}\n"
            f"  Tono perfil: {narr.get('recommended_tone', 'N/D')}\n"
            f"  Temas sensibles: {', '.join(narr.get('sensitive_topics', [])[:2])}"
        )

    user_prompt = _USER_TEMPLATE.format(
        name=municipality_name,
        region=region,
        category=category,
        diagnosis_summary=diagnosis_summary[:800],
        needs_text=needs_text,
        opps_text=opps_text,
        political_text=political_text,
        kpi_text=kpi_text,
    )

    req = LLMRequest(
        messages=[
            LLMMessage(role="system", content=_SYSTEM),
            LLMMessage(role="user", content=user_prompt),
        ],
        temperature=0.65,
        max_tokens=2000,
        json_mode=True,
        purpose="analysis_strategy",
    )

    t0 = time.monotonic()
    try:
        resp = await _groq.complete(req)
        raw, ok = output_parser.parse_json(resp.content)
        if ok and isinstance(raw, dict):
            # Normalize messaging_axes to ensure dict structure
            axes = raw.get("messaging_axes", [])
            if axes and isinstance(axes[0], dict):
                raw["messaging_axes"] = axes
            raw["ai_generated"] = True
            raw["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
            return raw
    except Exception as exc:
        logger.warning("Strategy LLM failed for %s: %s", municipality_name, exc)

    # Structural fallback
    return {
        "executive_strategic": diagnosis_summary[:300] if diagnosis_summary else "",
        "messaging_axes": [],
        "pain_points_ranked": [n.get("title", "") for n in critical_needs[:3]],
        "opportunities_ranked": opportunities[:3],
        "candidate_positioning": "",
        "recommended_tone": "moderado y propositivo",
        "risk_flags": [],
        "framing_suggestions": [],
        "communication_channels_priority": ["mitin", "reunion_vecinal"],
        "ai_generated": False,
        "latency_ms": round((time.monotonic() - t0) * 1000, 1),
    }