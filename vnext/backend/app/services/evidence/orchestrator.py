"""
EvidenceOrchestrator — single source of truth for evidence resolution.

Resolution order:
  1. DB cache (fresh + matching snapshot_version)
  2. Reference data (region/category-calibrated or municipal real data)
  3. Live API enrichment (Banxico if configured)

Never throws — always returns a record with explicit quality signals.
"""
from __future__ import annotations
import hashlib, inspect, logging, uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import TerritoryNotFoundError
from app.db.repositories.evidence_repo import EvidenceRepository
from app.models.db_models import EvidenceRecordDB
from app.models.enums import DataQualityLevel
from app.services.evidence.reference_data import get_reference_pack
from app.services.integrations import banxico_client as banxico
from app.services.territory.repository import TerritoryRepository

logger = logging.getLogger(__name__)


def _snapshot_version() -> str:
    """Hash of reference_data.py source — changes force cache invalidation."""
    try:
        import app.services.evidence.reference_data as rd
        src = inspect.getsource(rd)
        repo_version = TerritoryRepository.get_instance().get_schema_version()
        combined = src + repo_version
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


def _compute_quality(pack) -> dict:
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
        "official_municipal": 0, "official_state": 0,
        "calibrated_estimate": 0, "unavailable": 0,
    }
    for p in points:
        if not p.available or getattr(p, "value", None) is None:
            counts["unavailable"] += 1
        else:
            level = getattr(p, "geographic_level", "municipal") or "municipal"
            if level == "municipal":
                counts["official_municipal"] += 1
            elif level in ("estatal", "state", "nacional", "national"):
                counts["official_state"] += 1
            elif level in ("regional", "estimated"):
                counts["calibrated_estimate"] += 1
            else:
                counts["official_municipal"] += 1

    mun_pct  = counts["official_municipal"] / n * 100
    stat_pct = counts["official_state"] / n * 100
    est_pct  = counts["calibrated_estimate"] / n * 100
    una_pct  = counts["unavailable"] / n * 100

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


def _unavailable_quality() -> dict:
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

        # Assemble fresh
        mun = repo.get_municipality(municipality_id)
        name     = mun["name"] if mun else municipality_id
        pop      = mun.get("population_approx", 15_000) if mun else 15_000
        region   = mun.get("region", "Valle Central") if mun else "Valle Central"
        category = mun.get("category", "municipio_rural") if mun else "municipio_rural"

        pack = get_reference_pack(municipality_id, name, pop, region, category)

        # Live Banxico enrichment (optional)
        try:
            fx = await banxico.banxico_client.fetch_exchange_rate()
            if fx and pack.economic:
                pack.economic.exchange_rate_usd_mxn.value = fx
        except Exception as exc:
            logger.debug("Banxico FX skipped: %s", exc)

        quality = _compute_quality(pack)

        record = EvidenceRecordDB(
            id=str(uuid.uuid4()),
            municipality_id=municipality_id,
            municipality_name=name,
            snapshot_version=current_snapshot,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.EVIDENCE_CACHE_TTL_DAYS),
            collection_method=pack.data_quality,
            overall_confidence=quality["overall_confidence"],
            municipal_coverage_pct=quality["municipal_coverage_pct"],
            state_coverage_pct=quality["state_coverage_pct"],
            estimated_coverage_pct=quality["estimated_coverage_pct"],
            can_cite_as_municipal=quality["can_cite_as_municipal"],
            quality_label=quality["quality_label"],
            methodology_disclaimer=quality["methodology_disclaimer"],
            social_data=self._layer_to_dict(pack.social),
            economic_data=self._layer_to_dict(pack.economic),
            infrastructure_data=self._layer_to_dict(pack.infrastructure),
            sources_used=list(pack.sources_used),
            sources_failed=[],
            geographic_fallbacks=list(pack.geographic_fallbacks) if pack.geographic_fallbacks else [],
        )

        await ev_repo.save(record)
        logger.info("Evidence resolved: %s (confidence=%.2f, quality=%s)",
                    municipality_id, quality["overall_confidence"], quality["quality_label"])
        return record

    async def get_latest(self, municipality_id: str, db: AsyncSession) -> Optional[EvidenceRecordDB]:
        ev_repo = EvidenceRepository(db)
        return await ev_repo.get_latest(municipality_id)

    def _layer_to_dict(self, layer) -> dict:
        if layer is None:
            return {}
        result = {}
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

        def _fmt(key: str, layer: dict, label: str, suffix: str = "") -> Optional[str]:
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

        s = record.social_data
        e = record.economic_data
        i = record.infrastructure_data

        poverty = s.get("poverty_rate_pct", {})
        pov_val = poverty.get("value")
        if pov_val is not None:
            pov_geo = poverty.get("geographic_level", "")
            prefix = "~" if pov_geo not in ("municipal",) else ""
            note = " (estimación regional calibrada)" if pov_geo == "regional" else ""
            lines.append(f"\nPobreza multidimensional: {prefix}{pov_val:.1f}%{note} ({poverty.get('period','')})")

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

        sectors = e.get("main_sectors", [])
        if sectors:
            lines.append(f"Sectores dominantes: {', '.join(sectors[:4])}")

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
        if gaps:
            lines.append(f"\nBrechas de infraestructura: {'; '.join(gaps)}")

        return "\n".join(lines)

    def extract_pain_points(self, record: EvidenceRecordDB, diagnosis: Optional[dict] = None) -> list[str]:
        if diagnosis:
            needs = diagnosis.get("critical_needs", [])
            if needs:
                return [n.get("title", "") for n in needs if isinstance(n, dict) and n.get("title")]
        s = record.social_data
        pains = []
        poverty_val = (s.get("poverty_rate_pct") or {}).get("value")
        if poverty_val and poverty_val >= 40:
            pains.append("Pobreza multidimensional severa")
        informal_val = (record.economic_data.get("informal_employment_pct") or {}).get("value")
        if informal_val and informal_val >= 50:
            pains.append("Alta informalidad laboral sin acceso a seguridad social")
        health_val = (s.get("health_access_lack_pct") or {}).get("value")
        if health_val and health_val >= 25:
            pains.append("Carencia de acceso a servicios de salud")
        edu_val = (s.get("education_lag_pct") or {}).get("value")
        if edu_val and edu_val >= 20:
            pains.append("Rezago educativo significativo")
        water_val = (record.infrastructure_data.get("drinking_water_access_pct") or {}).get("value")
        if water_val and water_val < 80:
            pains.append("Déficit de agua potable")
        return pains or ["Acceso limitado a servicios básicos", "Empleo informal predominante"]


evidence_orchestrator = EvidenceOrchestrator()
