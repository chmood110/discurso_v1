"""
Unit tests for OutputValidationPipeline.
"""
from app.services.validation.pipeline import OutputValidationPipeline

vp = OutputValidationPipeline()


class TestBriefValidation:
    def _good_brief(self) -> dict:
        return {
            "executive_summary": "Apizaco es un municipio industrial con 28.6% de pobreza y alta informalidad laboral.",
            "key_findings": ["Alta informalidad laboral en manufactura textil"],
            "pain_points": ["Empleo precario sin prestaciones"],
            "messaging_axes": [
                {
                    "axis": "Trabajo digno",
                    "message": "Apizaco merece empleos con contrato real.",
                    "rationale": "42% informalidad",
                }
            ],
            "recommended_tone": "combativo y propositivo",
        }

    def test_good_brief_passes(self):
        r = vp.validate_brief(self._good_brief())
        assert r.passed
        assert r.score == 1.0

    def test_placeholder_in_list_blocked(self):
        b = self._good_brief()
        b["key_findings"] = ["hallazgo 1 accionable", "hallazgo real"]
        r = vp.validate_brief(b)
        assert not r.passed
        codes = {i.code for i in r.blocking_issues}
        assert "PLACEHOLDER_IN_LIST" in codes

    def test_multiple_placeholder_patterns_blocked(self):
        for placeholder in ["dolor ciudadano 1", "gancho emocional 2", "eje de mensaje 3", "[INSERT nombre]"]:
            b = self._good_brief()
            b["pain_points"] = [placeholder]
            r = vp.validate_brief(b)
            assert not r.passed

    def test_editorial_text_blocked(self):
        b = self._good_brief()
        b["executive_summary"] = "Esta sección debe personalizarse con información del municipio real."
        r = vp.validate_brief(b)
        assert not r.passed
        assert any(i.code == "EDITORIAL_TEXT" for i in r.blocking_issues)

    def test_empty_required_field_blocked(self):
        b = self._good_brief()
        b["messaging_axes"] = []
        b["pain_points"] = []
        r = vp.validate_brief(b)
        assert not r.passed

    def test_unqualified_estimated_claims_warning(self):
        b = self._good_brief()
        b["executive_summary"] = (
            "El 32.1% vive en pobreza. El 41.2% tiene informalidad. "
            "El 28.3% carece de salud. El 18.7% tiene rezago. "
            "El 12.9% inseguridad. El 9.8% sin agua."
        )
        r = vp.validate_brief(b, can_cite_as_municipal=False)
        warning_codes = {i.code for i in r.warning_issues}
        assert "UNQUALIFIED_ESTIMATED_CLAIMS" in warning_codes

    def test_rule_version_present(self):
        assert vp.RULE_VERSION == "1.1.0"


class TestSpeechValidation:
    def _long_speech(self, minutes: int = 3) -> dict:
        target = int(130 * minutes * 1.15)
        text = (
            "Ciudadanas y ciudadanos de Apizaco, hoy vengo a hablar de trabajo digno "
            "y justicia social para todas las familias que se levantan temprano a trabajar. "
        ) * (target // 22 + 1)
        return {
            "opening": text[:450],
            "body_sections": [{"title": "Diagnóstico", "content": text, "persuasion_technique": "validación"}],
            "closing": text[:260],
            "full_text": text,
        }

    def test_long_enough_speech_passes(self):
        r = vp.validate_speech(self._long_speech(3), target_minutes=3)
        assert r.passed, f"Blocking: {[i.description for i in r.blocking_issues]}"

    def test_too_short_blocked(self):
        r = vp.validate_speech({"full_text": "Hola Apizaco."}, target_minutes=15)
        assert not r.passed
        assert any(i.code == "SPEECH_TOO_SHORT" for i in r.blocking_issues)

    def test_too_short_message_has_word_targets(self):
        r = vp.validate_speech({"full_text": "Hola."}, target_minutes=15)
        issue = next(i for i in r.blocking_issues if i.code == "SPEECH_TOO_SHORT")
        assert "palabras" in issue.description

    def test_duration_mismatch_detected_when_metadata_present(self):
        s = self._long_speech(8)
        s["duration_verification"] = {
            "target_minutes": 8,
            "estimated_minutes": 3.2,
            "lower_bound_minutes": 6.0,
            "upper_bound_minutes": 10.0,
            "within_tolerance": False,
            "delta_minutes": -4.8,
            "delta_pct": -0.6,
            "words_per_minute": 130,
            "actual_word_count": 420,
        }
        r = vp.validate_speech(s, target_minutes=8)
        issue = next(i for i in r.issues if i.code == "DURATION_MISMATCH")
        assert issue.severity == "blocking"

    def test_duration_mismatch_warning_when_too_long(self):
        s = self._long_speech(4)
        s["duration_verification"] = {
            "target_minutes": 4,
            "estimated_minutes": 7.5,
            "lower_bound_minutes": 3.0,
            "upper_bound_minutes": 5.0,
            "within_tolerance": False,
            "delta_minutes": 3.5,
            "delta_pct": 0.875,
            "words_per_minute": 130,
            "actual_word_count": 975,
        }
        r = vp.validate_speech(s, target_minutes=4)
        issue = next(i for i in r.issues if i.code == "DURATION_MISMATCH")
        assert issue.severity == "warning"

    def test_placeholder_in_speech_blocked(self):
        s = self._long_speech(3)
        s["full_text"] = s["full_text"] + " hallazgo 1 accionable"
        r = vp.validate_speech(s, target_minutes=3)
        assert not r.passed
        assert any("PLACEHOLDER" in i.code for i in r.blocking_issues)

    def test_editorial_text_blocked(self):
        s = self._long_speech(3)
        s["full_text"] = s["full_text"] + " Esta sección debe personalizarse con datos reales."
        r = vp.validate_speech(s, target_minutes=3)
        editorial = [i for i in r.issues if "EDITORIAL" in i.code]
        assert len(editorial) > 0

    def test_paragraph_duplication_detected(self):
        dup = "Los ciudadanos de Apizaco merecen un gobierno honesto que respete sus derechos fundamentales siempre."
        full = "\n\n".join([dup] * 7)
        r = vp.validate_speech({"full_text": full, "opening": dup, "body_sections": [], "closing": dup}, target_minutes=1)
        dup_issues = [i for i in r.issues if i.code == "PARAGRAPH_DUPLICATION"]
        assert len(dup_issues) > 0

    def test_empty_opening_blocked(self):
        s = self._long_speech(3)
        s["opening"] = "Hi."
        r = vp.validate_speech(s, target_minutes=3)
        opening_issues = [i for i in r.blocking_issues if i.field == "opening"]
        assert len(opening_issues) > 0

    def test_expansion_fragment_blocked(self):
        s = self._long_speech(3)
        s["full_text"] += " [Expansión programática] más detalles aquí."
        r = vp.validate_speech(s, target_minutes=3)
        assert not r.passed

    def test_validation_report_fields_complete(self):
        r = vp.validate_brief(
            {
                "executive_summary": "Test municipio con datos.",
                "key_findings": [],
                "pain_points": [],
                "messaging_axes": [],
                "recommended_tone": "moderado",
            }
        )
        report = r.to_dict()
        for key in ("passed", "score", "checks_run", "checks_failed", "blocking_count", "warning_count", "issues"):
            assert key in report