"""
Enumerations used across models and services.
"""
import enum


class DataQualityLevel(str, enum.Enum):
    OFFICIAL_MUNICIPAL  = "official_municipal"
    OFFICIAL_STATE      = "official_state"
    CALIBRATED_ESTIMATE = "calibrated_estimate"
    UNAVAILABLE         = "unavailable"

    @property
    def confidence(self) -> float:
        return {
            "official_municipal": 1.0,
            "official_state": 0.7,
            "calibrated_estimate": 0.4,
            "unavailable": 0.0,
        }[self.value]

    @property
    def can_cite_as_fact(self) -> bool:
        return self == DataQualityLevel.OFFICIAL_MUNICIPAL

    @property
    def label_es(self) -> str:
        return {
            "official_municipal": "Dato oficial municipal",
            "official_state": "Dato oficial estatal",
            "calibrated_estimate": "Estimación regional calibrada",
            "unavailable": "Sin dato disponible",
        }[self.value]

    @property
    def prompt_prefix(self) -> str:
        """How this value appears in LLM prompts."""
        return {
            "official_municipal": "",
            "official_state": "~",
            "calibrated_estimate": "≈",
            "unavailable": "[N/D]",
        }[self.value]


class GeographicLevel(str, enum.Enum):
    MUNICIPAL = "municipal"
    STATE     = "state"
    NATIONAL  = "national"
    REGIONAL  = "regional"


class RunStatus(str, enum.Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    INVALID   = "invalid"


class BatchJobType(str, enum.Enum):
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"
    BRIEF    = "brief"
    SPEECH   = "speech"
    EXPORT   = "export"
