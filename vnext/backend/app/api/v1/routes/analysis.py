"""Analysis routes v2.0 — expone strategy_section integrado."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TerritoryNotFoundError
from app.core.responses import APIResponse
from app.db.connection import get_db
from app.models.schemas import AnalysisDetail, AnalysisRunRequest, AnalysisSummary, StrategySection, MessagingAxis
from app.services.analysis.orchestrator import analysis_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


def _dq(run) -> dict:
    return {"overall_confidence": run.overall_confidence, "can_cite_as_municipal": run.can_cite_as_municipal}


def _val(run, full=True) -> dict:
    issues = run.validation_issues or []
    return {
        "passed": run.validation_passed,
        "score": run.validation_score,
        "checks_run": len(issues),
        "checks_failed": sum(1 for i in issues if i.get("severity") == "blocking"),
        "blocking_count": sum(1 for i in issues if i.get("severity") == "blocking"),
        "warning_count": sum(1 for i in issues if i.get("severity") == "warning"),
        "rule_version": getattr(run, "validation_rule_version", "2.0.0"),
        "issues": issues if full else [],
    }


def _parse_strategy(raw: dict | None) -> StrategySection:
    if not raw:
        return StrategySection()
    axes_raw = raw.get("messaging_axes", []) or []
    axes = []
    for a in axes_raw:
        if isinstance(a, dict):
            axes.append(MessagingAxis(
                axis=a.get("axis", ""),
                message=a.get("message", ""),
                rationale=a.get("rationale", ""),
                emotional_hook=a.get("emotional_hook", ""),
                data_anchor=a.get("data_anchor", ""),
            ))
    return StrategySection(
        executive_strategic=raw.get("executive_strategic", ""),
        messaging_axes=axes,
        pain_points_ranked=raw.get("pain_points_ranked", []),
        opportunities_ranked=raw.get("opportunities_ranked", []),
        candidate_positioning=raw.get("candidate_positioning", ""),
        recommended_tone=raw.get("recommended_tone", ""),
        risk_flags=raw.get("risk_flags", []),
        framing_suggestions=raw.get("framing_suggestions", []),
        communication_channels_priority=raw.get("communication_channels_priority", []),
        ai_generated=raw.get("ai_generated", False),
        latency_ms=raw.get("latency_ms"),
    )


def _to_detail(run) -> AnalysisDetail:
    return AnalysisDetail(
        id=run.id,
        municipality_id=run.municipality_id,
        evidence_record_id=run.evidence_record_id,
        created_at=run.created_at,
        status=run.status,
        objective=run.objective,
        executive_summary=run.executive_summary or "",
        demographic_profile=run.demographic_profile or {},
        economic_engine=run.economic_engine or {},
        infrastructure_gaps=run.infrastructure_gaps or {},
        critical_needs=run.critical_needs or [],
        opportunities=run.opportunities or [],
        kpi_board=run.kpi_board or {},
        strategy_section=_parse_strategy(run.strategy_section),
        data_quality=_dq(run),
        validation=_val(run, full=True),
    )


def _to_summary(run) -> AnalysisSummary:
    return AnalysisSummary(
        id=run.id,
        municipality_id=run.municipality_id,
        evidence_record_id=run.evidence_record_id,
        created_at=run.created_at,
        status=run.status,
        objective=run.objective,
        executive_summary=run.executive_summary or "",
        data_quality=_dq(run),
        validation=_val(run, full=False),
    )


@router.post("/run", response_model=APIResponse[AnalysisDetail],
             summary="Generate or retrieve cached analysis.")
async def run_analysis(req: AnalysisRunRequest, db: AsyncSession = Depends(get_db)):
    try:
        run = await analysis_orchestrator.run(
            req.municipality_id, db, objective=req.objective, force_refresh=req.force_refresh
        )
        return APIResponse[AnalysisDetail].ok(data=_to_detail(run), message="Análisis listo.")
    except TerritoryNotFoundError as exc:
        raise HTTPException(404, detail=exc.message)
    except Exception as exc:
        logger.exception("Analysis failed for %s", req.municipality_id)
        raise HTTPException(500, detail=str(exc))


@router.get("/latest/{municipality_id}", response_model=APIResponse[AnalysisSummary])
async def get_latest(municipality_id: str, db: AsyncSession = Depends(get_db)):
    run = await analysis_orchestrator.get_latest(municipality_id, db)
    if not run:
        raise HTTPException(404, detail=f"Sin análisis para {municipality_id}. Llama a POST /analysis/run.")
    return APIResponse[AnalysisSummary].ok(data=_to_summary(run))


@router.get("/history/{municipality_id}", response_model=APIResponse[list[AnalysisSummary]])
async def get_history(municipality_id: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    runs = await analysis_orchestrator.history(municipality_id, db, limit=limit)
    return APIResponse[list[AnalysisSummary]].ok(data=[_to_summary(r) for r in runs])