"""
Regression test suite — specific guards against historically confirmed bugs.

Each test is named after the bug it prevents from returning.
"""
import pytest
import inspect


class TestRegressionForceRefreshBodyOnly:
    """
    REGRESSION: force_refresh was previously received as query param in evidence.
    Frontend sends it in JSON body — must be read from body only.
    """

    def test_evidence_resolve_has_body_parameter(self):
        from app.api.v1.routes.evidence import resolve_evidence
        src = inspect.getsource(resolve_evidence)
        assert "body: EvidenceResolveRequest" in src, (
            "REGRESSION: force_refresh must come from body (EvidenceResolveRequest), not query param."
        )
        assert "force_refresh: bool = False" not in src.split("def resolve_evidence")[1].split(")")[0], (
            "REGRESSION: force_refresh must not be a standalone query parameter."
        )

    def test_evidence_resolve_uses_body_force_refresh(self):
        from app.api.v1.routes.evidence import resolve_evidence
        src = inspect.getsource(resolve_evidence)
        assert "body.force_refresh" in src, (
            "REGRESSION: route must pass body.force_refresh to orchestrator."
        )

    @pytest.mark.asyncio
    async def test_force_refresh_false_in_body_caches(self, client):
        r1 = (await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})).json()["data"]
        r2 = (await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})).json()["data"]
        assert r1["id"] == r2["id"]

    @pytest.mark.asyncio
    async def test_force_refresh_true_in_body_refreshes(self, client):
        r1 = (await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})).json()["data"]
        r2 = (await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": True})).json()["data"]
        assert r1["id"] != r2["id"]


class TestRegressionBatchSharedSession:
    """
    REGRESSION: batch tasks originally shared the HTTP request db session,
    causing DetachedInstanceError when the response returned.
    """

    def test_batch_execute_analysis_no_db_param(self):
        from app.services.batch.processor import BatchProcessor
        src = inspect.getsource(BatchProcessor._execute_analysis)
        first_line = src.strip().split('\n')[0]
        assert 'db:' not in first_line and 'db =' not in first_line, (
            "REGRESSION: _execute_analysis must not accept a db parameter."
        )

    def test_batch_execute_brief_no_db_param(self):
        from app.services.batch.processor import BatchProcessor
        src = inspect.getsource(BatchProcessor._execute_brief)
        first_line = src.strip().split('\n')[0]
        assert 'db:' not in first_line, (
            "REGRESSION: _execute_brief must not accept a db parameter."
        )

    def test_batch_runs_analysis_creates_job_before_returning(self):
        """The run_analysis method creates the job synchronously before spawning the task."""
        from app.services.batch.processor import BatchProcessor
        src = inspect.getsource(BatchProcessor.run_analysis)
        # create_task must come AFTER _create_job
        create_job_pos = src.find("_create_job")
        create_task_pos = src.find("create_task")
        assert create_job_pos < create_task_pos, (
            "REGRESSION: job must be persisted before asyncio.create_task fires."
        )


class TestRegressionSummaryDetailSeparation:
    """
    REGRESSION: Summary endpoints were returning detail-only fields,
    breaking the contract.
    """

    @pytest.mark.asyncio
    async def test_analysis_latest_no_detail_fields(self, client):
        await client.post("/api/v1/analysis/run", json={"municipality_id": "TLX-APZ"})
        resp = await client.get("/api/v1/analysis/latest/TLX-APZ")
        data = resp.json()["data"]
        for excluded in ("demographic_profile", "economic_engine", "infrastructure_gaps", "speeches", "kpi_board"):
            assert excluded not in data, f"REGRESSION: AnalysisSummary must not include {excluded}"

    @pytest.mark.asyncio
    async def test_brief_latest_no_brief_data(self, client, mock_groq):
        await client.post("/api/v1/brief/run", json={
            "municipality_id": "TLX-APZ",
            "campaign_objective": "Ganar presidencia municipal Apizaco 2024",
        })
        resp = await client.get("/api/v1/brief/latest/TLX-APZ")
        assert "brief_data" not in resp.json()["data"], (
            "REGRESSION: BriefSummary must not expose brief_data"
        )

    @pytest.mark.asyncio
    async def test_speech_latest_no_speech_data(self, client, mock_groq):
        await client.post("/api/v1/speech/run", json={
            "municipality_id": "TLX-APZ",
            "speech_goal": "Movilizar apoyo ciudadano en zona industrial",
            "audience": "Trabajadoras y trabajadores textiles de Apizaco",
            "tone": "moderado", "channel": "mitin", "duration_minutes": 5,
        })
        resp = await client.get("/api/v1/speech/latest/TLX-APZ")
        assert "speech_data" not in resp.json()["data"], (
            "REGRESSION: SpeechSummary must not expose speech_data"
        )

    @pytest.mark.asyncio
    async def test_evidence_summary_no_raw_data_layers(self, client):
        await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        resp = await client.get("/api/v1/evidence/latest/TLX-APZ")
        data = resp.json()["data"]
        for excluded in ("social_data", "economic_data", "infrastructure_data"):
            assert excluded not in data, f"REGRESSION: EvidenceSummary must not expose {excluded}"


class TestRegressionDataQualityPlaceholders:
    """
    REGRESSION: routes were filling data_quality with fake zeros and empty strings
    for fields that don't exist on the DB model.
    """

    @pytest.mark.asyncio
    async def test_analysis_detail_no_zero_coverage_fields(self, client):
        resp = await client.post("/api/v1/analysis/run", json={"municipality_id": "TLX-APZ"})
        dq = resp.json()["data"]["data_quality"]
        # AnalysisDetail uses DataQualityBrief — only 2 real fields
        assert sorted(dq.keys()) == ["can_cite_as_municipal", "overall_confidence"], (
            "REGRESSION: AnalysisDetail.data_quality must have exactly 2 fields, no fake zeros."
        )
        assert "municipal_coverage_pct" not in dq
        assert "quality_label" not in dq

    @pytest.mark.asyncio
    async def test_evidence_summary_has_quality_label_not_empty(self, client):
        await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        resp = await client.get("/api/v1/evidence/latest/TLX-APZ")
        dq = resp.json()["data"]["data_quality"]
        assert dq.get("quality_label"), (
            "REGRESSION: EvidenceSummary.data_quality.quality_label must not be empty."
        )


class TestRegressionEstimatedDataNotCitedAsMunicipal:
    """
    REGRESSION: estimated data municipalities were shown as official municipal data.
    """

    @pytest.mark.asyncio
    async def test_estimated_municipality_cannot_cite_as_municipal(self, client):
        resp = await client.post("/api/v1/evidence/resolve/TLX-AMA", json={"force_refresh": False})
        dq = resp.json()["data"]["data_quality"]
        assert dq["can_cite_as_municipal"] is False, (
            "REGRESSION: Amaxac (estimated data) must have can_cite_as_municipal=False"
        )

    @pytest.mark.asyncio
    async def test_estimated_municipality_has_methodology_disclaimer(self, client):
        resp = await client.post("/api/v1/evidence/resolve/TLX-AMA", json={"force_refresh": False})
        dq = resp.json()["data"]["data_quality"]
        assert dq["methodology_disclaimer"] != "", (
            "REGRESSION: Estimated data must have a non-empty methodology disclaimer."
        )

    @pytest.mark.asyncio
    async def test_official_municipality_can_cite(self, client):
        resp = await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        dq = resp.json()["data"]["data_quality"]
        assert dq["can_cite_as_municipal"] is True


class TestRegressionMunicipalityCount:
    """
    REGRESSION: municipality JSON had 4 duplicate entries (61 records for 57 unique).
    """

    def test_no_duplicate_municipality_names(self):
        from app.services.territory.repository import TerritoryRepository
        repo = TerritoryRepository.get_instance()
        muns = repo.get_all_municipalities()
        names = [m["name"] for m in muns]
        duplicates = {n for n in names if names.count(n) > 1}
        assert duplicates == set(), f"REGRESSION: Duplicate municipalities: {duplicates}"

    def test_municipality_count_is_57(self):
        from app.core.constants import MUNICIPALITIES_COUNT
        assert MUNICIPALITIES_COUNT == 57, (
            f"REGRESSION: Expected 57 municipalities, got {MUNICIPALITIES_COUNT}."
        )

    def test_no_zacatelco_duplicate(self):
        from app.services.territory.repository import TerritoryRepository
        repo = TerritoryRepository.get_instance()
        zac = [m for m in repo.get_all_municipalities() if "Zacatelco" in m["name"]]
        assert len(zac) == 1, f"REGRESSION: Zacatelco appears {len(zac)} times, expected 1."


class TestRegressionValidationBlocksPresistence:
    """
    REGRESSION: brief/speech with blocking validation issues must never be
    persisted with validation_passed=True.
    """

    def test_validation_report_blocking_count_matches_issues(self):
        from app.services.validation.pipeline import output_validator
        bad = {
            "executive_summary": "Brief.",
            "key_findings": ["hallazgo 1 accionable", "hallazgo 2 accionable"],
            "pain_points": ["dolor ciudadano 1"],
            "messaging_axes": [],
            "recommended_tone": "moderado",
        }
        r = output_validator.validate_brief(bad)
        assert r.blocking_count == len(r.blocking_issues)
        assert not r.passed
        assert r.score < 1.0

    def test_placeholder_blocked_never_passes(self):
        from app.services.validation.pipeline import output_validator
        for placeholder in [
            "hallazgo 1 accionable",
            "[INSERT municipio]",
            "dolor ciudadano 2",
            "argumento racional 1",
            "línea de acción 3",
        ]:
            bad = {"executive_summary": "Test válido municipio.", "key_findings": [placeholder],
                   "pain_points": [], "messaging_axes": [], "recommended_tone": "moderado"}
            r = output_validator.validate_brief(bad)
            assert not r.passed, f"Must block placeholder: {placeholder}"


class TestRegressionReviewRunPersisted:
    """
    REGRESSION: POST /speech/review previously returned in-memory data only,
    no ID, no persistence. Must now return a real persisted ReviewRunDB.
    """

    @pytest.mark.asyncio
    async def test_review_returns_persisted_id(self, client, mock_groq):
        resp = await client.post("/api/v1/speech/review", json={
            "municipality_id": "TLX-APZ",
            "speech_text": "Ciudadanas y ciudadanos de Apizaco, vengo a hablar de trabajo y justicia para todos. " * 20,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        import uuid
        uuid.UUID(data["id"])  # raises if not valid UUID — proves it was persisted
        assert "municipality_id" in data
        assert "created_at" in data
