"""
Narrative content for needs and KPIs, indexed by category.

Replaces the ``if "pobreza" in low: ... elif "informal" in low: ...``
chains scattered across the original renderer with two things:

1. ``classify_need`` / ``classify_kpi`` — keyword tables converting free
   text into a stable ``Enum`` value.
2. ``NEED_NARRATIVES`` / ``KPI_RATIONALES`` — copy tables indexed by
   category, with formatter-friendly templates.

The renderer should never re-implement keyword logic locally. If a new
category is needed, add it in ``categories.py``, then extend the keyword
table here, then add its narrative.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.export.content.categories import (
    KpiCategory,
    NeedCategory,
    Severity,
)


# ── Need classification ──────────────────────────────────────────────────────

# Order matters: more specific keywords go first within a category.
NEED_KEYWORDS: dict[NeedCategory, tuple[str, ...]] = {
    NeedCategory.POVERTY: ("pobreza",),
    NeedCategory.INFORMALITY: ("seguridad social", "informal"),
    NeedCategory.HEALTH: ("salud",),
    NeedCategory.CONNECTIVITY: ("internet", "conectividad"),
    NeedCategory.EDUCATION: ("rezago educativo", "escolaridad", "educación"),
    NeedCategory.HOUSING: ("vivienda",),
}


def classify_need(title: str, description: str = "") -> NeedCategory:
    """Map a free-text need to its ``NeedCategory``."""
    text = f"{title} {description}".casefold()
    for category, keywords in NEED_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return NeedCategory.OTHER


# ── Narratives ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class NeedNarrative:
    why_it_matters: str
    implication_template: str  # uses ``{severity}`` placeholder


_DEFAULT_NEED_NARRATIVE = NeedNarrative(
    why_it_matters=(
        "Concentra impacto cotidiano sobre bienestar, acceso a servicios y "
        "estabilidad económica del hogar."
    ),
    implication_template=(
        "Implicación estratégica ({severity}): requiere intervención pública "
        "focalizada y seguimiento verificable."
    ),
)

NEED_NARRATIVES: dict[NeedCategory, NeedNarrative] = {
    NeedCategory.POVERTY: NeedNarrative(
        why_it_matters=(
            "Condiciona ingreso, consumo, continuidad educativa y capacidad de "
            "respuesta del hogar ante shocks."
        ),
        implication_template=(
            "Implicación estratégica ({severity}): requiere paquete integral "
            "de ingreso, servicios y focalización territorial."
        ),
    ),
    NeedCategory.INFORMALITY: NeedNarrative(
        why_it_matters=(
            "Eleva vulnerabilidad laboral y reduce protección frente a "
            "enfermedad, desempleo y vejez."
        ),
        implication_template=(
            "Implicación estratégica ({severity}): conviene articular "
            "formalización, empleo local y protección social."
        ),
    ),
    NeedCategory.HEALTH: NeedNarrative(
        why_it_matters=(
            "Afecta atención oportuna, gasto de bolsillo y resiliencia del "
            "hogar ante episodios críticos."
        ),
        implication_template=(
            "Implicación estratégica ({severity}): debe priorizarse cobertura "
            "efectiva, cercanía operativa y continuidad."
        ),
    ),
    NeedCategory.CONNECTIVITY: NeedNarrative(
        why_it_matters=(
            "Limita acceso a educación, empleo, trámites y servicios digitales."
        ),
        implication_template=_DEFAULT_NEED_NARRATIVE.implication_template,
    ),
    NeedCategory.OTHER: _DEFAULT_NEED_NARRATIVE,
}


def narrative_for_need(category: NeedCategory) -> NeedNarrative:
    return NEED_NARRATIVES.get(category, _DEFAULT_NEED_NARRATIVE)


def need_implication(category: NeedCategory, severity: Severity) -> str:
    return narrative_for_need(category).implication_template.format(
        severity=severity.value.upper()
    )


def need_why_it_matters(category: NeedCategory) -> str:
    return narrative_for_need(category).why_it_matters


# ── KPI classification ───────────────────────────────────────────────────────

KPI_KEYWORDS: dict[KpiCategory, tuple[str, ...]] = {
    KpiCategory.POVERTY: ("pobreza",),
    KpiCategory.EMPLOYMENT: ("informal", "empleo"),
    KpiCategory.HEALTH: ("salud",),
    KpiCategory.CONNECTIVITY: ("internet", "conectividad"),
    KpiCategory.WATER: ("agua",),
}


def classify_kpi(name: str) -> KpiCategory:
    text = (name or "").casefold()
    for category, keywords in KPI_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return KpiCategory.OTHER


KPI_RATIONALES: dict[KpiCategory, str] = {
    KpiCategory.POVERTY: (
        "La mejora depende de combinar ingreso, acceso a servicios y "
        "reducción de vulnerabilidad social."
    ),
    KpiCategory.EMPLOYMENT: (
        "El avance exige formalización productiva y encadenamientos con "
        "{sectors}."
    ),
    KpiCategory.HEALTH: (
        "La reducción exige cobertura efectiva, menor fricción de acceso y "
        "continuidad en la atención."
    ),
    KpiCategory.CONNECTIVITY: (
        "La conectividad tiene efecto multiplicador en educación, empleo, "
        "trámites y acceso a servicios."
    ),
    KpiCategory.WATER: (
        "La meta debe leerse como sostenimiento de cobertura con mejora de "
        "calidad y continuidad."
    ),
}


def kpi_rationale(
    name: str,
    *,
    baseline: float | None,
    target: float | None,
    unit: str,
    sectors: list[str],
    opportunities: list[str] | None = None,
) -> str:
    """Return the rationale string for a KPI.

    Resolution order (preserves the original renderer's behavior):
      1. Category-specific narrative if the name matches a known category.
      2. The first available *opportunity* string from the analysis,
         used as a free-form rationale when no category matches.
         (Kept for behavior parity; consider removing in a future PR.)
      3. A quantitative description ("Se propone mover desde X hasta Y …")
         when baseline, target and unit are all present.
      4. A generic safety-net string.
    """
    category = classify_kpi(name)
    template = KPI_RATIONALES.get(category)

    if template is not None:
        sectors_text = ", ".join(sectors[:2]) if sectors else "la economía local"
        return template.format(sectors=sectors_text)

    # Behavior-parity fallback (legacy): first opportunity as rationale.
    if opportunities:
        first = next((o for o in opportunities if o), "")
        if first:
            return first

    if baseline is not None and target is not None and unit:
        return (
            f"Se propone mover el indicador desde {baseline:,.1f} hasta "
            f"{target:,.1f} {unit} con una meta verificable."
        )

    return (
        "Meta alineada al diagnóstico territorial y diseñada para "
        "seguimiento verificable."
    )
