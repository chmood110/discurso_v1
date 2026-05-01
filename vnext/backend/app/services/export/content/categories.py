"""
Stable, language-independent identifiers for needs and KPIs.

These enums replace the original substring-matching scattered across
``_need_why_it_matters``, ``_need_implication`` and ``_kpi_rationale``.

Adding a new category? Add it here, then add its keywords in
``classifiers.py`` and its narrative in ``narratives.py``. The renderer
itself doesn't need to change.
"""
from __future__ import annotations

from enum import Enum


class NeedCategory(str, Enum):
    """High-level grouping of critical-need entries."""

    POVERTY = "poverty"
    INFORMALITY = "informality"
    HEALTH = "health"
    CONNECTIVITY = "connectivity"
    EDUCATION = "education"
    HOUSING = "housing"
    OTHER = "other"


class KpiCategory(str, Enum):
    """High-level grouping for KPI rationales."""

    POVERTY = "poverty"
    EMPLOYMENT = "employment"      # includes informality / formal employment
    HEALTH = "health"
    CONNECTIVITY = "connectivity"
    WATER = "water"
    OTHER = "other"


class Severity(str, Enum):
    """Severity tier used for need cards (panel colors + title color)."""

    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baja"

    @classmethod
    def from_text(cls, raw: str) -> "Severity":
        clean = (raw or "").strip().casefold()
        for member in cls:
            if member.value == clean:
                return member
        return cls.MEDIUM
