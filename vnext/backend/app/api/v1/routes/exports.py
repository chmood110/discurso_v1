"""Export routes v2.0 — analysis + speech PDFs only."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.services.export.pdf_pipeline import export_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pdf/analysis/{run_id}", summary="Download analysis PDF.", response_class=Response)
async def export_analysis_pdf(run_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    try:
        pdf = await export_pipeline.export_analysis(run_id, db)
        return Response(
            content=pdf, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="analisis-{run_id[:8]}.pdf"'},
        )
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))
    except Exception as exc:
        logger.exception("PDF export failed for analysis %s", run_id)
        raise HTTPException(500, detail=str(exc))


@router.get("/pdf/speech/{run_id}", summary="Download speech PDF.", response_class=Response)
async def export_speech_pdf(run_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    try:
        pdf = await export_pipeline.export_speech(run_id, db)
        return Response(
            content=pdf, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="discurso-{run_id[:8]}.pdf"'},
        )
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(500, detail=str(exc))