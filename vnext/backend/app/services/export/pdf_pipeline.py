"""PDF export pipeline v2.0 — analysis + speech only."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.evidence_repo import EvidenceRepository
from app.db.repositories.speech_repo import SpeechRepository

from app.services.export._analysis_renderer import render_analysis_pdf
from app.services.export.pdf_speech import speech_pdf_builder


class ExportPipeline:
    """Small export service for analysis and speech PDFs only."""

    async def export_analysis(self, run_id: str, db: AsyncSession) -> bytes:
        analysis_repo = AnalysisRepository(db)
        evidence_repo = EvidenceRepository(db)

        run = await analysis_repo.get_by_id(run_id)
        if not run:
            raise ValueError("Analysis run not found")

        evidence = await evidence_repo.get_by_id(run.evidence_record_id)
        return render_analysis_pdf(run, evidence)

    async def export_speech(self, run_id: str, db: AsyncSession) -> bytes:
        speech_repo = SpeechRepository(db)
        analysis_repo = AnalysisRepository(db)
        evidence_repo = EvidenceRepository(db)

        run = await speech_repo.get_by_id(run_id)
        if not run:
            raise ValueError("Speech run not found")

        evidence = None
        if run.analysis_run_id:
            analysis_run = await analysis_repo.get_by_id(run.analysis_run_id)
            if analysis_run:
                evidence = await evidence_repo.get_by_id(analysis_run.evidence_record_id)

        return speech_pdf_builder.build(run, evidence)


export_pipeline = ExportPipeline()