from abc import ABC, abstractmethod

from app.services.llm.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """
    Interfaz abstracta para proveedores LLM.

    Groq es el proveedor activo en esta implementación.
    Cualquier otro proveedor (OpenAI, Anthropic, Ollama, Mistral...)
    debe implementar esta interfaz para ser intercambiable.
    """

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Envía un request al LLM y devuelve la respuesta normalizada."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica disponibilidad del proveedor."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre del proveedor para logging y trazabilidad."""
        ...