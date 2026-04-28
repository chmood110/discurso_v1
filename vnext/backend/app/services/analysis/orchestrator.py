"""
AnalysisOrchestrator v2.0 — pipeline completo:
  1. Evidence (datos reales INEGI/CONEVAL)
  2. DiagnosisGenerator (análisis algorítmico, sin LLM)
  3. KPIGenerator (KPIs SMART, sin LLM)
  4. AnalysisStrategist (estrategia política, 1 llamada LLM)
  5. ValidationPipeline
  6. Persistencia
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.analysis_repo import AnalysisRepository
from app.models.db_models import AnalysisRunDB, EvidenceRecordDB
from app.services.analysis.diagnosis import DiagnosisGenerator
from app.services.analysis.kpis import KPIGenerator
from app.services.analysis.strategist import generate_strategy
from app.services.evidence.orchestrator import evidence_orchestrator
from app.services.territory.repository import TerritoryRepository
from app.services.validation.pipeline import output_validator

logger = logging.getLogger(__name__)

_diagnosis_gen = DiagnosisGenerator()
_kpi_gen = KPIGenerator()


class AnalysisOrchestrator:
    async def run(
        self,
        municipality_id: str,
        db: AsyncSession,
        objective: Optional[str] = None,
        force_refresh: bool = False,
    ) -> AnalysisRunDB:
        analysis_repo = AnalysisRepository(db)

        if not force_refresh:
            cached = await analysis_repo.get_latest_valid(municipality_id)
            if cached:
                logger.debug("Analysis cache hit: %s", municipality_id)
                return cached

        evidence = await evidence_orchestrator.resolve(
            municipality_id, db, force_refresh=force_refresh
        )
        pack = self._record_to_pack(evidence)

        report = _diagnosis_gen.generate(pack)
        kpi_board = _kpi_gen.generate(pack)

        def _serialize(obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_serialize(i) for i in obj]
            if hasattr(obj, "__dict__"):
                return {
                    k: _serialize(v)
                    for k, v in obj.__dict__.items()
                    if not k.startswith("_")
                }
            return obj

        report_dict = _serialize(report)
        kpi_dict = _serialize(kpi_board)

        territory_repo = TerritoryRepository.get_instance()
        municipality = territory_repo.get_municipality(municipality_id) or {}
        profile = territory_repo.get_profile(municipality_id) or {}

        strategy_section = await generate_strategy(
            municipality_name=pack.municipality_name,
            region=municipality.get("region", "Tlaxcala"),
            category=municipality.get("category", "municipio_general"),
            diagnosis_summary=report_dict.get("executive_summary", ""),
            critical_needs=report_dict.get("critical_needs", []),
            opportunities=report_dict.get("opportunities", []),
            kpi_board=kpi_dict,
            territorial_profile=profile,
        )

        validation = output_validator.validate_analysis(report_dict, kpi_dict)

        run = AnalysisRunDB(
            id=str(uuid.uuid4()),
            municipality_id=municipality_id,
            evidence_record_id=evidence.id,
            created_at=datetime.now(timezone.utc),
            objective=objective,
            status="completed",
            executive_summary=report_dict.get("executive_summary", ""),
            demographic_profile=report_dict.get("demographic_profile", {}),
            economic_engine=report_dict.get("economic_engine", {}),
            infrastructure_gaps=report_dict.get("infrastructure", {}),
            critical_needs=report_dict.get("critical_needs", []),
            opportunities=report_dict.get("opportunities", []),
            kpi_board=kpi_dict,
            speeches={},  # compatibilidad con la SQLite actual
            strategy_section=strategy_section,
            overall_confidence=evidence.overall_confidence,
            can_cite_as_municipal=evidence.can_cite_as_municipal,
            validation_passed=validation.passed,
            validation_score=validation.score,
            validation_issues=[i.__dict__ for i in validation.issues],
        )

        saved = await analysis_repo.save(run)
        logger.info(
            "Analysis saved: %s id=%s confidence=%.2f strategy_ai=%s",
            municipality_id,
            saved.id,
            evidence.overall_confidence,
            strategy_section.get("ai_generated", False),
        )
        return saved

    async def get_latest(self, municipality_id: str, db: AsyncSession) -> Optional[AnalysisRunDB]:
        return await AnalysisRepository(db).get_latest_valid(municipality_id)

    async def get_by_id(self, run_id: str, db: AsyncSession) -> Optional[AnalysisRunDB]:
        return await AnalysisRepository(db).get_by_id(run_id)

    async def history(
        self, municipality_id: str, db: AsyncSession, limit: int = 20
    ) -> list[AnalysisRunDB]:
        return await AnalysisRepository(db).history(municipality_id, limit)

    def _record_to_pack(self, evidence: EvidenceRecordDB):
        from types import SimpleNamespace

        def _ns(layer_dict: dict):
            ns = SimpleNamespace()
            for key, dp in layer_dict.items():
                if isinstance(dp, dict):
                    val = dp.get("value")
                    unit = dp.get("unit", "")
                    available = dp.get("available", val is not None)
                    limitation_note = dp.get("limitation_note")

                    def _make_display(v, u, a, ln):
                        def display():
                            if not a:
                                return f"No disponible ({ln or 'sin datos'})"
                            formatted = f"{v:,.1f}" if v is not None else "N/D"
                            return f"{formatted} {u}".strip()
                        return display

                    p = SimpleNamespace(
                        value=val,
                        unit=unit,
                        source=dp.get("source", ""),
                        period=dp.get("period", ""),
                        geographic_level=dp.get("geographic_level", "municipal"),
                        available=available,
                        limitation_note=limitation_note,
                    )
                    p.display = _make_display(val, unit, available, limitation_note)
                    setattr(ns, key, p)
                elif isinstance(dp, list):
                    setattr(ns, key, dp)
            return ns

        return SimpleNamespace(
            municipality_id=evidence.municipality_id,
            municipality_name=evidence.municipality_name,
            data_quality=evidence.collection_method,
            sources_used=evidence.sources_used,
            geographic_fallbacks=evidence.geographic_fallbacks,
            social=_ns(evidence.social_data),
            economic=_ns(evidence.economic_data),
            infrastructure=_ns(evidence.infrastructure_data),
        )


analysis_orchestrator = AnalysisOrchestrator()