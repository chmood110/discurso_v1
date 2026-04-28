"""Domain exceptions."""


class VoxPoliticaError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TerritoryNotFoundError(VoxPoliticaError):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(f"{entity} '{entity_id}' no encontrado en Tlaxcala.", "TERRITORY_NOT_FOUND")


class AnalysisNotFoundError(VoxPoliticaError):
    def __init__(self, municipality_id: str):
        super().__init__(f"Sin análisis vigente para {municipality_id}.", "ANALYSIS_NOT_FOUND")


class ValidationBlockedError(VoxPoliticaError):
    def __init__(self, blocking_count: int, first_issue: str):
        super().__init__(
            f"Output bloqueado por validación ({blocking_count} errores críticos). "
            f"Primer error: {first_issue}",
            "VALIDATION_BLOCKED",
        )


class SourceTextValidationError(VoxPoliticaError):
    def __init__(self, reason: str):
        super().__init__(f"Texto fuente inválido. {reason}".strip(), "SOURCE_TEXT_INVALID")


class LLMUnavailableError(VoxPoliticaError):
    def __init__(self, reason: str = ""):
        super().__init__(f"LLM no disponible. {reason}".strip(), "LLM_UNAVAILABLE")


class BatchJobNotFoundError(VoxPoliticaError):
    def __init__(self, job_id: str):
        super().__init__(f"BatchJob '{job_id}' no encontrado.", "BATCH_JOB_NOT_FOUND")


class LLMProviderError(VoxPoliticaError):
    def __init__(self, message: str = "Error en proveedor LLM", provider: str = "unknown"):
        super().__init__(f"[{provider}] {message}", "LLM_PROVIDER_ERROR")
        self.provider = provider