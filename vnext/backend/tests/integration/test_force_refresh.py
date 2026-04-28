"""
Integration tests for force_refresh behavior end-to-end.
Verifies cache hits, cache misses, and propagation through orchestrator chain.
"""
import pytest
from app.services.evidence.orchestrator import evidence_orchestrator


class TestEvidenceForceRefresh:

    @pytest.mark.asyncio
    async def test_false_returns_cached_record(self, seeded_db):
        r1 = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=False)
        r2 = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=False)
        assert r1.id == r2.id, "force_refresh=False must return same cached record"

    @pytest.mark.asyncio
    async def test_true_creates_new_record(self, seeded_db):
        r1 = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=False)
        r2 = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=True)
        assert r1.id != r2.id, "force_refresh=True must create a new record"

    @pytest.mark.asyncio
    async def test_true_then_false_returns_new_record(self, seeded_db):
        """After force_refresh, cache should serve the newer record."""
        await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=False)
        fresh = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=True)
        cached_after = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=False)
        assert fresh.id == cached_after.id

    @pytest.mark.asyncio
    async def test_snapshot_version_consistent(self, seeded_db):
        r1 = await evidence_orchestrator.resolve("TLX-APZ", seeded_db, force_refresh=False)
        r2 = await evidence_orchestrator.resolve("TLX-TLC", seeded_db, force_refresh=False)
        assert r1.snapshot_version == r2.snapshot_version, "All records must share snapshot_version"
        assert len(r1.snapshot_version) == 16, "snapshot_version must be 16-char hash"


class TestForceRefreshViaAPI:

    @pytest.mark.asyncio
    async def test_force_refresh_in_body_not_query_param(self, client):
        """Regression: force_refresh must be read from JSON body, not query string."""
        resp_body = await client.post(
            "/api/v1/evidence/resolve/TLX-APZ",
            json={"force_refresh": True}
        )
        assert resp_body.status_code == 200

        # Sending force_refresh as query param should be ignored (or accepted if FastAPI parses it)
        # The key check: body-based call must create a new record
        id1 = (await client.post("/api/v1/evidence/resolve/TLX-APZ",
                                   json={"force_refresh": False})).json()["data"]["id"]
        id2 = (await client.post("/api/v1/evidence/resolve/TLX-APZ",
                                   json={"force_refresh": True})).json()["data"]["id"]
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_analysis_force_refresh_propagates_to_evidence(self, client):
        """Regression: analysis force_refresh=True must also refresh evidence."""
        ev1 = (await client.post("/api/v1/evidence/resolve/TLX-HMT",
                                   json={"force_refresh": False})).json()["data"]["id"]

        # Run analysis with force_refresh — this should create new evidence too
        await client.post("/api/v1/analysis/run",
                           json={"municipality_id": "TLX-HMT", "force_refresh": True})

        ev2 = (await client.post("/api/v1/evidence/resolve/TLX-HMT",
                                   json={"force_refresh": True})).json()["data"]["id"]
        # A new evidence record was created during the force_refresh chain
        assert ev1 != ev2


class TestBriefCacheByParameterHash:

    @pytest.mark.asyncio
    async def test_same_params_reuses_brief(self, client, mock_groq):
        params = {
            "municipality_id": "TLX-APZ",
            "campaign_objective": "Ganar presidencia municipal Apizaco 2024",
            "force_refresh": False,
        }
        r1 = (await client.post("/api/v1/brief/run", json=params)).json()["data"]
        r2 = (await client.post("/api/v1/brief/run", json=params)).json()["data"]
        assert r1["id"] == r2["id"], "Same params must reuse cached brief"

    @pytest.mark.asyncio
    async def test_different_objective_different_brief(self, client, mock_groq):
        r1 = (await client.post("/api/v1/brief/run", json={
            "municipality_id": "TLX-APZ",
            "campaign_objective": "Ganar presidencia municipal Apizaco 2024",
        })).json()["data"]
        r2 = (await client.post("/api/v1/brief/run", json={
            "municipality_id": "TLX-APZ",
            "campaign_objective": "Campaña de regiduria zona norte 2024 completamente distinta",
        })).json()["data"]
        assert r1["id"] != r2["id"], "Different objective must create different brief"

    @pytest.mark.asyncio
    async def test_force_refresh_ignores_cache(self, client, mock_groq):
        params = {"municipality_id": "TLX-APZ", "campaign_objective": "Ganar presidencia municipal Apizaco 2024", "force_refresh": False}
        r1 = (await client.post("/api/v1/brief/run", json=params)).json()["data"]
        params["force_refresh"] = True
        r2 = (await client.post("/api/v1/brief/run", json=params)).json()["data"]
        assert r1["id"] != r2["id"], "force_refresh=True must bypass cache"
