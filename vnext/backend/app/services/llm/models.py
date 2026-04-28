from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    """Estructura agnóstica al proveedor para solicitudes LLM."""

    messages: list[LLMMessage]
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=32768)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    stream: bool = False
    json_mode: bool = False  # Activa response_format: json_object en Groq

    # Trazabilidad interna
    request_id: Optional[str] = None
    purpose: Optional[str] = None


class LLMUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    """Respuesta normalizada del proveedor LLM."""

    content: str
    model: str
    usage: Optional[LLMUsage] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
    provider: str = "unknown"
    latency_ms: Optional[float] = None
    json_mode: bool = False