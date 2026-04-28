from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PromptTemplate:
    """
    Contenedor para un prompt completo listo para enviar al LLM.
    Incluye system prompt, user prompt y parámetros de generación.
    """

    system_prompt: str
    user_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4096
    purpose: str = "general"
    output_format: str = "text"  # "text" | "json"
    metadata: dict = field(default_factory=dict)


@dataclass
class PromptContext:
    """
    Contexto ensamblado para inyección en prompts.
    Centraliza todos los inputs necesarios para construir prompts
    de alta densidad estratégica sobre el territorio tlaxcalteca.
    """

    # Territorio (siempre Tlaxcala)
    territory_text: str = ""
    municipality_name: str = ""
    neighborhood_name: str = ""
    pain_points: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    sensitive_topics: list[str] = field(default_factory=list)
    recommended_tone: str = "moderado"
    framing_suggestions: list[str] = field(default_factory=list)
    political_tendency: str = ""

    # Candidato
    candidate_name: Optional[str] = None
    candidate_party: Optional[str] = None
    candidate_position: Optional[str] = None
    candidate_style: Optional[str] = None
    candidate_values: list[str] = field(default_factory=list)
    candidate_municipality: Optional[str] = None

    # Discurso
    speech_goal: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    channel: Optional[str] = None
    duration_minutes: Optional[int] = None
    priority_topics: list[str] = field(default_factory=list)
    avoid_topics: list[str] = field(default_factory=list)
    source_text: Optional[str] = None
    electoral_moment: Optional[str] = None

    # Campaña
    campaign_objective: Optional[str] = None
    tone_preferences: list[str] = field(default_factory=list)
    electoral_period: Optional[str] = None