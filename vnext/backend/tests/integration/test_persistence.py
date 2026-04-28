"""
Persistence integration tests — verify all DB models round-trip correctly.
"""
import pytest
import uuid
from datetime import datetime, timezone
from app.models.db_models import (
    EvidenceRecordDB, AnalysisRunDB, BriefRunDB,
    SpeechRunDB, ReviewRunDB, BatchJobDB,
)
from app.db.repositories.evidence_repo import EvidenceRepository
from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.brief_repo import BriefRepository
from app.db.repositories.speech_repo import SpeechRepository
from app.db.repositories.review_repo import ReviewRepository
from app.db.repositories.batch_repo import BatchRepository


def _now(): return datetime.now(timezone.utc)
def _uuid(): return str(uuid.uuid4())


class TestEvidencePersistence:

    @pytest.mark.asyncio
    async def test_save_and_retrieve(self, seeded_db):
        rec = EvidenceRecordDB(
            id=_uuid(), municipality_id="TLX-APZ",
            municipality_name="Apizaco",
            snapshot_version="abc123def456abcd",
            created_at=_now(),
            collection_method="reference",
            overall_confidence=0.95,
            municipal_coverage_pct=80.0,
            state_coverage_pct=10.0,
            estimated_coverage_pct=10.0,
            can_cite_as_municipal=True,
            quality_label="Alta",
            methodology_disclaimer="",
            social_data={"poverty_rate_pct": {"value": 28.6}},
            economic_data={},
            infrastructure_data={},
            sources_used=["INEGI", "CONEVAL"],
            sources_failed=[],
            geographic_fallbacks=[],
        )
        repo = EvidenceRepository(seeded_db)
        saved = await repo.save(rec)
        loaded = await repo.get_by_id(saved.id)

        assert loaded is not None
        assert loaded.municipality_name == "Apizaco"
        assert loaded.overall_confidence == 0.95
        assert loaded.can_cite_as_municipal is True
        assert "INEGI" in loaded.sources_used

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(self, seeded_db):
        # Use TLX-CAL (Calpulalpan) — not used by any other persistence test
        repo = EvidenceRepository(seeded_db)
        r1 = EvidenceRecordDB(id=_uuid(), municipality_id="TLX-CAL", municipality_name="Calpulalpan",
            snapshot_version="persist_v1_older", created_at=datetime(2024,1,1,tzinfo=timezone.utc),
            collection_method="reference", overall_confidence=0.8, municipal_coverage_pct=70.0,
            state_coverage_pct=15.0, estimated_coverage_pct=15.0, can_cite_as_municipal=True,
            quality_label="Alta", methodology_disclaimer="", social_data={}, economic_data={},
            infrastructure_data={}, sources_used=[], sources_failed=[], geographic_fallbacks=[])
        r2 = EvidenceRecordDB(id=_uuid(), municipality_id="TLX-CAL", municipality_name="Calpulalpan",
            snapshot_version="persist_v2_newer", created_at=datetime(2024,6,1,tzinfo=timezone.utc),
            collection_method="reference", overall_confidence=0.95, municipal_coverage_pct=80.0,
            state_coverage_pct=10.0, estimated_coverage_pct=10.0, can_cite_as_municipal=True,
            quality_label="Alta", methodology_disclaimer="", social_data={}, economic_data={},
            infrastructure_data={}, sources_used=[], sources_failed=[], geographic_fallbacks=[])
        await repo.save(r1)
        await repo.save(r2)
        latest = await repo.get_latest("TLX-CAL")
        assert latest.snapshot_version == "persist_v2_newer"

    @pytest.mark.asyncio
    async def test_is_fresh_stale_snapshot_returns_false(self, seeded_db):
        repo = EvidenceRepository(seeded_db)
        rec = EvidenceRecordDB(id=_uuid(), municipality_id="TLX-APZ", municipality_name="Apizaco",
            snapshot_version="old_hash_abcd1234", created_at=_now(),
            collection_method="reference", overall_confidence=0.9, municipal_coverage_pct=80.0,
            state_coverage_pct=10.0, estimated_coverage_pct=10.0, can_cite_as_municipal=True,
            quality_label="Alta", methodology_disclaimer="", social_data={}, economic_data={},
            infrastructure_data={}, sources_used=[], sources_failed=[], geographic_fallbacks=[])
        await repo.save(rec)
        # Different current snapshot → stale
        assert await repo.is_fresh(rec, "different_hash_xyz") is False

    @pytest.mark.asyncio
    async def test_is_fresh_matching_snapshot_returns_true(self, seeded_db):
        repo = EvidenceRepository(seeded_db)
        rec = EvidenceRecordDB(id=_uuid(), municipality_id="TLX-APZ", municipality_name="Apizaco",
            snapshot_version="matching_hash1234", created_at=_now(),
            collection_method="reference", overall_confidence=0.9, municipal_coverage_pct=80.0,
            state_coverage_pct=10.0, estimated_coverage_pct=10.0, can_cite_as_municipal=True,
            quality_label="Alta", methodology_disclaimer="", social_data={}, economic_data={},
            infrastructure_data={}, sources_used=[], sources_failed=[], geographic_fallbacks=[])
        await repo.save(rec)
        assert await repo.is_fresh(rec, "matching_hash1234") is True


