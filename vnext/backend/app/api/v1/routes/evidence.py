"""
Evidence routes.

POST /resolve/{municipality_id}  → APIResponse[EvidenceDetail]
GET  /latest/{municipality_id}   → APIResponse[EvidenceSummary]
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TerritoryNotFoundError
from app.core.responses import APIResponse
from app.db.connection import get_db
from app.models.schemas import EvidenceDetail, EvidenceResolveRequest, EvidenceSummary
from app.services.evidence.orchestrator import evidence_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_detail(record) -> EvidenceDetail:
    return EvidenceDetail(
        id=record.id,
        municipality_id=record.municipality_id,
        municipality_name=record.municipality_name,
        snapshot_version=record.snapshot_version,
        created_at=record.created_at,
        expires_at=record.expires_at,
        collection_method=record.collection_method,
        data_quality=dict(
            overall_confidence=record.overall_confidence,
            municipal_coverage_pct=record.municipal_coverage_pct,
            state_coverage_pct=record.state_coverage_pct,
            estimated_coverage_pct=record.estimated_coverage_pct,
            can_cite_as_municipal=record.can_cite_as_municipal,
            quality_label=record.quality_label,
            methodology_disclaimer=record.methodology_disclaimer,
        ),
        sources_used=record.sources_used or [],
        geographic_fallbacks=record.geographic_fallbacks or [],
    )


def _to_summary(record) -> EvidenceSummary:
    return EvidenceSummary(
        id=record.id,
        municipality_id=record.municipality_id,
        municipality_name=record.municipality_name,
        created_at=record.created_at,
        collection_method=record.collection_method,
        data_quality=dict(
            overall_confidence=record.overall_confidence,
            can_cite_as_municipal=record.can_cite_as_municipal,
            quality_label=record.quality_label,
        ),
    )


@router.post(
    "/resolve/{municipality_id}",
    response_model=APIResponse[EvidenceDetail],
    summary="Resolve evidence for a municipality. Returns EvidenceDetail.",
)
async def resolve_evidence(
    municipality_id: str,
    body: EvidenceResolveRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvidenceDetail]:
    try:
        record = await evidence_orchestrator.resolve(
            municipality_id, db, force_refresh=body.force_refresh
        )
        return APIResponse[EvidenceDetail].ok(
            data=_to_detail(record),
            message=f"Evidencia resuelta: {record.municipality_name}.",
            meta={
                "refreshed": body.force_refresh,
                "can_cite_as_municipal": record.can_cite_as_municipal,
            },
        )
    except TerritoryNotFoundError as exc:
        raise HTTPException(404, detail=exc.message)
    except Exception as exc:
        logger.exception("Error resolving evidence for %s", municipality_id)
        raise HTTPException(500, detail=str(exc))


@router.get(
    "/latest/{municipality_id}",
    response_model=APIResponse[EvidenceSummary],
    summary="Get latest evidence summary for a municipality.",
)
async def get_latest_evidence(
    municipality_id: str,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvidenceSummary]:
    record = await evidence_orchestrator.get_latest(municipality_id, db)
    if not record:
        raise HTTPException(
            404,
            detail=(
                f"Sin evidencia para {municipality_id}. "
                f"Llama a POST /evidence/resolve/{municipality_id} primero."
            ),
        )
    return APIResponse[EvidenceSummary].ok(data=_to_summary(record))
