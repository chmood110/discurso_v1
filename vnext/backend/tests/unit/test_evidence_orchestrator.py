"""
Unit tests for EvidenceOrchestrator — quality computation and data differentiation.
"""
import pytest
import pytest_asyncio
from app.services.evidence.orchestrator import EvidenceOrchestrator, _compute_quality

eo = EvidenceOrchestrator()


class TestQualityComputation:

    def test_all_municipal_data_high_confidence(self):
        """Mock pack with all municipal-level data → high confidence, can_cite=True."""
        from types import SimpleNamespace
        def _dp(val, geo="municipal"):
            return SimpleNamespace(value=val, available=True, geographic_level=geo, unit="", source="INEGI", period="2020", limitation_note=None)

        social = SimpleNamespace(
            poverty_rate_pct=_dp(28.6, "municipal"),
            social_security_lack_pct=_dp(45.0, "municipal"),
            health_access_lack_pct=_dp(18.0, "municipal"),
            education_lag_pct=_dp(12.0, "municipal"),
            food_insecurity_pct=_dp(10.0, "municipal"),
        )
        pack = SimpleNamespace(social=social, economic=SimpleNamespace(), infrastructure=SimpleNamespace())
        quality = _compute_quality(pack)

        assert quality["overall_confidence"] >= 0.9
        assert quality["can_cite_as_municipal"] is True
        assert quality["municipal_coverage_pct"] > 80

    def test_estimated_data_low_confidence(self):
        """Pack with all calibrated_estimate data → low confidence, can_cite=False."""
        from types import SimpleNamespace
        def _dp(val, geo="regional"):
            return SimpleNamespace(value=val, available=True, geographic_level=geo, unit="", source="Estimado", period="2020", limitation_note=None)

        social = SimpleNamespace(
            poverty_rate_pct=_dp(32.0, "regional"),
            social_security_lack_pct=_dp(52.0, "regional"),
            health_access_lack_pct=_dp(24.0, "regional"),
            education_lag_pct=_dp(20.0, "regional"),
            food_insecurity_pct=_dp(18.0, "regional"),
        )
        pack = SimpleNamespace(social=social, economic=SimpleNamespace(), infrastructure=SimpleNamespace())
        quality = _compute_quality(pack)

        assert quality["overall_confidence"] <= 0.5
        assert quality["can_cite_as_municipal"] is False
        assert quality["methodology_disclaimer"] != ""

    def test_disclaimer_present_for_estimated(self):
        from types import SimpleNamespace
        def _dp(val, geo="regional"):
            return SimpleNamespace(value=val, available=True, geographic_level=geo, unit="", source="Est", period="2020", limitation_note=None)

        social = SimpleNamespace(poverty_rate_pct=_dp(40.0, "regional"))
        pack = SimpleNamespace(social=social, economic=SimpleNamespace(), infrastructure=SimpleNamespace())
        quality = _compute_quality(pack)
        assert "estimaciones calibradas" in quality["methodology_disclaimer"] or "estimación" in quality["methodology_disclaimer"].lower()

    def test_no_disclaimer_for_official_municipal(self):
        from types import SimpleNamespace
        def _dp(val):
            return SimpleNamespace(value=val, available=True, geographic_level="municipal", unit="", source="INEGI", period="2020", limitation_note=None)

        social = SimpleNamespace(
            poverty_rate_pct=_dp(28.6),
            social_security_lack_pct=_dp(45.0),
            health_access_lack_pct=_dp(18.0),
            education_lag_pct=_dp(12.0),
            food_insecurity_pct=_dp(10.0),
        )
        pack = SimpleNamespace(social=social, economic=SimpleNamespace(), infrastructure=SimpleNamespace())
        quality = _compute_quality(pack)
        assert quality["methodology_disclaimer"] == ""


class TestDataDifferentiation:

    @pytest.mark.asyncio
    async def test_different_municipalities_different_poverty(self, seeded_db):
        r1 = await eo.resolve("TLX-APZ", seeded_db)  # Apizaco — official
        r2 = await eo.resolve("TLX-TLC", seeded_db)  # Tlaxco — high poverty
        r3 = await eo.resolve("TLX-AMA", seeded_db)  # Amaxac — estimated

        pov1 = r1.social_data.get("poverty_rate_pct", {}).get("value")
        pov2 = r2.social_data.get("poverty_rate_pct", {}).get("value")
        pov3 = r3.social_data.get("poverty_rate_pct", {}).get("value")

        assert pov1 != pov2 != pov3, "Municipalities must have distinct poverty rates"
        assert pov2 > pov1, "Tlaxco (sierra) should have higher poverty than Apizaco (valley)"

    @pytest.mark.asyncio
    async def test_official_municipal_can_cite(self, seeded_db):
        r = await eo.resolve("TLX-APZ", seeded_db)
        assert r.can_cite_as_municipal is True

    @pytest.mark.asyncio
    async def test_estimated_cannot_cite(self, seeded_db):
        r = await eo.resolve("TLX-AMA", seeded_db)
        assert r.can_cite_as_municipal is False
        assert r.methodology_disclaimer != ""


class TestParameterHashing:

    def test_brief_same_params_same_hash(self):
        from app.services.documents.brief_orchestrator import _param_hash
        from app.models.schemas import BriefRunRequest
        r1 = BriefRunRequest(municipality_id="TLX-APZ", campaign_objective="Ganar presidencia municipal Apizaco 2024")
        r2 = BriefRunRequest(municipality_id="TLX-APZ", campaign_objective="Ganar presidencia municipal Apizaco 2024")
        assert _param_hash(r1) == _param_hash(r2)

    def test_brief_different_objective_different_hash(self):
        from app.services.documents.brief_orchestrator import _param_hash
        from app.models.schemas import BriefRunRequest
        r1 = BriefRunRequest(municipality_id="TLX-APZ", campaign_objective="Ganar presidencia municipal Apizaco 2024")
        r2 = BriefRunRequest(municipality_id="TLX-APZ", campaign_objective="Campaña de regiduría tercer lugar")
        assert _param_hash(r1) != _param_hash(r2)

    def test_speech_same_params_same_hash(self):
        from app.services.documents.speech_orchestrator import _speech_param_hash
        from app.models.schemas import SpeechRunRequest
        r1 = SpeechRunRequest(municipality_id="TLX-APZ", speech_goal="Movilizar apoyo ciudadano en barrios", audience="Vecinos de colonias populares", tone="moderado", channel="mitin", duration_minutes=10)
        r2 = SpeechRunRequest(municipality_id="TLX-APZ", speech_goal="Movilizar apoyo ciudadano en barrios", audience="Vecinos de colonias populares", tone="moderado", channel="mitin", duration_minutes=10)
        assert _speech_param_hash(r1) == _speech_param_hash(r2)

    def test_speech_different_tone_different_hash(self):
        from app.services.documents.speech_orchestrator import _speech_param_hash
        from app.models.schemas import SpeechRunRequest
        r1 = SpeechRunRequest(municipality_id="TLX-APZ", speech_goal="Movilizar apoyo ciudadano en barrios", audience="Vecinos de colonias populares", tone="moderado", channel="mitin", duration_minutes=10)
        r2 = SpeechRunRequest(municipality_id="TLX-APZ", speech_goal="Movilizar apoyo ciudadano en barrios", audience="Vecinos de colonias populares", tone="combativo y propositivo", channel="mitin", duration_minutes=10)
        assert _speech_param_hash(r1) != _speech_param_hash(r2)
