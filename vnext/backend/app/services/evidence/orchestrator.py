"""
EvidenceOrchestrator — single source of truth for evidence resolution.

Resolution order:
  1. DB cache (fresh + matching snapshot_version)
  2. Reference data (region/category-calibrated or municipal real data)
  3. Live API enrichment (INEGI DENUE + Banxico if configured)

Never throws for API failures — always returns a record with explicit quality signals.
"""
from __future__ import annotations

import hashlib
import inspect
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import TerritoryNotFoundError
from app.db.repositories.evidence_repo import EvidenceRepository
from app.models.db_models import EvidenceRecordDB
from app.services.evidence.evidence_api_builder import EvidenceApiBuilder
from app.services.evidence.reference_data import get_reference_pack
from app.services.integrations import banxico_client as banxico
from app.services.territory.repository import TerritoryRepository

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot / cache version
# ─────────────────────────────────────────────────────────────────────────────

def _snapshot_version() -> str:
    """
    Hash of reference_data.py + territory schema + API integration marker.

    Important:
        The marker forces cache invalidation after integrating DENUE BuscarAreaAct.
        If this marker changes, cached evidence will be rebuilt.
    """
    try:
        import app.services.evidence.reference_data as rd

        src = inspect.getsource(rd)
        repo_version = TerritoryRepository.get_instance().get_schema_version()

        api_marker = "reference-plus-api-denue-areaact-v3"
        combined = src + repo_version + api_marker

        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    except Exception:
        return "reference-plus-api-denue-areaact-v3"


# ─────────────────────────────────────────────────────────────────────────────
# Data quality
# ─────────────────────────────────────────────────────────────────────────────

def _compute_quality(pack) -> dict[str, Any]:
    """Compute OverallDataQuality from an EvidencePack's DataPoints."""
    points = []

    for layer_name in ("social", "economic", "infrastructure"):
        layer = getattr(pack, layer_name, None)

        if not layer:
            continue

        for _, val in layer.__dict__.items():
            if hasattr(val, "available") and hasattr(val, "geographic_level"):
                points.append(val)

    if not points:
        return _unavailable_quality()

    n = len(points)

    counts: dict[str, int] = {
        "official_municipal": 0,
        "official_state": 0,
        "calibrated_estimate": 0,
        "unavailable": 0,
    }

    for p in points:
        if not p.available or getattr(p, "value", None) is None:
            counts["unavailable"] += 1
            continue

        level = getattr(p, "geographic_level", "municipal") or "municipal"

        if level == "municipal":
            counts["official_municipal"] += 1
        elif level in ("estatal", "state", "nacional", "national"):
            counts["official_state"] += 1
        elif level in ("regional", "estimated"):
            counts["calibrated_estimate"] += 1
        else:
            counts["official_municipal"] += 1

    mun_pct = counts["official_municipal"] / n * 100
    stat_pct = counts["official_state"] / n * 100
    est_pct = counts["calibrated_estimate"] / n * 100
    una_pct = counts["unavailable"] / n * 100

    confidence = (mun_pct * 1.0 + stat_pct * 0.7 + est_pct * 0.4) / 100
    can_cite = mun_pct >= 50

    if mun_pct >= 80:
        label = "Alta — datos oficiales municipales"
        disclaimer = ""
    elif mun_pct >= 30:
        label = "Media — mezcla de datos oficiales y estatales"
        disclaimer = (
            "NOTA METODOLÓGICA: Este análisis combina datos oficiales municipales con datos "
            "a nivel estatal. Las cifras de escala estatal son orientativas para el municipio."
        )
    else:
        label = "Baja — estimaciones regionales calibradas"
        disclaimer = (
            "NOTA METODOLÓGICA IMPORTANTE: Por ausencia de datos municipales específicos, "
            "este análisis utiliza estimaciones calibradas por región y categoría de municipio, "
            "basadas en los rangos documentados por CONEVAL e INEGI para Tlaxcala (2020). "
            "Las cifras son aproximaciones orientativas — NO estadísticas municipales exactas. "
            "Deben interpretarse como rangos de referencia para orientar estrategia, "
            "no como datos censales precisos de este municipio."
        )

    return {
        "overall_confidence": round(confidence, 2),
        "municipal_coverage_pct": round(mun_pct, 1),
        "state_coverage_pct": round(stat_pct, 1),
        "estimated_coverage_pct": round(est_pct, 1),
        "unavailable_pct": round(una_pct, 1),
        "can_cite_as_municipal": can_cite,
        "quality_label": label,
        "methodology_disclaimer": disclaimer,
    }


