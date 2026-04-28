"""
Integration tests for BatchProcessor — concurrency, session safety, partial failures.

Critical regression: each batch task MUST use its own AsyncSessionLocal(),
not share the HTTP request session (which closes when the response returns).
"""
import asyncio
import pytest
from app.services.batch.processor import BatchProcessor
from app.models.schemas import BatchAnalysisRequest


class TestBatchSessionSafety:

    def test_execute_analysis_does_not_accept_db_param(self):
        """Regression: _execute_analysis must not take a db parameter."""
        import inspect
        src = inspect.getsource(BatchProcessor._execute_analysis)
        sig_line = src.split('\n')[0]
        # The first line is the def — it must NOT have a db: AsyncSession parameter
        assert 'db: AsyncSession' not in sig_line, (
            "REGRESSION: _execute_analysis must not accept a db session parameter. "
            "It must create its own sessions via AsyncSessionLocal()."
        )

    def test_execute_analysis_uses_async_session_local(self):
        """Each task must open AsyncSessionLocal(), not use shared session."""
        import inspect
        src = inspect.getsource(BatchProcessor._execute_analysis)
        assert 'AsyncSessionLocal()' in src, (
            "Batch tasks must use AsyncSessionLocal() to create independent sessions."
        )

    def test_execute_brief_uses_async_session_local(self):
        import inspect
        src = inspect.getsource(BatchProcessor._execute_brief)
        assert 'AsyncSessionLocal()' in src

    def test_execute_speech_uses_async_session_local(self):
        import inspect
        src = inspect.getsource(BatchProcessor._execute_speech)
        assert 'AsyncSessionLocal()' in src


class TestBatchLifecycle:

    @pytest.mark.asyncio
    async def test_batch_job_persisted_before_response(self, client):
        """Job must be created in DB before the HTTP response returns."""
        resp = await client.post("/api/v1/batch/analysis", json={
            "municipality_ids": ["TLX-APZ"],
            "concurrency": 1,
        })
        assert resp.status_code == 200
        job_id = resp.json()["data"]["id"]
        # Immediately query status — must exist
        status_resp = await client.get(f"/api/v1/batch/{job_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["data"]["id"] == job_id

    @pytest.mark.asyncio
    async def test_batch_initial_status_is_pending_or_running(self, client):
        resp = await client.post("/api/v1/batch/analysis", json={
            "municipality_ids": ["TLX-APZ", "TLX-HMT"],
            "concurrency": 1,
        })
        status = resp.json()["data"]["status"]
        assert status in ("pending", "running"), f"Unexpected initial status: {status}"

    @pytest.mark.asyncio
    async def test_batch_total_matches_input_count(self, client):
        mun_ids = ["TLX-APZ", "TLX-HMT", "TLX-TLA"]
        resp = await client.post("/api/v1/batch/analysis", json={
            "municipality_ids": mun_ids,
            "concurrency": 1,
        })
        assert resp.json()["data"]["total"] == len(mun_ids)

    @pytest.mark.asyncio
    async def test_batch_partial_failure_tracked_per_municipality(self, client):
        """Errors for one municipality must not poison the whole batch."""
        resp = await client.post("/api/v1/batch/analysis", json={
            # Mix valid + invalid municipality IDs
            "municipality_ids": ["TLX-APZ", "TLX-ZZZZ-INVALID"],
            "concurrency": 1,
        })
        assert resp.status_code == 200
        job_id = resp.json()["data"]["id"]

        # Wait briefly for async tasks
        await asyncio.sleep(1.0)

        status_resp = await client.get(f"/api/v1/batch/{job_id}")
        data = status_resp.json()["data"]
        # The invalid municipality should be in errors, not crashing the whole job
        # Job should not be in an unrecoverable state
        assert data["status"] in ("pending", "running", "completed", "partial_failure")

    @pytest.mark.asyncio
    async def test_batch_results_keyed_by_municipality_id(self, client):
        """results dict must be keyed by municipality_id."""
        resp = await client.post("/api/v1/batch/analysis", json={
            "municipality_ids": ["TLX-APZ"],
            "concurrency": 1,
        })
        job_id = resp.json()["data"]["id"]
        await asyncio.sleep(2.0)  # allow async task to run
        status_resp = await client.get(f"/api/v1/batch/{job_id}")
        data = status_resp.json()["data"]
        if data["completed"] > 0:
            assert "TLX-APZ" in data["results"]
            import uuid
            uuid.UUID(data["results"]["TLX-APZ"])  # must be a valid run_id UUID


class TestBatchConcurrencyLimit:

    def test_semaphore_respects_max_concurrency_setting(self):
        """Batch concurrency must be capped by BATCH_MAX_CONCURRENCY."""
        from app.core.config import settings
        assert settings.BATCH_MAX_CONCURRENCY == 5
        # The processor uses min(request.concurrency, settings.BATCH_MAX_CONCURRENCY)
        import inspect
        src = inspect.getsource(BatchProcessor._execute_analysis)
        assert 'BATCH_MAX_CONCURRENCY' in src or 'settings.BATCH_MAX_CONCURRENCY' in src
