
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SourceTextValidationError, TerritoryNotFoundError, ValidationBlockedError
from app.core.responses import APIResponse
from app.db.connection import get_db
from app.models.schemas import SpeechDetail, SpeechRunRequest, SpeechSummary
from app.services.speech.speech_orchestrator import speech_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


def _dq(run) -> dict:
    return {"overall_confidence": run.overall_confidence, "can_cite_as_municipal": False}


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


def _to_detail(run) -> SpeechDetail:
    return SpeechDetail(
        id=run.id,
        municipality_id=run.municipality_id,
        analysis_run_id=run.analysis_run_id,
        created_at=run.created_at,
        status=run.status,
        speech_type=run.speech_type,
        speech_data=run.speech_data or {},
        target_duration_minutes=run.target_duration_minutes,
        target_word_count=run.target_word_count,
        actual_word_count=run.actual_word_count,
        retry_count=run.retry_count,
        parameter_hash=getattr(run, "parameter_hash", ""),
        ai_generated=run.ai_generated,
        latency_ms=run.latency_ms,
        data_quality=_dq(run),
        validation=_val(run, full=True),
    )


def _to_summary(run) -> SpeechSummary:
    return SpeechSummary(
        id=run.id,
        municipality_id=run.municipality_id,
        analysis_run_id=run.analysis_run_id,
        created_at=run.created_at,
        status=run.status,
        speech_type=run.speech_type,
        target_duration_minutes=run.target_duration_minutes,
        target_word_count=run.target_word_count,
        actual_word_count=run.actual_word_count,
        retry_count=run.retry_count,
        parameter_hash=getattr(run, "parameter_hash", ""),
        data_quality=_dq(run),
        validation=_val(run, full=False),
    )


@router.post("/run", response_model=APIResponse[SpeechDetail],
             summary="Crear o mejorar discurso. Si hay source_text: mejora. Si no: crea.")
async def run_speech(req: SpeechRunRequest, db: AsyncSession = Depends(get_db)):
    try:
        run = await speech_orchestrator.run(req, db, force_refresh=req.force_refresh)
        mode = "Mejora" if req.source_text else "Creación"
        return APIResponse[SpeechDetail].ok(data=_to_detail(run), message=f"{mode} completada.")
    except (ValidationBlockedError, SourceTextValidationError) as exc:
        raise HTTPException(422, detail=exc.message)
    except TerritoryNotFoundError as exc:
        raise HTTPException(404, detail=exc.message)
    except Exception as exc:
        logger.exception("Speech failed for %s", req.municipality_id)
        raise HTTPException(500, detail=str(exc))


@router.get("/latest/{municipality_id}", response_model=APIResponse[SpeechSummary])
async def get_latest(municipality_id: str, db: AsyncSession = Depends(get_db)):
    run = await speech_orchestrator.get_latest(municipality_id, db)
    if not run:
        raise HTTPException(404, detail=f"Sin discurso para {municipality_id}.")
    return APIResponse[SpeechSummary].ok(data=_to_summary(run))