class TestAnalysisPersistence:

    @pytest.mark.asyncio
    async def test_get_latest_valid_excludes_invalid_status(self, seeded_db):
        ev_id = _uuid()
        ev = EvidenceRecordDB(id=ev_id, municipality_id="TLX-APZ", municipality_name="Apizaco",
            snapshot_version="snap", created_at=_now(), collection_method="reference",
            overall_confidence=0.9, municipal_coverage_pct=80.0, state_coverage_pct=10.0,
            estimated_coverage_pct=10.0, can_cite_as_municipal=True, quality_label="Alta",
            methodology_disclaimer="", social_data={}, economic_data={}, infrastructure_data={},
            sources_used=[], sources_failed=[], geographic_fallbacks=[])
        seeded_db.add(ev)
        await seeded_db.commit()

        repo = AnalysisRepository(seeded_db)
        # Save an invalid run
        invalid = AnalysisRunDB(id=_uuid(), municipality_id="TLX-APZ", evidence_record_id=ev_id,
            created_at=_now(), status="invalid", executive_summary="Old",
            demographic_profile={}, economic_engine={}, infrastructure_gaps={},
            critical_needs=[], opportunities=[], kpi_board={}, speeches={},
            overall_confidence=0.9, can_cite_as_municipal=True,
            validation_passed=True, validation_score=1.0, validation_issues=[])
        await repo.save(invalid)

        latest = await repo.get_latest_valid("TLX-APZ")
        assert latest is None or latest.status == "completed"

    @pytest.mark.asyncio
    async def test_validation_passed_false_not_returned_by_latest_valid(self, seeded_db):
        ev_id = _uuid()
        seeded_db.add(EvidenceRecordDB(id=ev_id, municipality_id="TLX-APZ", municipality_name="Apizaco",
            snapshot_version="snap2", created_at=_now(), collection_method="reference",
            overall_confidence=0.5, municipal_coverage_pct=40.0, state_coverage_pct=30.0,
            estimated_coverage_pct=30.0, can_cite_as_municipal=False, quality_label="Media",
            methodology_disclaimer="X", social_data={}, economic_data={}, infrastructure_data={},
            sources_used=[], sources_failed=[], geographic_fallbacks=[]))
        await seeded_db.commit()

        repo = AnalysisRepository(seeded_db)
        failed = AnalysisRunDB(id=_uuid(), municipality_id="TLX-APZ", evidence_record_id=ev_id,
            created_at=_now(), status="completed", executive_summary="Bad",
            demographic_profile={}, economic_engine={}, infrastructure_gaps={},
            critical_needs=[], opportunities=[], kpi_board={}, speeches={},
            overall_confidence=0.5, can_cite_as_municipal=False,
            validation_passed=False, validation_score=0.0, validation_issues=[{"code": "PLACEHOLDER", "severity": "blocking"}])
        await repo.save(failed)

        latest = await repo.get_latest_valid("TLX-APZ")
        if latest:
            assert latest.validation_passed is True


