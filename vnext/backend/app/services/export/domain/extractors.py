"""
Generic metric extractors.

This module centralizes all safe data extraction used by PDF renderers.

It supports:
    - Traditional metrics from EvidenceRecordDB / AnalysisRunDB.
    - Social and infrastructure profile rows.
    - Local economic sectors.
    - Sources and quality metadata.
    - API enrichment fields produced by EvidenceApiBuilder / DENUE normalizer.
    - Flexible DENUE/API payload shapes for PDF rendering.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from app.services.export.domain.metric_specs import (
    INFRA_PROFILE_ROWS,
    SOCIAL_PROFILE_ROWS,
    MetricSpec,
    ProfileRow,
)
from app.services.export.domain.safe_access import (
    as_dict,
    as_float,
    as_list,
    as_text,
    dedupe_preserving_order,
)

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Generic metric extraction
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractedMetric:
    """A successfully resolved metric value with provenance."""

    spec: MetricSpec
    value: float
    text: str
    found_in: str


def _lookup_in(container: dict[str, Any], spec: MetricSpec) -> float | None:
    """Try every alias against a single container; return the first numeric hit."""
    for alias in spec.aliases:
        entry = container.get(alias)

        if not isinstance(entry, dict):
            continue

        raw = entry.get("value")

        if raw is None and spec.accept_avg_key:
            raw = entry.get("avg")

        value = as_float(raw)

        if value is not None:
            return value

    return None


def extract_metric(
    spec: MetricSpec,
    evidence: Any,
    analysis: Any,
) -> ExtractedMetric | None:
    """
    Resolve a metric from evidence first, then fall back to analysis.

    Returns None if no alias matches in any source.
    """
    sources: list[tuple[str, dict[str, Any]]] = []

    if evidence is not None:
        for container in spec.evidence_containers:
            sources.append(
                (
                    f"evidence.{container}",
                    as_dict(
                        getattr(evidence, container, None),
                        context=f"evidence.{container}",
                    ),
                )
            )

    for container in spec.analysis_containers:
        sources.append(
            (
                f"analysis.{container}",
                as_dict(
                    getattr(analysis, container, None),
                    context=f"analysis.{container}",
                ),
            )
        )

    for source_name, payload in sources:
        value = _lookup_in(payload, spec)

        if value is not None:
            return ExtractedMetric(
                spec=spec,
                value=value,
                text=spec.formatter(value),
                found_in=source_name,
            )

    log.debug("metric %s not found in any source", spec.name)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Safe generic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _first_present(payload: dict[str, Any], keys: Iterable[str]) -> Any:
    """
    Return the first existing value from a dictionary using multiple possible keys.

    Supports both:
        {"key": {"value": ...}}
    and:
        {"key": ...}
    """
    for key in keys:
        if key not in payload:
            continue

        item = payload.get(key)

        if isinstance(item, dict) and "value" in item:
            return item.get("value")

        return item

    return None


def _extract_nested_value(
    payload: dict[str, Any],
    key: str,
) -> Any:
    """
    Extract value from the standard enriched shape:

        {
            "some_key": {
                "value": ...
            }
        }

    If the key points directly to a primitive/list, return it as fallback.
    """
    item = payload.get(key)

    if isinstance(item, dict) and "value" in item:
        return item.get("value")

    return item


def _deep_get(payload: Any, path: Iterable[str]) -> Any:
    """
    Safely get a nested value from a dictionary-like object.

    Example:
        _deep_get(data, ["api", "denue", "summary"])
    """
    current = payload

    for key in path:
        current_dict = as_dict(current)

        if key not in current_dict:
            return None

        current = current_dict.get(key)

    if isinstance(current, dict) and "value" in current:
        return current.get("value")

    return current


def _collect_candidate_containers(*containers: Any) -> list[dict[str, Any]]:
    """
    Build a list of possible containers where API/DENUE data may have been stored.

    This is intentionally tolerant because different stages of the backend may save:
        - values directly inside economic_data / infrastructure_data
        - values inside denue
        - values inside api
        - values inside api.denue
        - values inside denue_summary
        - values inside raw / payload / metadata
    """
    result: list[dict[str, Any]] = []

    for container in containers:
        base = as_dict(container)

        if base:
            result.append(base)

        for key in (
            "api",
            "denue",
            "denue_api",
            "denue_summary",
            "api_enrichment",
            "enrichment",
            "enriched",
            "raw",
            "payload",
            "metadata",
            "data",
            "summary",
        ):
            nested = as_dict(base.get(key))
            if nested:
                result.append(nested)

        api = as_dict(base.get("api"))
        denue_inside_api = as_dict(api.get("denue"))
        if denue_inside_api:
            result.append(denue_inside_api)

        denue = as_dict(base.get("denue"))
        summary_inside_denue = as_dict(denue.get("summary"))
        if summary_inside_denue:
            result.append(summary_inside_denue)

        data_inside_denue = as_dict(denue.get("data"))
        if data_inside_denue:
            result.append(data_inside_denue)

        payload_inside_denue = as_dict(denue.get("payload"))
        if payload_inside_denue:
            result.append(payload_inside_denue)

    deduped: list[dict[str, Any]] = []
    seen: set[int] = set()

    for item in result:
        marker = id(item)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(item)

    return deduped


def _find_first_value(containers: Iterable[dict[str, Any]], keys: Iterable[str]) -> Any:
    """Find the first value matching any key in any container."""
    for container in containers:
        value = _first_present(container, keys)

        if value is not None:
            return value

    return None


def _normalize_count(value: Any) -> int | None:
    """Normalize numeric values to integer counts."""
    number = as_float(value)

    if number is None:
        return None

    return int(number)


def _normalize_share(value: Any) -> float:
    """Normalize percentage/share values safely."""
    number = as_float(value)

    if number is None:
        return 0.0

    return float(number)


def _normalize_denue_rows(
    rows: Any,
    *,
    label_keys: Iterable[str],
    output_label_key: str,
) -> list[dict[str, Any]]:
    """
    Normalize generic DENUE distribution rows.

    Accepts rows like:
        {"sector": "...", "count": 10, "share_pct": 20.5}
        {"name": "...", "total": 10, "percentage": 20.5}
        {"label": "...", "value": 10, "pct": 20.5}
    """
    cleaned: list[dict[str, Any]] = []

    for row in as_list(rows):
        data = as_dict(row)

        label = as_text(_first_present(data, label_keys))

        count = as_float(
            _first_present(
                data,
                (
                    "count",
                    "total",
                    "value",
                    "units",
                    "business_units",
                    "establecimientos",
                    "ue",
                    "unidades",
                    "n",
                ),
            )
        )

        share = as_float(
            _first_present(
                data,
                (
                    "share_pct",
                    "share",
                    "percentage",
                    "percent",
                    "pct",
                    "porcentaje",
                ),
            )
        )

        if not label or count is None:
            continue

        cleaned.append(
            {
                output_label_key: label,
                "count": int(count),
                "share_pct": float(share or 0.0),
            }
        )

    return cleaned


def _build_distribution_from_raw_denue_records(
    records: Any,
    *,
    field_keys: Iterable[str],
    output_label_key: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Build a distribution from raw DENUE records.

    Useful when the API response was stored as a raw list of establishments instead of
    precomputed summaries.
    """
    items = as_list(records)

    if not items:
        return []

    counts: dict[str, int] = {}

    for item in items:
        data = as_dict(item)

        label = ""

        for key in field_keys:
            label = as_text(data.get(key))
            if label:
                break

        if not label:
            continue

        counts[label] = counts.get(label, 0) + 1

    total = sum(counts.values())

    if total <= 0:
        return []

    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:limit]

    return [
        {
            output_label_key: label,
            "count": count,
            "share_pct": (count / total) * 100,
        }
        for label, count in ranked
    ]


