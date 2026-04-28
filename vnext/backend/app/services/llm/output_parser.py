from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_BRIEF_REQUIRED_FIELDS = {
    "summary",
    "key_findings",
    "pain_points",
    "messaging_axes",
    "recommended_tone",
}

_SPEECH_REQUIRED_FIELDS = {
    "opening",
    "body_sections",
    "closing",
    "full_text",
}

_REVIEW_REQUIRED_FIELDS = {
    "overall_score",
    "strengths",
    "weaknesses",
    "improvement_suggestions",
}

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


class OutputParser:
    def parse_json(self, content: str) -> tuple[dict[str, Any], bool]:
        if not content or not content.strip():
            return {}, False

        raw = content.strip()

        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}, isinstance(data, dict)
        except json.JSONDecodeError:
            pass

        match = _JSON_BLOCK_RE.search(raw)
        if match:
            try:
                data = json.loads(match.group(1))
                return data if isinstance(data, dict) else {}, isinstance(data, dict)
            except json.JSONDecodeError:
                pass

        extracted = self._extract_first_json_object(raw)
        if extracted:
            try:
                data = json.loads(extracted)
                return data if isinstance(data, dict) else {}, isinstance(data, dict)
            except json.JSONDecodeError:
                pass

        logger.warning("No se pudo parsear JSON de la respuesta LLM. Longitud=%d", len(raw))
        return {}, False

    def _extract_first_json_object(self, text: str) -> str:
        start = text.find("{")
        if start == -1:
            return ""

        depth = 0
        in_string = False
        escape_next = False

        for i, ch in enumerate(text[start:], start=start):
            if escape_next:
                escape_next = False
                continue

            if ch == "\\" and in_string:
                escape_next = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return ""

    def validate_and_normalize_brief(
        self,
        data: dict[str, Any],
        territory_name: str = "Tlaxcala",
    ) -> dict[str, Any]:
        if not isinstance(data, dict):
            data = {}

        missing = _BRIEF_REQUIRED_FIELDS - set(data.keys())
        if missing:
            logger.warning("Brief LLM incompleto. Campos faltantes: %s", sorted(missing))

        defaults: dict[str, Any] = {
            "summary": f"Brief territorial para {territory_name}.",
            "territorial_context": "",
            "key_findings": [],
            "audience_insights": {
                "dominant_profile": "No determinado",
                "key_segments": [],
                "engagement_level": "medio",
                "media_consumption": [],
            },
            "pain_points": [],
            "messaging_axes": [],
            "strategic_opportunities": [],
            "risk_flags": [],
            "recommended_tone": "moderado",
            "emotional_hooks": [],
            "rational_hooks": [],
            "call_to_action_lines": [],
            "framing_suggestions": [],
            "candidate_positioning": "",
            "priority_promises": [],
        }

        normalized = {**defaults, **data}
        normalized["summary"] = self._normalize_text(normalized.get("summary"))
        normalized["territorial_context"] = self._normalize_text(normalized.get("territorial_context"))
        normalized["candidate_positioning"] = self._normalize_text(normalized.get("candidate_positioning"))
        normalized["recommended_tone"] = self._normalize_text(normalized.get("recommended_tone")) or "moderado"

        normalized["key_findings"] = self._normalize_string_list(normalized.get("key_findings"))
        normalized["pain_points"] = self._normalize_string_list(normalized.get("pain_points"))
        normalized["strategic_opportunities"] = self._normalize_string_list(normalized.get("strategic_opportunities"))
        normalized["risk_flags"] = self._normalize_string_list(normalized.get("risk_flags"))
        normalized["emotional_hooks"] = self._normalize_string_list(normalized.get("emotional_hooks"))
        normalized["rational_hooks"] = self._normalize_string_list(normalized.get("rational_hooks"))
        normalized["call_to_action_lines"] = self._normalize_string_list(normalized.get("call_to_action_lines"))
        normalized["priority_promises"] = self._normalize_string_list(normalized.get("priority_promises"))

        axes = normalized.get("messaging_axes") or []
        normalized_axes: list[dict[str, Any]] = []
        for ax in axes:
            if isinstance(ax, str):
                normalized_axes.append(
                    {
                        "axis": self._normalize_text(ax),
                        "message": self._normalize_text(ax),
                        "rationale": "",
                        "sample_phrase": "",
                    }
                )
            elif isinstance(ax, dict):
                normalized_axes.append(
                    {
                        "axis": self._normalize_text(ax.get("axis")),
                        "message": self._normalize_text(ax.get("message") or ax.get("sample_phrase")),
                        "rationale": self._normalize_text(ax.get("rationale")),
                        "sample_phrase": self._normalize_text(ax.get("sample_phrase")),
                    }
                )
        normalized["messaging_axes"] = [ax for ax in normalized_axes if ax.get("axis") or ax.get("message")]

        framings = normalized.get("framing_suggestions") or []
        normalized_framings: list[dict[str, Any]] = []
        for fr in framings:
            if isinstance(fr, str):
                normalized_framings.append(
                    {
                        "frame": self._normalize_text(fr),
                        "description": "",
                        "example": "",
                    }
                )
            elif isinstance(fr, dict):
                normalized_framings.append(
                    {
                        "frame": self._normalize_text(fr.get("frame")),
                        "description": self._normalize_text(fr.get("description")),
                        "example": self._normalize_text(fr.get("example")),
                    }
                )
        normalized["framing_suggestions"] = [fr for fr in normalized_framings if fr.get("frame")]

        if not isinstance(normalized.get("audience_insights"), dict):
            normalized["audience_insights"] = defaults["audience_insights"]

        return normalized

    def validate_and_normalize_speech(
        self,
        data: dict[str, Any],
        channel: str = "mitin",
    ) -> dict[str, Any]:
        if not isinstance(data, dict):
            data = {}

        missing = _SPEECH_REQUIRED_FIELDS - set(data.keys())
        if missing:
            logger.warning("Speech LLM incompleto. Campos faltantes: %s", sorted(missing))

        defaults: dict[str, Any] = {
            "title": "Discurso político",
            "speech_objective": "",
            "target_audience": "",
            "estimated_duration_minutes": None,
            "estimated_word_count": None,
            "opening": "",
            "body_sections": [],
            "local_references": [],
            "emotional_hooks": [],
            "rational_hooks": [],
            "closing": "",
            "full_text": "",
            "adaptation_notes": [],
            "improvements_made": [],
            "duration_verification": {},
            "generation_plan": {},
            "source_processing": {},
        }

        normalized = {**defaults, **data}
        normalized["title"] = self._normalize_text(normalized.get("title")) or "Discurso político"
        normalized["speech_objective"] = self._normalize_text(normalized.get("speech_objective"))
        normalized["target_audience"] = self._normalize_text(normalized.get("target_audience"))
        normalized["opening"] = self._normalize_text(normalized.get("opening"))
        normalized["closing"] = self._normalize_text(normalized.get("closing"))
        normalized["local_references"] = self._normalize_string_list(normalized.get("local_references"))
        normalized["emotional_hooks"] = self._normalize_string_list(normalized.get("emotional_hooks"))
        normalized["rational_hooks"] = self._normalize_string_list(normalized.get("rational_hooks"))
        normalized["adaptation_notes"] = self._normalize_string_list(normalized.get("adaptation_notes"))
        normalized["improvements_made"] = self._normalize_string_list(normalized.get("improvements_made"))

        sections = normalized.get("body_sections") or []
        normalized_sections: list[dict[str, str]] = []
        for idx, sec in enumerate(sections, start=1):
            if isinstance(sec, str):
                content = self._normalize_text(sec)
                if content:
                    normalized_sections.append(
                        {
                            "title": f"Sección {idx}",
                            "content": content,
                            "persuasion_technique": "",
                        }
                    )
                continue

            if isinstance(sec, dict):
                title = self._normalize_text(sec.get("title")) or f"Sección {idx}"
                content = self._normalize_text(sec.get("content"))
                technique = self._normalize_text(sec.get("persuasion_technique"))
                if content:
                    normalized_sections.append(
                        {
                            "title": title,
                            "content": content,
                            "persuasion_technique": technique,
                        }
                    )
        normalized["body_sections"] = normalized_sections

        full_text = self._normalize_text(normalized.get("full_text"))
        if not full_text:
            parts: list[str] = []
            if normalized["opening"]:
                parts.append(normalized["opening"])
            for section in normalized["body_sections"]:
                if section.get("title"):
                    parts.append(section["title"])
                if section.get("content"):
                    parts.append(section["content"])
            if normalized["closing"]:
                parts.append(normalized["closing"])
            full_text = "\n\n".join([p for p in parts if p.strip()])

        normalized["full_text"] = self._normalize_text(full_text)

        if normalized["estimated_word_count"] in (None, "", 0):
            normalized["estimated_word_count"] = len(normalized["full_text"].split())

        if normalized["estimated_duration_minutes"] in (None, "", 0):
            wpm = self._words_per_minute(channel)
            normalized["estimated_duration_minutes"] = round(
                normalized["estimated_word_count"] / max(1, wpm),
                2,
            )

        if not isinstance(normalized.get("duration_verification"), dict):
            normalized["duration_verification"] = {}
        if not isinstance(normalized.get("generation_plan"), dict):
            normalized["generation_plan"] = {}
        if not isinstance(normalized.get("source_processing"), dict):
            normalized["source_processing"] = {}

        return normalized

    def validate_and_normalize_review(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            data = {}

        missing = _REVIEW_REQUIRED_FIELDS - set(data.keys())
        if missing:
            logger.warning("Review LLM incompleto. Campos faltantes: %s", sorted(missing))

        defaults: dict[str, Any] = {
            "overall_score": 5.0,
            "clarity_score": 5.0,
            "persuasion_score": 5.0,
            "territorial_alignment_score": 5.0,
            "coherence_score": 5.0,
            "strengths": [],
            "weaknesses": [],
            "territorial_gaps": [],
            "tone_assessment": "No evaluado",
            "risk_flags": [],
            "improvement_suggestions": [],
            "revised_closing": None,
        }

        normalized = {**defaults, **data}
        for score_field in (
            "overall_score",
            "clarity_score",
            "persuasion_score",
            "territorial_alignment_score",
            "coherence_score",
        ):
            normalized[score_field] = self._normalize_score(normalized.get(score_field))

        normalized["strengths"] = self._normalize_string_list(normalized.get("strengths"))
        normalized["weaknesses"] = self._normalize_string_list(normalized.get("weaknesses"))
        normalized["territorial_gaps"] = self._normalize_string_list(normalized.get("territorial_gaps"))
        normalized["risk_flags"] = self._normalize_string_list(normalized.get("risk_flags"))
        normalized["improvement_suggestions"] = self._normalize_string_list(normalized.get("improvement_suggestions"))
        normalized["tone_assessment"] = self._normalize_text(normalized.get("tone_assessment")) or "No evaluado"
        normalized["revised_closing"] = self._normalize_text(normalized.get("revised_closing")) or None

        return normalized

    def _normalize_score(self, value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 5.0
        return round(min(10.0, max(0.0, score)), 2)

    def _normalize_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []

        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = self._normalize_text(item)
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = text.strip("`")
        if text.lower().startswith("json\n"):
            text = text[5:]
        text = _WS_RE.sub(" ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = _MULTI_NL_RE.sub("\n\n", text)
        return text.strip()

    def _words_per_minute(self, channel: str) -> int:
        low = (channel or "mitin").strip().lower()
        channel_map = {
            "mitin": 120,
            "plaza pública": 120,
            "discurso_formal": 128,
            "reunion_vecinal": 122,
            "entrevista": 140,
            "radio": 135,
            "televisión": 130,
            "tv": 130,
            "video": 128,
            "video_redes": 124,
            "redes": 124,
            "debate": 145,
            "asamblea": 122,
        }
        return channel_map.get(low, 130)


output_parser = OutputParser()