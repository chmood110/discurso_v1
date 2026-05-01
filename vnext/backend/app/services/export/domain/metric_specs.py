"""
Declarative catalogue of metrics extracted from ``EvidenceRecordDB``
and ``AnalysisRunDB``.

Each ``MetricSpec`` describes:
    - a list of *aliases* (the keys the metric may be stored under),
    - one or more *containers* in evidence (e.g. ``social_data``),
    - an optional *fallback container* in analysis,
    - a *formatter* turning a float into the display string,
    - an optional *display unit* (free-form, used for KPI cells).

Centralising this means the renderer never re-implements lookup logic;
it just asks ``extract_metric(Metric.FOO.value, ev, an)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ── Formatters ───────────────────────────────────────────────────────────────

def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def fmt_count(v: float) -> str:
    return f"{v:,.1f}"


def fmt_years(v: float) -> str:
    return f"{v:.1f}"


def fmt_int_pct(v: float) -> str:
    return f"{v:.0f}%"


# ── Spec ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricSpec:
    """Declarative description of how to find and render a metric."""

    name: str
    aliases: tuple[str, ...]
    evidence_containers: tuple[str, ...] = ()
    analysis_containers: tuple[str, ...] = ()
    formatter: Callable[[float], str] = fmt_count
    unit: str = ""
    # When evidence has only ``avg`` instead of ``value`` (legacy schema).
    accept_avg_key: bool = False


class Metric(Enum):
    """Catalogue of metrics consumed by the renderer."""

    POPULATION = MetricSpec(
        name="population",
        aliases=("population", "population_total", "total_population", "population_2020"),
        evidence_containers=("social_data",),
        analysis_containers=("demographic_profile",),
        formatter=fmt_count,
    )
    SCHOOLING = MetricSpec(
        name="schooling",
        aliases=(
            "schooling_years_avg",
            "average_schooling_years",
            "schooling_avg_years",
            "avg_schooling_years",
        ),
        evidence_containers=("social_data",),
        analysis_containers=("demographic_profile",),
        formatter=fmt_years,
        accept_avg_key=True,
    )
    POVERTY = MetricSpec(
        name="poverty",
        aliases=("poverty_rate_pct", "poverty_pct", "multidimensional_poverty_pct"),
        evidence_containers=("social_data",),
        formatter=fmt_pct,
    )
    INTERNET = MetricSpec(
        name="internet",
        aliases=("internet_households_pct", "internet_access_pct", "internet_pct"),
        evidence_containers=("infrastructure_data",),
        analysis_containers=("infrastructure_gaps",),
        formatter=fmt_pct,
    )


# ── Profile rows ─────────────────────────────────────────────────────────────
# Lists of metrics rendered together as a horizontal bar chart.

@dataclass(frozen=True)
class ProfileRow:
    label: str
    aliases: tuple[str, ...]


SOCIAL_PROFILE_ROWS: tuple[ProfileRow, ...] = (
    ProfileRow("Carencia seguridad social", ("lack_social_security_pct", "social_security_lack_pct")),
    ProfileRow("Carencia acceso a salud", ("lack_health_access_pct", "health_access_lack_pct")),
    ProfileRow("Inseguridad alimentaria", ("food_insecurity_pct", "food_lack_pct")),
    ProfileRow("Rezago educativo", ("educational_lag_pct", "education_lag_pct")),
    ProfileRow("Calidad de vivienda", ("housing_quality_pct", "housing_quality_lack_pct")),
    ProfileRow("Servicios básicos vivienda", ("basic_services_housing_pct", "housing_services_lack_pct")),
)


INFRA_PROFILE_ROWS: tuple[ProfileRow, ...] = (
    ProfileRow("Internet en hogares", ("internet_households_pct", "internet_access_pct", "internet_pct")),
    ProfileRow("Agua potable", ("water_households_pct", "water_access_pct")),
    ProfileRow("Drenaje", ("drainage_households_pct", "drainage_access_pct")),
    ProfileRow("Electricidad", ("electricity_households_pct", "electricity_access_pct")),
)