def _unavailable_quality() -> dict[str, Any]:
    return {
        "overall_confidence": 0.0,
        "municipal_coverage_pct": 0.0,
        "state_coverage_pct": 0.0,
        "estimated_coverage_pct": 0.0,
        "unavailable_pct": 100.0,
        "can_cite_as_municipal": False,
        "quality_label": "Sin datos",
        "methodology_disclaimer": "No hay datos disponibles para este municipio.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Safe helpers
# ─────────────────────────────────────────────────────────────────────────────

def _merge_dicts(
    base: dict[str, Any] | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Merge two dictionaries preserving base values and adding/replacing with extra.

    API-enriched values intentionally override same-key reference values because
    they are more specific for fields such as DENUE distributions.
    """
    merged: dict[str, Any] = {}

    if isinstance(base, dict):
        merged.update(base)

    if isinstance(extra, dict):
        for key, value in extra.items():
            if value is not None:
                merged[key] = value

    return merged


def _dedupe_list(values: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """Deduplicate a list while preserving order."""
    if not values:
        return []

    result: list[Any] = []
    seen: set[str] = set()

    for value in values:
        marker = str(value).strip()

        if not marker or marker in seen:
            continue

        seen.add(marker)
        result.append(value)

    return result


def _as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _has_meaningful_api_data(api_snapshot: dict[str, Any]) -> bool:
    """
    Determine if the API snapshot contains useful DENUE enrichment.

    Banxico alone should not count as meaningful PDF enrichment, because it is
    national macro context and has use_in_pdf=False.
    """
    if not api_snapshot:
        return False

    economic_data = api_snapshot.get("economic_data") or {}
    infrastructure_data = api_snapshot.get("infrastructure_data") or {}

    denue_economic_keys = {
        "business_units_total_api",
        "sector_distribution_api",
        "top_economic_activities_api",
        "business_size_distribution_api",
        "top_neighborhoods_business_api",
    }

    denue_infra_keys = {
        "health_facilities_count_api",
        "schools_count_api",
    }

    return any(key in economic_data for key in denue_economic_keys) or any(
        key in infrastructure_data for key in denue_infra_keys
    )


# ─────────────────────────────────────────────────────────────────────────────
# Coordinates
# ─────────────────────────────────────────────────────────────────────────────

def _first_float_from(
    payload: dict[str, Any] | None,
    keys: tuple[str, ...],
) -> float | None:
    if not isinstance(payload, dict):
        return None

    for key in keys:
        value = _as_float(payload.get(key))

        if value is not None:
            return value

    return None


def _resolve_coordinates(
    repo: TerritoryRepository,
    municipality_id: str,
    municipality: dict[str, Any] | None,
) -> tuple[float | None, float | None, str | None]:
    """
    Resolve coordinates for DENUE fallback.

    Priority:
        1. Municipality fields if present.
        2. Neighborhood/reference AGEEML municipal seat fields.
        3. None if unavailable.
    """
    lat = _first_float_from(
        municipality,
        (
            "lat",
            "latitude",
            "lat_decimal",
            "seat_lat_decimal",
            "municipal_seat_lat",
            "cabecera_lat",
        ),
    )
    lon = _first_float_from(
        municipality,
        (
            "lon",
            "lng",
            "longitude",
            "lon_decimal",
            "seat_lon_decimal",
            "municipal_seat_lon",
            "cabecera_lon",
        ),
    )

    if lat is not None and lon is not None:
        return lat, lon, "municipalities.json"

    try:
        neighborhoods = repo.get_neighborhoods_for(municipality_id)
    except Exception as exc:
        logger.debug("Could not read neighborhoods for %s: %s", municipality_id, exc)
        neighborhoods = []

    for item in neighborhoods:
        lat = _first_float_from(
            item,
            (
                "seat_lat_decimal",
                "lat",
                "latitude",
                "lat_decimal",
                "municipal_seat_lat",
                "cabecera_lat",
            ),
        )
        lon = _first_float_from(
            item,
            (
                "seat_lon_decimal",
                "lon",
                "lng",
                "longitude",
                "lon_decimal",
                "municipal_seat_lon",
                "cabecera_lon",
            ),
        )

        if lat is not None and lon is not None:
            return lat, lon, "neighborhoods.json"

    return None, None, None


def _resolve_denue_radius_m(category: str) -> int:
    """
    Pick a useful DENUE fallback radius.

    DENUE caps radius at 5,000m in the current client.
    """
    normalized = (category or "").casefold()

    if "ciudad" in normalized or "urbano" in normalized:
        return 3000

    if "semi" in normalized:
        return 4000

    return 5000


# ─────────────────────────────────────────────────────────────────────────────
# DENUE area codes
# ─────────────────────────────────────────────────────────────────────────────

def _first_text_from(
    payload: dict[str, Any] | None,
    keys: tuple[str, ...],
) -> str | None:
    if not isinstance(payload, dict):
        return None

    for key in keys:
        value = _as_text(payload.get(key))

        if value:
            return value

    return None


def _normalize_entity_code(value: Any) -> str | None:
    raw = _as_text(value)

    if not raw:
        return None

    if raw.isdigit():
        return f"{int(raw):02d}"

    return raw.zfill(2)


def _normalize_municipality_code(value: Any) -> str | None:
    raw = _as_text(value)

    if not raw:
        return None

    if raw.isdigit() and len(raw) == 5:
        raw = raw[-3:]

    if raw.isdigit():
        return f"{int(raw):03d}"

    return raw.zfill(3)


def _split_cvegeo(value: Any) -> tuple[str | None, str | None]:
    raw = _as_text(value)

    if not raw:
        return None, None

    digits = "".join(char for char in raw if char.isdigit())

    if len(digits) >= 5:
        return digits[:2], digits[2:5]

    return None, None


def _resolve_denue_area_codes(
    repo: TerritoryRepository,
    municipality_id: str,
    municipality: dict[str, Any] | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Resolve DENUE BuscarAreaAct codes.

    Returns:
        (entity_code, municipality_code, source_label)

    Priority:
        1. Explicit cve_ent / cve_mun in municipalities.json.
        2. CVEGEO-like field in municipalities.json.
        3. Explicit fields in neighborhoods/reference zones.
        4. CVEGEO-like field in neighborhoods/reference zones.
    """
    entity = _first_text_from(
        municipality,
        (
            "cve_ent",
            "entity_code",
            "state_code",
            "entidad",
            "entidad_federativa",
            "CVE_ENT",
        ),
    )
    mun = _first_text_from(
        municipality,
        (
            "cve_mun",
            "municipality_code",
            "municipio_code",
            "clave_municipio",
            "CVE_MUN",
        ),
    )

    if entity and mun:
        return (
            _normalize_entity_code(entity),
            _normalize_municipality_code(mun),
            "municipalities.json:cve_ent/cve_mun",
        )

    cvegeo = _first_text_from(
        municipality,
        (
            "municipality_cvegeo",
            "cvegeo",
            "CVEGEO",
            "Cvegeo",
            "cve_municipio",
            "cvegeo_municipal",
        ),
    )
    entity_from_cvegeo, mun_from_cvegeo = _split_cvegeo(cvegeo)

    if entity_from_cvegeo and mun_from_cvegeo:
        return (
            _normalize_entity_code(entity_from_cvegeo),
            _normalize_municipality_code(mun_from_cvegeo),
            "municipalities.json:cvegeo",
        )

    try:
        neighborhoods = repo.get_neighborhoods_for(municipality_id)
    except Exception as exc:
        logger.debug("Could not read neighborhoods for area codes %s: %s", municipality_id, exc)
        neighborhoods = []

    for item in neighborhoods:
        entity = _first_text_from(
            item,
            (
                "cve_ent",
                "entity_code",
                "state_code",
                "entidad",
                "entidad_federativa",
                "CVE_ENT",
            ),
        )
        mun = _first_text_from(
            item,
            (
                "cve_mun",
                "municipality_code",
                "municipio_code",
                "clave_municipio",
                "CVE_MUN",
            ),
        )

        if entity and mun:
            return (
                _normalize_entity_code(entity),
                _normalize_municipality_code(mun),
                "neighborhoods.json:cve_ent/cve_mun",
            )

        cvegeo = _first_text_from(
            item,
            (
                "municipality_cvegeo",
                "cvegeo",
                "CVEGEO",
                "Cvegeo",
                "cve_municipio",
                "cvegeo_municipal",
            ),
        )
        entity_from_cvegeo, mun_from_cvegeo = _split_cvegeo(cvegeo)

        if entity_from_cvegeo and mun_from_cvegeo:
            return (
                _normalize_entity_code(entity_from_cvegeo),
                _normalize_municipality_code(mun_from_cvegeo),
                "neighborhoods.json:cvegeo",
            )

    return None, None, None


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceOrchestrator:
    async def resolve(
        self,
        municipality_id: str,
        db: AsyncSession,
        force_refresh: bool = False,
    ) -> EvidenceRecordDB:
        """
        Resolve evidence for municipality_id.

        Hits DB cache first; rebuilds if stale or force_refresh.
        Enriches reference evidence with API/DENUE data when available.
        """
        repo = TerritoryRepository.get_instance()

        if not repo.exists(municipality_id):
            raise TerritoryNotFoundError("Municipio", municipality_id)

        current_snapshot = _snapshot_version()
        ev_repo = EvidenceRepository(db)

        if not force_refresh:
            cached = await ev_repo.get_latest(municipality_id)

            if cached and await ev_repo.is_fresh(cached, current_snapshot):
                logger.debug("Evidence cache hit: %s", municipality_id)
                return cached

        # ------------------------------------------------------------------
        # Base reference evidence
        # ------------------------------------------------------------------
        municipality = repo.get_municipality(municipality_id)

        name = municipality.get("name", municipality_id) if municipality else municipality_id
        pop = (
            municipality.get("population_approx")
            or municipality.get("population_2020")
            or municipality.get("population")
            or 15_000
        ) if municipality else 15_000
        region = municipality.get("region", "Valle Central") if municipality else "Valle Central"
        category = municipality.get("category", "municipio_rural") if municipality else "municipio_rural"

        pack = get_reference_pack(municipality_id, name, pop, region, category)

        # ------------------------------------------------------------------
        # Optional legacy Banxico FX enrichment already present in the project
        # ------------------------------------------------------------------
        try:
            fx = await banxico.banxico_client.fetch_exchange_rate()

            if fx and pack.economic:
                pack.economic.exchange_rate_usd_mxn.value = fx

        except Exception as exc:
            logger.debug("Banxico FX skipped: %s", exc)

        quality = _compute_quality(pack)

        social_data = self._layer_to_dict(pack.social)
        economic_data = self._layer_to_dict(pack.economic)
        infrastructure_data = self._layer_to_dict(pack.infrastructure)

        sources_used = list(pack.sources_used)
        sources_failed: list[str] = []
        geographic_fallbacks = (
            list(pack.geographic_fallbacks)
            if pack.geographic_fallbacks
            else []
        )

        # ------------------------------------------------------------------
        # DENUE coordinates and area codes
        # ------------------------------------------------------------------
        lat, lon, coordinate_source = _resolve_coordinates(
            repo=repo,
            municipality_id=municipality_id,
            municipality=municipality,
        )

        if coordinate_source:
            geographic_fallbacks.append(
                f"Coordenadas para DENUE resueltas desde {coordinate_source}"
            )
        else:
            geographic_fallbacks.append(
                "Coordenadas DENUE no resueltas; fallback por radio no disponible"
            )

        entity_code, municipality_code, area_code_source = _resolve_denue_area_codes(
            repo=repo,
            municipality_id=municipality_id,
            municipality=municipality,
        )

        if entity_code and municipality_code:
            geographic_fallbacks.append(
                f"Claves DENUE resueltas desde {area_code_source}: entidad={entity_code}, municipio={municipality_code}"
            )
        else:
            geographic_fallbacks.append(
                "Claves DENUE entity_code/municipality_code no resueltas; BuscarAreaAct no disponible"
            )

        logger.info(
            "DENUE resolution for %s | lat=%s lon=%s coordinate_source=%s entity_code=%s municipality_code=%s area_code_source=%s",
            municipality_id,
            lat,
            lon,
            coordinate_source,
            entity_code,
            municipality_code,
            area_code_source,
        )

        # ------------------------------------------------------------------
        # API enrichment: INEGI DENUE + Banxico reference series
        # ------------------------------------------------------------------
        try:
            denue_radius_m = _resolve_denue_radius_m(category)

            api_builder = EvidenceApiBuilder()

            api_snapshot = await api_builder.build_api_snapshot(
                municipality_id=municipality_id,
                municipality_name=name,
                lat=lat,
                lon=lon,
                entity_code=entity_code,
                municipality_code=municipality_code,
                denue_radius_m=denue_radius_m,
                denue_page_size=500,
                denue_max_records=5000,
            )

            if _has_meaningful_api_data(api_snapshot):
                economic_data = _merge_dicts(
                    economic_data,
                    api_snapshot.get("economic_data"),
                )
                infrastructure_data = _merge_dicts(
                    infrastructure_data,
                    api_snapshot.get("infrastructure_data"),
                )

                api_sources_used = api_snapshot.get("sources_used") or []
                api_sources_failed = api_snapshot.get("sources_failed") or []
                api_fallbacks = api_snapshot.get("geographic_fallbacks") or []

                sources_used = _dedupe_list([*sources_used, *api_sources_used])
                sources_failed = _dedupe_list([*sources_failed, *api_sources_failed])
                geographic_fallbacks = _dedupe_list(
                    [*geographic_fallbacks, *api_fallbacks]
                )

                quality = self._upgrade_quality_with_api(quality)

                logger.info(
                    "API evidence merged for %s: economic_keys=%s infrastructure_keys=%s",
                    municipality_id,
                    list((api_snapshot.get("economic_data") or {}).keys()),
                    list((api_snapshot.get("infrastructure_data") or {}).keys()),
                )
            else:
                api_sources_failed = api_snapshot.get("sources_failed") or []
                api_fallbacks = api_snapshot.get("geographic_fallbacks") or []

                sources_failed = _dedupe_list([*sources_failed, *api_sources_failed])
                geographic_fallbacks = _dedupe_list(
                    [*geographic_fallbacks, *api_fallbacks]
                )

                logger.info(
                    "API evidence empty for %s; using reference evidence only. failed=%s",
                    municipality_id,
                    sources_failed,
                )

        except Exception as exc:
            logger.warning(
                "API evidence enrichment skipped for %s: %s",
                municipality_id,
                exc,
            )
            sources_failed.append(f"API enrichment: {exc}")

        logger.info("FINAL economic_data keys for %s: %s", municipality_id, list(economic_data.keys()))
        logger.info("FINAL infrastructure_data keys for %s: %s", municipality_id, list(infrastructure_data.keys()))
        logger.info("FINAL sources_used for %s: %s", municipality_id, sources_used)
        logger.info("FINAL sources_failed for %s: %s", municipality_id, sources_failed)
        logger.info("FINAL geographic_fallbacks for %s: %s", municipality_id, geographic_fallbacks)

        # ------------------------------------------------------------------
        # Persist evidence record
        # ------------------------------------------------------------------
        record = EvidenceRecordDB(
            id=str(uuid.uuid4()),
            municipality_id=municipality_id,
            municipality_name=name,
            snapshot_version=current_snapshot,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.EVIDENCE_CACHE_TTL_DAYS),
            collection_method=(
                "reference_plus_api"
                if any("API" in str(src) for src in sources_used)
                else pack.data_quality
            ),
            overall_confidence=quality["overall_confidence"],
            municipal_coverage_pct=quality["municipal_coverage_pct"],
            state_coverage_pct=quality["state_coverage_pct"],
            estimated_coverage_pct=quality["estimated_coverage_pct"],
            can_cite_as_municipal=quality["can_cite_as_municipal"],
            quality_label=quality["quality_label"],
            methodology_disclaimer=quality["methodology_disclaimer"],
            social_data=social_data,
            economic_data=economic_data,
            infrastructure_data=infrastructure_data,
            sources_used=_dedupe_list(sources_used),
            sources_failed=_dedupe_list(sources_failed),
            geographic_fallbacks=_dedupe_list(geographic_fallbacks),
        )

        await ev_repo.save(record)

        logger.info(
            "Evidence resolved: %s (confidence=%.2f, quality=%s, sources=%s, failed=%s)",
            municipality_id,
            quality["overall_confidence"],
            quality["quality_label"],
            record.sources_used,
            record.sources_failed,
        )

        return record

    async def get_latest(
        self,
        municipality_id: str,
        db: AsyncSession,
    ) -> Optional[EvidenceRecordDB]:
        ev_repo = EvidenceRepository(db)
        return await ev_repo.get_latest(municipality_id)

    def _upgrade_quality_with_api(self, quality: dict[str, Any]) -> dict[str, Any]:
        """
        Slightly upgrade quality metadata when local API data is successfully merged.

        This does not pretend that all indicators became municipal; it only reflects
        that the evidence now contains local API enrichment.
        """
        upgraded = dict(quality)

        current_confidence = _as_float(upgraded.get("overall_confidence")) or 0.0
        upgraded["overall_confidence"] = round(max(current_confidence, 0.80), 2)

        current_municipal = _as_float(upgraded.get("municipal_coverage_pct")) or 0.0
        upgraded["municipal_coverage_pct"] = round(max(current_municipal, 70.0), 1)

        upgraded["can_cite_as_municipal"] = True
        upgraded["quality_label"] = "Alta — datos locales con enriquecimiento API"

        if not upgraded.get("methodology_disclaimer"):
            upgraded["methodology_disclaimer"] = (
                "La evidencia combina datos territoriales versionados con información "
                "complementaria consultada en APIs oficiales. Los conteos DENUE deben "
                "interpretarse como establecimientos registrados, no como capacidad efectiva "
                "de atención o cobertura del servicio."
            )

        return upgraded

    def _layer_to_dict(self, layer) -> dict[str, Any]:
        if layer is None:
            return {}

        result: dict[str, Any] = {}

        for key, val in layer.__dict__.items():
            if key.startswith("_"):
                continue

            if hasattr(val, "value"):
                result[key] = {
                    "value": getattr(val, "value", None),
                    "unit": getattr(val, "unit", ""),
                    "period": getattr(val, "period", ""),
                    "source": getattr(val, "source", ""),
                    "geographic_level": getattr(val, "geographic_level", ""),
                    "available": getattr(val, "available", False),
                    "limitation_note": getattr(val, "limitation_note", None),
                }
            elif isinstance(val, list):
                result[key] = val

        return result

    def to_prompt_text(self, record: EvidenceRecordDB) -> str:
        """
        Convert a persisted EvidenceRecord to the territorial context block
        that gets injected into LLM prompts. Quality-aware — never misrepresents estimates.
        """
        lines = ["=== CONTEXTO TERRITORIAL — TLAXCALA ==="]
        lines.append(f"Municipio: {record.municipality_name}")

        if not record.can_cite_as_municipal:
            lines.append(
                f"\n[Calidad de datos: {record.quality_label}. "
                "Las cifras son estimaciones orientativas, no datos censales exactos.]"
            )

        def _fmt(
            key: str,
            layer: dict[str, Any],
            label: str,
            suffix: str = "",
        ) -> Optional[str]:
            dp = layer.get(key, {})
            val = dp.get("value")

            if val is None or not dp.get("available"):
                return None

            geo = dp.get("geographic_level", "")
            prefix = "~" if geo in ("estatal", "state", "regional") else ""

            note = ""
            if geo in ("regional", "estimated"):
                note = " (estimación regional)"
            elif geo in ("estatal", "state"):
                note = " (dato estatal)"

            return f"{label}: {prefix}{val:,.1f}{suffix}{note}"

        s = record.social_data or {}
        e = record.economic_data or {}
        i = record.infrastructure_data or {}

        poverty = s.get("poverty_rate_pct", {})
        pov_val = poverty.get("value")

        if pov_val is not None:
            pov_geo = poverty.get("geographic_level", "")
            prefix = "~" if pov_geo not in ("municipal",) else ""
            note = " (estimación regional calibrada)" if pov_geo == "regional" else ""

            lines.append(
                f"\nPobreza multidimensional: "
                f"{prefix}{pov_val:.1f}%{note} ({poverty.get('period', '')})"
            )

        for key, label, suffix in [
            ("social_security_lack_pct", "Sin seguridad social", "%"),
            ("health_access_lack_pct", "Sin acceso a salud", "%"),
            ("education_lag_pct", "Rezago educativo", "%"),
            ("food_insecurity_pct", "Inseguridad alimentaria", "%"),
        ]:
            line = _fmt(key, s, label, suffix)

            if line:
                lines.append(line)

        lines.append("")

        for key, label, suffix in [
            ("informal_employment_pct", "Empleo informal", "% de la PEA"),
            ("avg_income_mxn", "Ingreso promedio mensual", " MXN"),
            ("economic_units_total", "Unidades económicas activas", ""),
        ]:
            line = _fmt(key, e, label, suffix)

            if line:
                lines.append(line)

        api_units = e.get("business_units_total_api", {})
        api_units_value = api_units.get("value")

        if api_units_value is not None:
            lines.append(
                f"Unidades económicas observadas vía DENUE API: "
                f"{api_units_value:,.0f}"
            )

        sectors = e.get("main_sectors", [])

        if sectors:
            lines.append(f"Sectores dominantes: {', '.join(sectors[:4])}")

        api_sector_distribution = e.get("sector_distribution_api", {})
        api_sector_rows = api_sector_distribution.get("value")

        if isinstance(api_sector_rows, list) and api_sector_rows:
            top_api_sectors = [
                str(row.get("sector", "")).strip()
                for row in api_sector_rows[:4]
                if isinstance(row, dict) and str(row.get("sector", "")).strip()
            ]

            if top_api_sectors:
                lines.append(
                    "Sectores observados vía DENUE API: "
                    + ", ".join(top_api_sectors)
                )

        water = i.get("drinking_water_access_pct", {})
        internet = i.get("internet_access_pct", {})
        hospital = i.get("minutes_to_nearest_hospital", {})

        gaps = []

        if water.get("available") and water.get("value", 100) < 88:
            gaps.append(f"agua potable {water['value']:.0f}%")

        if internet.get("available") and internet.get("value", 100) < 55:
            gaps.append(f"internet {internet['value']:.0f}%")

        if hospital.get("available") and hospital.get("value", 0) > 25:
            gaps.append(f"hospital a {int(hospital['value'])} min")

        health_api = i.get("health_facilities_count_api", {})
        schools_api = i.get("schools_count_api", {})

        if health_api.get("value") is not None:
            lines.append(
                f"Establecimientos relacionados con salud observados en DENUE API: "
                f"{health_api.get('value'):,.0f}"
            )

        if schools_api.get("value") is not None:
            lines.append(
                f"Registros educativos observados en DENUE API: "
                f"{schools_api.get('value'):,.0f}"
            )

        if gaps:
            lines.append(f"\nBrechas de infraestructura: {'; '.join(gaps)}")

        return "\n".join(lines)

    def extract_pain_points(
        self,
        record: EvidenceRecordDB,
        diagnosis: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        if diagnosis:
            needs = diagnosis.get("critical_needs", [])

            if needs:
                return [
                    n.get("title", "")
                    for n in needs
                    if isinstance(n, dict) and n.get("title")
                ]

        s = record.social_data or {}
        pains: list[str] = []

        poverty_val = (s.get("poverty_rate_pct") or {}).get("value")

        if poverty_val and poverty_val >= 40:
            pains.append("Pobreza multidimensional severa")

        informal_val = (
            (record.economic_data or {}).get("informal_employment_pct") or {}
        ).get("value")

        if informal_val and informal_val >= 50:
            pains.append("Alta informalidad laboral sin acceso a seguridad social")

        health_val = (s.get("health_access_lack_pct") or {}).get("value")

        if health_val and health_val >= 25:
            pains.append("Carencia de acceso a servicios de salud")

        edu_val = (s.get("education_lag_pct") or {}).get("value")

        if edu_val and edu_val >= 20:
            pains.append("Rezago educativo significativo")

        water_val = (
            (record.infrastructure_data or {}).get("drinking_water_access_pct") or {}
        ).get("value")

        if water_val and water_val < 80:
            pains.append("Déficit de agua potable")

        return pains or [
            "Acceso limitado a servicios básicos",
            "Empleo informal predominante",
        ]


evidence_orchestrator = EvidenceOrchestrator()