def _find_raw_denue_records(evidence: Any) -> list[Any]:
    """
    Try to locate raw DENUE establishment records in evidence.

    Common shapes:
        evidence.economic_data["denue_records"]
        evidence.economic_data["records"]
        evidence.economic_data["items"]
        evidence.economic_data["results"]
        evidence.economic_data["data"]
        evidence.raw_data["denue"]
    """
    if not evidence:
        return []

    containers = _collect_candidate_containers(
        getattr(evidence, "economic_data", None),
        getattr(evidence, "infrastructure_data", None),
        getattr(evidence, "raw_data", None),
        getattr(evidence, "metadata", None),
    )

    for container in containers:
        rows = _find_first_value(
            [container],
            (
                "denue_records",
                "denue_results",
                "records",
                "items",
                "results",
                "establecimientos",
                "businesses",
                "business_units",
                "unidades_economicas",
            ),
        )

        if as_list(rows):
            return as_list(rows)

    return []


# ─────────────────────────────────────────────────────────────────────────────
# Profile rows: social / infrastructure bar charts
# ─────────────────────────────────────────────────────────────────────────────

def extract_profile_rows(
    container: dict[str, Any],
    rows: Iterable[ProfileRow],
) -> list[tuple[str, float]]:
    """Resolve each row's first matching alias and return (label, value)."""
    out: list[tuple[str, float]] = []

    for row in rows:
        for alias in row.aliases:
            entry = container.get(alias)

            if not isinstance(entry, dict):
                continue

            value = as_float(entry.get("value"))

            if value is not None:
                out.append((row.label, value))
                break

    return out


