"""Analysis PDF builder — reads from AnalysisRunDB.
Uses the proven report_builder from the existing project."""
from io import BytesIO
from app.models.db_models import AnalysisRunDB, EvidenceRecordDB


class AnalysisPDFBuilder:

    def build(self, run: AnalysisRunDB, evidence: EvidenceRecordDB | None) -> bytes:
        """Build full analysis report PDF."""
        from app.services.export._analysis_renderer import render_analysis_pdf
        return render_analysis_pdf(run, evidence)


analysis_pdf_builder = AnalysisPDFBuilder()