class TestReviewPersistence:

    @pytest.mark.asyncio
    async def test_review_run_persists_and_retrieves(self, seeded_db):
        repo = ReviewRepository(seeded_db)
        review = ReviewRunDB(
            id=_uuid(), municipality_id="TLX-APZ",
            created_at=_now(), status="completed",
            speech_text_excerpt="Ciudadanos de Apizaco...",
            speech_text_length=500,
            review_data={"overall_score": 8.0, "strengths": ["bien territorializado"]},
            overall_score=8.0, ai_generated=True, latency_ms=1200.0,
        )
        saved = await repo.save(review)
        loaded = await repo.get_by_id(saved.id)

        assert loaded is not None
        assert loaded.overall_score == 8.0
        assert loaded.ai_generated is True
        assert "overall_score" in loaded.review_data

    @pytest.mark.asyncio
    async def test_review_has_id_from_db(self, seeded_db):
        repo = ReviewRepository(seeded_db)
        review = ReviewRunDB(id=_uuid(), municipality_id="TLX-APZ",
            created_at=_now(), status="completed",
            speech_text_excerpt="Test", speech_text_length=4,
            review_data={}, overall_score=None, ai_generated=False)
        saved = await repo.save(review)
        import uuid as uuid_mod
        uuid_mod.UUID(saved.id)  # raises if not valid UUID


class TestBriefParameterHashPersistence:

    @pytest.mark.asyncio
    async def test_get_latest_by_params_returns_matching_hash(self, seeded_db):
        ev_id = _uuid()
        analysis_id = _uuid()
        seeded_db.add(EvidenceRecordDB(id=ev_id, municipality_id="TLX-APZ", municipality_name="Apizaco",
            snapshot_version="snap3", created_at=_now(), collection_method="reference",
            overall_confidence=0.9, municipal_coverage_pct=80.0, state_coverage_pct=10.0,
            estimated_coverage_pct=10.0, can_cite_as_municipal=True, quality_label="Alta",
            methodology_disclaimer="", social_data={}, economic_data={}, infrastructure_data={},
            sources_used=[], sources_failed=[], geographic_fallbacks=[]))
        seeded_db.add(AnalysisRunDB(id=analysis_id, municipality_id="TLX-APZ",
            evidence_record_id=ev_id, created_at=_now(), status="completed",
            executive_summary="Test", demographic_profile={}, economic_engine={},
            infrastructure_gaps={}, critical_needs=[], opportunities=[], kpi_board={}, speeches={},
            overall_confidence=0.9, can_cite_as_municipal=True,
            validation_passed=True, validation_score=1.0, validation_issues=[]))
        await seeded_db.commit()

        repo = BriefRepository(seeded_db)
        hash_val = "abcd1234ef567890"
        brief = BriefRunDB(id=_uuid(), municipality_id="TLX-APZ", analysis_run_id=analysis_id,
            created_at=_now(), status="completed", campaign_objective="Ganar presidencia",
            candidate_context={}, brief_data={"executive_summary": "Test brief"},
            parameter_hash=hash_val, ai_generated=True, latency_ms=500.0,
            overall_confidence=0.9, can_cite_as_municipal=True,
            validation_passed=True, validation_score=1.0, validation_issues=[])
        await repo.save(brief)

        found = await repo.get_latest_by_params("TLX-APZ", hash_val)
        assert found is not None
        assert found.parameter_hash == hash_val

        not_found = await repo.get_latest_by_params("TLX-APZ", "different_hash_xyz")
        assert not_found is None
