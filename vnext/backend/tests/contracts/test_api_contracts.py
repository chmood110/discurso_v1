"""
Contract tests — verify every active endpoint returns the promised shape.
Aligned with the current vNext router:
- health
- territory
- evidence
- analysis
- speech
- exports
"""
import pytest


class TestHealthContracts:
    @pytest.mark.asyncio
    async def test_health_returns_expected_shape(self, client):
        resp = await client.get("/api/v1/health/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["message"]
        assert body["data"]["status"] == "ok"


class TestTerritoryContracts:
    @pytest.mark.asyncio
    async def test_municipalities_returns_list_shape(self, client):
        resp = await client.get("/api/v1/territory/municipalities")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        for field in ("id", "name"):
            assert field in first, f"Missing municipality field: {field}"

    @pytest.mark.asyncio
    async def test_municipality_detail_returns_neighborhoods(self, client):
        resp = await client.get("/api/v1/territory/municipalities/TLX-APZ")
        assert resp.status_code == 200
        data = resp.json()["data"]
        for field in ("id", "name", "neighborhoods"):
            assert field in data, f"Missing municipality detail field: {field}"
        assert isinstance(data["neighborhoods"], list)

    @pytest.mark.asyncio
    async def test_neighborhoods_returns_list(self, client):
        resp = await client.get("/api/v1/territory/neighborhoods/TLX-APZ")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_municipality_returns_404(self, client):
        resp = await client.get("/api/v1/territory/municipalities/TLX-XXXX")
        assert resp.status_code == 404


class TestEvidenceContracts:
    """POST /evidence/resolve → EvidenceDetail | GET /evidence/latest → EvidenceSummary"""

    @pytest.mark.asyncio
    async def test_resolve_returns_evidence_detail_shape(self, client):
        resp = await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        for field in (
            "id",
            "municipality_id",
            "municipality_name",
            "snapshot_version",
            "created_at",
            "collection_method",
            "sources_used",
            "geographic_fallbacks",
            "data_quality",
        ):
            assert field in data, f"Missing field in EvidenceDetail: {field}"

        dq = data["data_quality"]
        for f in (
            "overall_confidence",
            "municipal_coverage_pct",
            "state_coverage_pct",
            "estimated_coverage_pct",
            "can_cite_as_municipal",
            "quality_label",
            "methodology_disclaimer",
        ):
            assert f in dq, f"Missing DataQualitySummary field: {f}"

    @pytest.mark.asyncio
    async def test_resolve_no_unexpected_internal_payload(self, client):
        resp = await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        data = resp.json()["data"]
        for excluded in ("social_data", "economic_data", "infrastructure_data"):
            assert excluded not in data, f"EvidenceDetail should not expose: {excluded}"

    @pytest.mark.asyncio
    async def test_latest_returns_evidence_summary_shape(self, client):
        await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        resp = await client.get("/api/v1/evidence/latest/TLX-APZ")
        assert resp.status_code == 200
        data = resp.json()["data"]

        for field in (
            "id",
            "municipality_id",
            "municipality_name",
            "created_at",
            "collection_method",
            "data_quality",
        ):
            assert field in data, f"Missing field in EvidenceSummary: {field}"

        dq = data["data_quality"]
        assert sorted(dq.keys()) == ["can_cite_as_municipal", "overall_confidence", "quality_label"]
        assert "methodology_disclaimer" not in dq
        assert "municipal_coverage_pct" not in dq

    @pytest.mark.asyncio
    async def test_latest_summary_has_quality_label_not_empty(self, client):
        await client.post("/api/v1/evidence/resolve/TLX-APZ", json={"force_refresh": False})
        resp = await client.get("/api/v1/evidence/latest/TLX-APZ")
        dq = resp.json()["data"]["data_quality"]
        assert isinstance(dq["quality_label"], str) and len(dq["quality_label"]) > 3

    @pytest.mark.asyncio
    async def test_invalid_municipality_resolve_returns_404(self, client):
        resp = await client.post("/api/v1/evidence/resolve/TLX-ZZZZ", json={"force_refresh": False})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_latest_not_resolved_returns_404(self, client):
        resp = await client.get("/api/v1/evidence/latest/TLX-HMT-NEVER")
        assert resp.status_code == 404


class TestAnalysisContracts:
    @pytest.mark.asyncio
    async def test_run_returns_analysis_detail_shape(self, client):
        resp = await client.post(
            "/api/v1/analysis/run",
            json={"municipality_id": "TLX-APZ", "force_refresh": False},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        for field in (
            "id",
            "municipality_id",
            "evidence_record_id",
            "created_at",
            "status",
            "objective",
            "executive_summary",
            "demographic_profile",
            "economic_engine",
            "infrastructure_gaps",
            "critical_needs",
            "opportunities",
            "kpi_board",
            "strategy_section",
            "data_quality",
            "validation",
        ):
            assert field in data, f"Missing AnalysisDetail field: {field}"

        assert sorted(data["data_quality"].keys()) == ["can_cite_as_municipal", "overall_confidence"]
        assert "rule_version" in data["validation"]

        strategy = data["strategy_section"]
        for field in (
            "executive_strategic",
            "messaging_axes",
            "pain_points_ranked",
            "opportunities_ranked",
            "candidate_positioning",
            "recommended_tone",
            "risk_flags",
            "framing_suggestions",
            "communication_channels_priority",
            "ai_generated",
        ):
            assert field in strategy, f"Missing StrategySection field: {field}"

    @pytest.mark.asyncio
    async def test_latest_returns_analysis_summary_without_detail_fields(self, client):
        await client.post("/api/v1/analysis/run", json={"municipality_id": "TLX-APZ"})
        resp = await client.get("/api/v1/analysis/latest/TLX-APZ")
        assert resp.status_code == 200
        data = resp.json()["data"]

        for field in ("id", "municipality_id", "executive_summary", "data_quality", "validation"):
            assert field in data

        for excluded in (
            "demographic_profile",
            "economic_engine",
            "infrastructure_gaps",
            "critical_needs",
            "kpi_board",
            "strategy_section",
        ):
            assert excluded not in data, f"AnalysisSummary should not expose: {excluded}"

        assert data["validation"]["issues"] == []

    @pytest.mark.asyncio
    async def test_history_returns_list_of_summaries(self, client):
        await client.post("/api/v1/analysis/run", json={"municipality_id": "TLX-APZ"})
        resp = await client.get("/api/v1/analysis/history/TLX-APZ")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            assert "strategy_section" not in item
            assert "demographic_profile" not in item


class TestSpeechContracts:
    @pytest.mark.asyncio
    async def test_run_returns_speech_detail_shape(self, client, mock_groq):
        resp = await client.post(
            "/api/v1/speech/run",
            json={
                "municipality_id": "TLX-APZ",
                "speech_goal": "Movilizar apoyo ciudadano en zona industrial",
                "audience": "Trabajadoras y trabajadores textiles de Apizaco",
                "tone": "combativo y propositivo",
                "channel": "mitin",
                "duration_minutes": 5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        for field in (
            "id",
            "municipality_id",
            "analysis_run_id",
            "created_at",
            "status",
            "speech_type",
            "speech_data",
            "target_duration_minutes",
            "target_word_count",
            "actual_word_count",
            "retry_count",
            "parameter_hash",
            "ai_generated",
            "latency_ms",
            "data_quality",
            "validation",
        ):
            assert field in data, f"Missing SpeechDetail field: {field}"

        speech_data = data["speech_data"]
        for field in (
            "title",
            "speech_objective",
            "target_audience",
            "estimated_duration_minutes",
            "estimated_word_count",
            "opening",
            "body_sections",
            "closing",
            "full_text",
            "duration_verification",
            "generation_plan",
            "adaptation_notes",
        ):
            assert field in speech_data, f"Missing SpeechData field: {field}"

        duration = speech_data["duration_verification"]
        for field in (
            "target_minutes",
            "estimated_minutes",
            "lower_bound_minutes",
            "upper_bound_minutes",
            "within_tolerance",
            "delta_minutes",
            "delta_pct",
            "words_per_minute",
            "actual_word_count",
        ):
            assert field in duration, f"Missing DurationVerification field: {field}"

        plan = speech_data["generation_plan"]
        for field in (
            "target_words",
            "minimum_words",
            "opening_words",
            "closing_words",
            "body_sections",
            "body_section_words",
            "batches",
        ):
            assert field in plan, f"Missing GenerationPlan field: {field}"

    @pytest.mark.asyncio
    async def test_improvement_returns_source_processing_shape(self, client, mock_groq):
        resp = await client.post(
            "/api/v1/speech/run",
            json={
                "municipality_id": "TLX-APZ",
                "speech_goal": "Mejorar discurso para reunión vecinal",
                "audience": "Vecinas y vecinos de Apizaco",
                "tone": "moderado",
                "channel": "reunion_vecinal",
                "duration_minutes": 10,
                "source_text": (
                    "Queridas vecinas y vecinos de Apizaco, hoy quiero hablarles del agua, "
                    "del empleo, de la seguridad y de la salud de nuestras familias. "
                ) * 20,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["speech_type"] == "adaptation"

        source_processing = data["speech_data"]["source_processing"]
        for field in (
            "word_count",
            "paragraph_count",
            "segments_count",
            "estimated_minutes",
            "alpha_ratio",
            "prompt_ready_word_count",
            "segment_previews",
        ):
            assert field in source_processing, f"Missing SourceProcessing field: {field}"

    @pytest.mark.asyncio
    async def test_latest_returns_speech_summary_without_speech_data(self, client, mock_groq):
        await client.post(
            "/api/v1/speech/run",
            json={
                "municipality_id": "TLX-APZ",
                "speech_goal": "Movilizar apoyo ciudadano en zona industrial",
                "audience": "Trabajadoras y trabajadores textiles de Apizaco",
                "tone": "moderado",
                "channel": "mitin",
                "duration_minutes": 5,
            },
        )
        resp = await client.get("/api/v1/speech/latest/TLX-APZ")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "speech_data" not in data, "SpeechSummary must not expose speech_data"
        assert "target_word_count" in data
        assert "actual_word_count" in data
        assert "parameter_hash" in data


class TestExportContracts:
    @pytest.mark.asyncio
    async def test_export_analysis_pdf_returns_pdf(self, client):
        run_resp = await client.post(
            "/api/v1/analysis/run",
            json={"municipality_id": "TLX-APZ", "force_refresh": False},
        )
        run_id = run_resp.json()["data"]["id"]

        resp = await client.get(f"/api/v1/exports/pdf/analysis/{run_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_export_speech_pdf_returns_pdf(self, client, mock_groq):
        run_resp = await client.post(
            "/api/v1/speech/run",
            json={
                "municipality_id": "TLX-APZ",
                "speech_goal": "Movilizar apoyo ciudadano en zona industrial",
                "audience": "Trabajadoras y trabajadores textiles de Apizaco",
                "tone": "moderado",
                "channel": "mitin",
                "duration_minutes": 5,
            },
        )
        run_id = run_resp.json()["data"]["id"]

        resp = await client.get(f"/api/v1/exports/pdf/speech/{run_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"