"""
OutputValidationPipeline — validates ALL LLM output before persistence or serving.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

PLACEHOLDER_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"hallazgo\s+\d+\s+accionable",
        r"dolor\s+ciudadano\s+\d+",
        r"gancho\s+emocional\s+\d+",
        r"referencia\s+territorial\s+\d+",
        r"argumento\s+racional\s+\d+",
        r"oportunidad\s+estratégica\s+\d+",
        r"eje\s+de\s+mensaje\s+\d+",
        r"canal\s+\d+",
        r"fuente\s+\d+",
        r"paso\s+(inmediato\s+)?\d+",
        r"línea\s+de\s+acción\s+\d+",
        r"\[INSERT",
        r"\[NOMBRE",
        r"\[MUNICIPIO",
        r"\[CANDIDATO",
        r"\[EXPANSION",
        r"\[AQUI",
        r"TODO[:：]",
        r"INSTRUCCIÓN[:：]",
        r"nota interna",
        r"nota de redacción",
        r"<placeholder",
        r"lorem ipsum",
        r"texto de ejemplo",
    ]
]

EDITORIAL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE | re.MULTILINE) for p in [
        r"^(aquí|en este punto|nota:|observación:|recuerda que)\b",
        r"(este párrafo|esta sección)\s+(debe|debería|puede|podría)",
        r"ajustar\s+según\s+(el\s+)?contexto",
        r"sustituir\s+por",
        r"modificar\s+si\s+",
        r"personalizar\s+con",
        r"agregar\s+datos\s+específicos",
        r"completar\s+con\s+información",
        r"\[expansión\s+programática\]",
        r"\[desarrollo\s+aquí\]",
        r"en este contexto,?\s+el candidato debería",
        r"técnica\s+de\s+persuasión\s*:",
    ]
]

SECTION_PLACEHOLDER_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^sección\s+\d+$",
        r"^sección$",
        r"^título\s*$",
        r"^desarrollo$",
        r"^\d+$",
    ]
]


@dataclass
class ValidationIssue:
    code: str
    severity: str
    field: Optional[str]
    description: str
    value_excerpt: Optional[str] = None


@dataclass
class ValidationReport:
    passed: bool
    score: float
    checks_run: int
    checks_failed: int
    issues: list[ValidationIssue] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @property
    def warning_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def blocking_count(self) -> int:
        return len(self.blocking_issues)

    @property
    def warning_count_prop(self) -> int:
        return len(self.warning_issues)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "checks_run": self.checks_run,
            "checks_failed": self.checks_failed,
            "blocking_count": len(self.blocking_issues),
            "warning_count": len(self.warning_issues),
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "field": i.field,
                    "description": i.description,
                    "value_excerpt": i.value_excerpt,
                }
                for i in self.issues
            ],
        }


class OutputValidationPipeline:
    RULE_VERSION: str = "1.1.0"

    def validate_brief(self, brief_data: dict, can_cite_as_municipal: bool = True) -> ValidationReport:
        issues: list[ValidationIssue] = []
        checks = 0

        checks += 1
        for req in ("executive_summary", "pain_points", "messaging_axes", "recommended_tone"):
            val = brief_data.get(req)
            if not val or (isinstance(val, list) and len(val) == 0):
                issues.append(ValidationIssue(
                    code="EMPTY_REQUIRED_FIELD",
                    severity="blocking",
                    field=req,
                    description=f"Campo requerido vacío: '{req}'",
                ))

        checks += 1
        for fld in ("executive_summary", "candidate_positioning", "territory_context"):
            text = self._flatten(brief_data.get(fld, ""))
            for ph in self._detect_placeholders(text):
                issues.append(ValidationIssue(
                    code="PLACEHOLDER_DETECTED",
                    severity="blocking",
                    field=fld,
                    description=f"Placeholder literal: '{ph}'",
                    value_excerpt=text[:120],
                ))

        checks += 1
        for list_fld in ("key_findings", "pain_points", "opportunities", "risk_flags"):
            items = brief_data.get(list_fld, []) or []
            for item in items:
                text = self._flatten(item)
                for ph in self._detect_placeholders(text):
                    issues.append(ValidationIssue(
                        code="PLACEHOLDER_IN_LIST",
                        severity="blocking",
                        field=list_fld,
                        description=f"Placeholder en lista '{list_fld}': '{ph}'",
                        value_excerpt=text[:80],
                    ))

        checks += 1
        for fld in ("executive_summary", "candidate_positioning", "territory_context"):
            text = self._flatten(brief_data.get(fld, ""))
            for ed in self._detect_editorial(text):
                issues.append(ValidationIssue(
                    code="EDITORIAL_TEXT",
                    severity="blocking",
                    field=fld,
                    description=f"Texto editorial interno detectado: '{ed[:60]}'",
                ))

        checks += 1
        summary = str(brief_data.get("executive_summary", "") or "")
        words = len(summary.split())
        if words < 8:
            issues.append(ValidationIssue(
                code="INSUFFICIENT_CONTENT",
                severity="blocking",
                field="executive_summary",
                description=f"Resumen ejecutivo muy corto: {words} palabras (mínimo 8).",
            ))

        checks += 1
        if not can_cite_as_municipal:
            all_text = self._flatten(brief_data)
            pct_matches = re.findall(r"\b(\d{1,2}(?:\.\d)?)\s*%", all_text)
            if len(pct_matches) > 5:
                issues.append(ValidationIssue(
                    code="UNQUALIFIED_ESTIMATED_CLAIMS",
                    severity="warning",
                    field=None,
                    description=(
                        f"Brief cita {len(pct_matches)} porcentajes precisos pero datos son estimados. "
                        "Verificar que disclaimer metodológico sea visible."
                    ),
                ))

        checks += 1
        axes = brief_data.get("messaging_axes", []) or []
        for i, ax in enumerate(axes):
            if isinstance(ax, dict):
                msg = ax.get("message", "")
                if len(str(msg).split()) < 5:
                    issues.append(ValidationIssue(
                        code="EMPTY_AXIS_MESSAGE",
                        severity="warning",
                        field="messaging_axes",
                        description=f"Eje de mensaje #{i + 1} demasiado corto: '{msg}'",
                    ))

        return self._build_report(issues, checks)

    def validate_speech(
        self,
        speech_data: dict,
        target_minutes: int,
        words_per_minute: int = 130,
        can_cite_as_municipal: bool = True,
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        checks = 0
        target_words = target_minutes * words_per_minute
        min_words = int(target_words * settings.SPEECH_MIN_WORDS_FACTOR)

        full_text = self._build_full_text(speech_data)
        actual_words = len(full_text.split())

        checks += 1
        if actual_words < min_words:
            issues.append(ValidationIssue(
                code="SPEECH_TOO_SHORT",
                severity="blocking",
                field="full_text",
                description=(
                    f"Discurso de {actual_words:,} palabras. "
                    f"Para {target_minutes} min se requieren ≥{min_words:,} palabras "
                    f"({actual_words / max(target_words, 1) * 100:.0f}% del objetivo). "
                    f"Duración real estimada: {actual_words / words_per_minute:.1f} min."
                ),
                value_excerpt=f"target={target_words}, actual={actual_words}, min={min_words}",
            ))

        checks += 1
        duration_meta = speech_data.get("duration_verification") or {}
        estimated_minutes = duration_meta.get("estimated_minutes")
        lower_bound = duration_meta.get("lower_bound_minutes")
        upper_bound = duration_meta.get("upper_bound_minutes")
        within_tolerance = duration_meta.get("within_tolerance")
        if estimated_minutes is None:
            estimated_minutes = actual_words / max(1, words_per_minute)
        if lower_bound is None or upper_bound is None:
            tolerance = max(
                settings.SPEECH_DURATION_TOLERANCE_MINUTES,
                target_minutes * settings.SPEECH_DURATION_TOLERANCE_PCT,
            )
            lower_bound = max(0.0, target_minutes - tolerance)
            upper_bound = target_minutes + tolerance
            within_tolerance = lower_bound <= estimated_minutes <= upper_bound
        if within_tolerance is False:
            severity = "blocking" if estimated_minutes < lower_bound else "warning"
            issues.append(ValidationIssue(
                code="DURATION_MISMATCH",
                severity=severity,
                field="duration_verification",
                description=(
                    f"Duración estimada fuera de tolerancia. Objetivo: {target_minutes} min; "
                    f"estimada: {estimated_minutes:.1f} min; rango aceptable: {lower_bound:.1f}-{upper_bound:.1f} min."
                ),
            ))

        checks += 1
        for ph in self._detect_placeholders(full_text):
            issues.append(ValidationIssue(
                code="PLACEHOLDER_IN_SPEECH",
                severity="blocking",
                field="full_text",
                description=f"Placeholder literal en discurso: '{ph}'",
            ))

        checks += 1
        paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 60]
        seen: list[str] = []
        for para in paragraphs:
            for prev in seen:
                if self._jaccard(para, prev) > 0.72:
                    issues.append(ValidationIssue(
                        code="PARAGRAPH_DUPLICATION",
                        severity="blocking",
                        field="full_text",
                        description="Párrafo duplicado o casi idéntico detectado.",
                        value_excerpt=para[:100],
                    ))
                    break
            seen.append(para)

        checks += 1
        for sec in speech_data.get("body_sections", []) or []:
            if isinstance(sec, dict):
                title = str(sec.get("title", "") or "")
                for ptn in SECTION_PLACEHOLDER_PATTERNS:
                    if ptn.match(title.strip()):
                        issues.append(ValidationIssue(
                            code="SECTION_TITLE_PLACEHOLDER",
                            severity="warning",
                            field="body_sections",
                            description=f"Título de sección parece placeholder: '{title}'",
                        ))

        checks += 1
        for i, sec in enumerate(speech_data.get("body_sections", []) or []):
            if isinstance(sec, dict):
                content = str(sec.get("content", "") or "")
                if len(content.split()) < 20:
                    issues.append(ValidationIssue(
                        code="EMPTY_SPEECH_SECTION",
                        severity="warning",
                        field="body_sections",
                        description=f"Sección #{i + 1} '{sec.get('title', '')}' muy corta ({len(content.split())} palabras).",
                    ))

        checks += 1
        for fld in ("opening", "closing"):
            text = str(speech_data.get(fld, "") or "")
            if len(text.split()) < 15:
                issues.append(ValidationIssue(
                    code="EMPTY_SPEECH_FIELD",
                    severity="blocking",
                    field=fld,
                    description=f"'{fld}' del discurso muy corto ({len(text.split())} palabras).",
                ))

        checks += 1
        for ed in self._detect_editorial(full_text):
            issues.append(ValidationIssue(
                code="EDITORIAL_TEXT_IN_SPEECH",
                severity="blocking",
                field="full_text",
                description=f"Texto editorial: '{ed[:60]}'",
            ))

        checks += 1
        if not can_cite_as_municipal:
            pct_matches = re.findall(r"\b(\d{1,2}(?:\.\d)?)\s*%", full_text)
            if len(pct_matches) > 4:
                issues.append(ValidationIssue(
                    code="PRECISE_CLAIM_ON_ESTIMATED_DATA",
                    severity="warning",
                    field="full_text",
                    description=(
                        f"Discurso cita {len(pct_matches)} porcentajes precisos, "
                        "pero los datos son estimaciones regionales. Revisar redacción."
                    ),
                ))

        return self._build_report(issues, checks)

    def validate_analysis(self, report_data: dict, kpi_data: dict) -> ValidationReport:
        issues: list[ValidationIssue] = []
        checks = 0

        checks += 1
        for req in ("executive_summary", "critical_needs"):
            val = report_data.get(req)
            if not val or (isinstance(val, list) and len(val) == 0):
                issues.append(ValidationIssue(
                    code="EMPTY_ANALYSIS_FIELD",
                    severity="blocking",
                    field=req,
                    description=f"Campo requerido vacío en análisis: '{req}'",
                ))

        checks += 1
        summary = str(report_data.get("executive_summary", "") or "")
        if len(summary.split()) < 15:
            issues.append(ValidationIssue(
                code="SHORT_ANALYSIS_SUMMARY",
                severity="blocking",
                field="executive_summary",
                description=f"Resumen ejecutivo del análisis muy corto: {len(summary.split())} palabras.",
            ))

        checks += 1
        for ph in self._detect_placeholders(summary):
            issues.append(ValidationIssue(
                code="PLACEHOLDER_IN_ANALYSIS",
                severity="blocking",
                field="executive_summary",
                description=f"Placeholder en análisis: '{ph}'",
            ))

        return self._build_report(issues, checks)

    def _detect_placeholders(self, text: str) -> list[str]:
        found = []
        for ptn in PLACEHOLDER_PATTERNS:
            matches = ptn.findall(text)
            found.extend(matches)
        return found

    def _detect_editorial(self, text: str) -> list[str]:
        found = []
        for ptn in EDITORIAL_PATTERNS:
            for m in ptn.finditer(text):
                found.append(m.group(0))
        return found

    def _flatten(self, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return " ".join(self._flatten(v) for v in value)
        if isinstance(value, dict):
            return " ".join(self._flatten(v) for v in value.values())
        return str(value) if value else ""

    def _build_full_text(self, speech_data: dict) -> str:
        full = speech_data.get("full_text", "") or ""
        if full and len(full.split()) > 50:
            return full
        parts = []
        opening = speech_data.get("opening", "")
        if opening:
            parts.append(str(opening))
        for sec in speech_data.get("body_sections", []) or []:
            if isinstance(sec, dict):
                parts.append(str(sec.get("content", "") or ""))
            elif isinstance(sec, str):
                parts.append(sec)
        closing = speech_data.get("closing", "")
        if closing:
            parts.append(str(closing))
        return "\n\n".join(p for p in parts if p.strip())

    def _jaccard(self, a: str, b: str) -> float:
        sa = set(a.lower().split())
        sb = set(b.lower().split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _build_report(self, issues: list[ValidationIssue], checks: int) -> ValidationReport:
        blocking = [i for i in issues if i.severity == "blocking"]
        n_blocked = len(blocking)
        n_warn = len([i for i in issues if i.severity == "warning"])
        score = max(0.0, 1.0 - n_blocked * 0.25 - n_warn * 0.05)
        return ValidationReport(
            passed=n_blocked == 0,
            score=round(score, 2),
            checks_run=checks,
            checks_failed=len(issues),
            issues=issues,
        )


output_validator = OutputValidationPipeline()