def extract_social_rows(evidence: Any) -> list[tuple[str, float]]:
    if not evidence:
        return []

    return extract_profile_rows(
        as_dict(getattr(evidence, "social_data", None)),
        SOCIAL_PROFILE_ROWS,
    )


def extract_infra_rows(evidence: Any) -> list[tuple[str, float]]:
    if not evidence:
        return []

    return extract_profile_rows(
        as_dict(getattr(evidence, "infrastructure_data", None)),
        INFRA_PROFILE_ROWS,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Economic sectors: legacy/reference shape
# ─────────────────────────────────────────────────────────────────────────────

def extract_economic_sectors(evidence: Any) -> list[str]:
    """List of main economic sectors. Tolerant of multiple legacy shapes."""
    if not evidence:
        return []

    econ = as_dict(getattr(evidence, "economic_data", None))

    sectors = econ.get("main_sectors") or econ.get("sectors")

    if isinstance(sectors, list):
        return [as_text(item) for item in sectors if as_text(item)]

    if isinstance(sectors, str):
        return [item.strip() for item in sectors.split("·") if item.strip()]

    main_activity = as_dict(econ.get("main_activity"))
    value = as_text(main_activity.get("value"))

    return [value] if value else []


# ─────────────────────────────────────────────────────────────────────────────
# API enrichment: DENUE / Banxico
# ─────────────────────────────────────────────────────────────────────────────

def extract_api_business_units(evidence: Any) -> int | None:
    """
    Extract total business units from API-enriched economic data.

    Supports legacy exact field:
        evidence.economic_data["business_units_total_api"]["value"]

    Also supports flexible aliases:
        total_units, total_business_units, denue_total, total, count, etc.
    """
    if not evidence:
        return None

    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(econ, raw_data, metadata)

    value = _find_first_value(
        containers,
        (
            "business_units_total_api",
            "business_units_total",
            "total_business_units_api",
            "total_business_units",
            "business_units_count_api",
            "business_units_count",
            "denue_business_units_total",
            "denue_business_units",
            "denue_total",
            "denue_count",
            "total_units",
            "total_unidades",
            "unidades_economicas_total",
            "unidades_economicas",
            "establecimientos_total",
            "establecimientos",
            "total_establishments",
            "total_records",
            "records_count",
            "count",
            "total",
        ),
    )

    count = _normalize_count(value)

    if count is not None:
        return count

    raw_records = _find_raw_denue_records(evidence)

    if raw_records:
        return len(raw_records)

    return None


def extract_api_sector_distribution(evidence: Any) -> list[dict[str, Any]]:
    """
    Extract DENUE sector distribution.

    Expected preferred field:
        evidence.economic_data["sector_distribution_api"]["value"]

    Output:
        [
            {"sector": "...", "count": 123, "share_pct": 45.6},
            ...
        ]
    """
    if not evidence:
        return []

    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(econ, raw_data, metadata)

    rows = _find_first_value(
        containers,
        (
            "sector_distribution_api",
            "sector_distribution",
            "sectors_distribution_api",
            "sectors_distribution",
            "sector_breakdown_api",
            "sector_breakdown",
            "denue_sector_distribution",
            "denue_sectors",
            "sectors_api",
            "sectors",
            "sectores",
            "distribution_by_sector",
            "by_sector",
        ),
    )

    cleaned = _normalize_denue_rows(
        rows,
        label_keys=(
            "sector",
            "name",
            "label",
            "category",
            "categoria",
            "sector_name",
            "nombre",
        ),
        output_label_key="sector",
    )

    if cleaned:
        return cleaned

    raw_records = _find_raw_denue_records(evidence)

    return _build_distribution_from_raw_denue_records(
        raw_records,
        field_keys=(
            "Sector",
            "sector",
            "sector_nombre",
            "Nombre_sector",
            "Clase_actividad",
            "clase_actividad",
            "actividad",
            "Actividad",
        ),
        output_label_key="sector",
        limit=10,
    )


def extract_api_top_activities(evidence: Any) -> list[dict[str, Any]]:
    """
    Extract top DENUE economic activities.

    Expected preferred field:
        evidence.economic_data["top_economic_activities_api"]["value"]
    """
    if not evidence:
        return []

    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(econ, raw_data, metadata)

    rows = _find_first_value(
        containers,
        (
            "top_economic_activities_api",
            "top_economic_activities",
            "economic_activities_api",
            "economic_activities",
            "top_activities_api",
            "top_activities",
            "activities_distribution_api",
            "activities_distribution",
            "denue_top_activities",
            "denue_activities",
            "actividades_economicas",
            "principales_actividades",
            "by_activity",
        ),
    )

    cleaned = _normalize_denue_rows(
        rows,
        label_keys=(
            "activity",
            "actividad",
            "Clase_actividad",
            "clase_actividad",
            "name",
            "label",
            "category",
            "nombre",
        ),
        output_label_key="activity",
    )

    if cleaned:
        return cleaned

    raw_records = _find_raw_denue_records(evidence)

    return _build_distribution_from_raw_denue_records(
        raw_records,
        field_keys=(
            "Clase_actividad",
            "clase_actividad",
            "activity",
            "actividad",
            "Nombre_act",
            "nombre_actividad",
        ),
        output_label_key="activity",
        limit=10,
    )


def extract_api_business_size_distribution(evidence: Any) -> list[dict[str, Any]]:
    """
    Extract DENUE business size distribution.

    Expected preferred field:
        evidence.economic_data["business_size_distribution_api"]["value"]
    """
    if not evidence:
        return []

    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(econ, raw_data, metadata)

    rows = _find_first_value(
        containers,
        (
            "business_size_distribution_api",
            "business_size_distribution",
            "size_distribution_api",
            "size_distribution",
            "business_sizes_api",
            "business_sizes",
            "denue_size_distribution",
            "denue_business_sizes",
            "estrato_distribution",
            "estratos",
            "by_size",
        ),
    )

    cleaned = _normalize_denue_rows(
        rows,
        label_keys=(
            "size",
            "estrato",
            "Estrato",
            "name",
            "label",
            "category",
            "nombre",
        ),
        output_label_key="size",
    )

    if cleaned:
        return cleaned

    raw_records = _find_raw_denue_records(evidence)

    return _build_distribution_from_raw_denue_records(
        raw_records,
        field_keys=(
            "Estrato",
            "estrato",
            "size",
            "tamano",
            "tamaño",
            "personal_ocupado",
        ),
        output_label_key="size",
        limit=10,
    )


def extract_api_business_neighborhoods(evidence: Any) -> list[dict[str, Any]]:
    """
    Extract DENUE neighborhood concentration.

    Expected preferred field:
        evidence.economic_data["top_neighborhoods_business_api"]["value"]
    """
    if not evidence:
        return []

    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(econ, raw_data, metadata)

    rows = _find_first_value(
        containers,
        (
            "top_neighborhoods_business_api",
            "top_neighborhoods_business",
            "business_neighborhoods_api",
            "business_neighborhoods",
            "top_neighborhoods_api",
            "top_neighborhoods",
            "neighborhood_distribution_api",
            "neighborhood_distribution",
            "denue_neighborhoods",
            "colonias",
            "zonas",
            "by_neighborhood",
            "by_colonia",
        ),
    )

    cleaned = _normalize_denue_rows(
        rows,
        label_keys=(
            "neighborhood",
            "colonia",
            "Colonia",
            "zone",
            "zona",
            "name",
            "label",
            "category",
            "nombre",
        ),
        output_label_key="neighborhood",
    )

    if cleaned:
        return cleaned

    raw_records = _find_raw_denue_records(evidence)

    return _build_distribution_from_raw_denue_records(
        raw_records,
        field_keys=(
            "Colonia",
            "colonia",
            "neighborhood",
            "barrio",
            "zone",
            "zona",
            "localidad",
            "Localidad",
        ),
        output_label_key="neighborhood",
        limit=10,
    )


def extract_api_health_facilities(evidence: Any) -> int | None:
    """
    Extract health-related DENUE establishments count.

    Expected preferred field:
        evidence.infrastructure_data["health_facilities_count_api"]["value"]

    Also supports values stored in economic_data or raw DENUE records.
    """
    if not evidence:
        return None

    infra = as_dict(getattr(evidence, "infrastructure_data", None))
    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(infra, econ, raw_data, metadata)

    value = _find_first_value(
        containers,
        (
            "health_facilities_count_api",
            "health_facilities_count",
            "health_facilities_api",
            "health_facilities",
            "health_units_api",
            "health_units",
            "denue_health_count",
            "denue_health_facilities",
            "salud_count",
            "salud",
            "establecimientos_salud",
            "unidades_salud",
            "medical_facilities",
            "clinics_count",
            "hospitals_count",
        ),
    )

    count = _normalize_count(value)

    if count is not None:
        return count

    raw_records = _find_raw_denue_records(evidence)

    if not raw_records:
        return None

    keywords = (
        "salud",
        "hospital",
        "clínica",
        "clinica",
        "consultorio",
        "médico",
        "medico",
        "dental",
        "farmacia",
        "laboratorio médico",
        "laboratorio medico",
    )

    total = 0

    for record in raw_records:
        data = as_dict(record)
        text = " ".join(
            [
                as_text(data.get("Clase_actividad")),
                as_text(data.get("clase_actividad")),
                as_text(data.get("Nombre")),
                as_text(data.get("nombre")),
                as_text(data.get("Razon_social")),
                as_text(data.get("razon_social")),
            ]
        ).lower()

        if any(keyword in text for keyword in keywords):
            total += 1

    return total if total > 0 else None


def extract_api_schools_count(evidence: Any) -> int | None:
    """
    Extract education-related DENUE establishments count.

    Expected preferred field:
        evidence.infrastructure_data["schools_count_api"]["value"]

    Also supports values stored in economic_data or raw DENUE records.
    """
    if not evidence:
        return None

    infra = as_dict(getattr(evidence, "infrastructure_data", None))
    econ = as_dict(getattr(evidence, "economic_data", None))
    raw_data = as_dict(getattr(evidence, "raw_data", None))
    metadata = as_dict(getattr(evidence, "metadata", None))

    containers = _collect_candidate_containers(infra, econ, raw_data, metadata)

    value = _find_first_value(
        containers,
        (
            "schools_count_api",
            "schools_count",
            "education_facilities_count_api",
            "education_facilities_count",
            "education_facilities_api",
            "education_facilities",
            "school_facilities",
            "school_units",
            "denue_schools_count",
            "denue_education_count",
            "escuelas_count",
            "escuelas",
            "establecimientos_educacion",
            "unidades_educacion",
            "educacion",
            "educación",
        ),
    )

    count = _normalize_count(value)

    if count is not None:
        return count

    raw_records = _find_raw_denue_records(evidence)

    if not raw_records:
        return None

    keywords = (
        "escuela",
        "educación",
        "educacion",
        "colegio",
        "instituto",
        "universidad",
        "preescolar",
        "primaria",
        "secundaria",
        "bachillerato",
        "capacitación",
        "capacitacion",
    )

    total = 0

    for record in raw_records:
        data = as_dict(record)
        text = " ".join(
            [
                as_text(data.get("Clase_actividad")),
                as_text(data.get("clase_actividad")),
                as_text(data.get("Nombre")),
                as_text(data.get("nombre")),
                as_text(data.get("Razon_social")),
                as_text(data.get("razon_social")),
            ]
        ).lower()

        if any(keyword in text for keyword in keywords):
            total += 1

    return total if total > 0 else None


def extract_banxico_reference_rate(evidence: Any) -> dict[str, Any] | None:
    """
    Extract Banxico reference-rate enrichment if available.

    This is usually useful as technical context, not as a territorial PDF metric.
    """
    if not evidence:
        return None

    econ = as_dict(getattr(evidence, "economic_data", None))
    item = as_dict(econ.get("banxico_reference_rate"))

    value = as_float(item.get("value"))

    if value is None:
        return None

    return {
        "value": value,
        "date": as_text(item.get("date")),
        "series_id": as_text(item.get("series_id")),
        "title": as_text(item.get("title")),
        "source": as_text(item.get("source"), "Banxico SIE"),
        "scope": as_text(item.get("scope"), "national"),
        "use_in_pdf": bool(item.get("use_in_pdf", False)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sources
# ─────────────────────────────────────────────────────────────────────────────

def extract_sources(evidence: Any) -> list[str]:
    """Deduplicate case-insensitive list of sources used."""
    if not evidence:
        return []

    raw = (as_text(item) for item in as_list(getattr(evidence, "sources_used", None)))

    return dedupe_preserving_order(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Quality / coverage metadata
# ─────────────────────────────────────────────────────────────────────────────

def extract_confidence(evidence: Any, analysis: Any) -> tuple[str, float | None]:
    """Confidence as ('xx%', float) or ('N/D', None)."""
    raw = (
        getattr(evidence, "overall_confidence", None)
        if evidence
        else getattr(analysis, "overall_confidence", None)
    )

    n = as_float(raw)

    if n is None:
        return "N/D", None

    if n <= 1:
        n *= 100

    return f"{n:.0f}%", n


def extract_municipal_coverage(evidence: Any) -> tuple[str, float | None]:
    if not evidence:
        return "N/D", None

    n = as_float(getattr(evidence, "municipal_coverage_pct", None))

    if n is not None and n <= 1:
        n *= 100

    return (f"{n:.0f}%" if n is not None else "N/D"), n


def extract_estimated_coverage(evidence: Any) -> tuple[str, float | None]:
    if not evidence:
        return "N/D", None

    n = as_float(getattr(evidence, "estimated_coverage_pct", None))

    if n is not None and n <= 1:
        n *= 100

    return (f"{n:.0f}%" if n is not None else "N/D"), n


def extract_quality_label(evidence: Any) -> str:
    if not evidence:
        return "Sin evidencia adjunta"

    return as_text(getattr(evidence, "quality_label", None), "Sin etiqueta")