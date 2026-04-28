from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.exceptions import SourceTextValidationError

_PAGE_NUMBER_RE = re.compile(r"^\s*(?:p[aá]gina\s+)?\d+\s*(?:de\s*\d+)?\s*$", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[•\-*·▪◦]+\s*")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")
_WORD_RE = re.compile(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]{2,}\b", re.UNICODE)
_SENTENCE_RE = re.compile(r"(?<=[.!?;:])\s+")


@dataclass(slots=True)
class TextSegment:
    index: int
    word_count: int
    preview: str
    text: str


@dataclass(slots=True)
class ExtractedText:
    raw_text: str
    cleaned_text: str
    normalized_text: str
    paragraphs: list[str]
    segments: list[TextSegment]
    word_count: int
    paragraph_count: int
    alpha_ratio: float
    estimated_minutes: float
    prompt_ready_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DurationVerification:
    target_minutes: int
    estimated_minutes: float
    lower_bound_minutes: float
    upper_bound_minutes: float
    within_tolerance: bool
    delta_minutes: float
    delta_pct: float
    words_per_minute: int
    actual_word_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_minutes": self.target_minutes,
            "estimated_minutes": round(self.estimated_minutes, 2),
            "lower_bound_minutes": round(self.lower_bound_minutes, 2),
            "upper_bound_minutes": round(self.upper_bound_minutes, 2),
            "within_tolerance": self.within_tolerance,
            "delta_minutes": round(self.delta_minutes, 2),
            "delta_pct": round(self.delta_pct, 4),
            "words_per_minute": self.words_per_minute,
            "actual_word_count": self.actual_word_count,
        }


@dataclass(slots=True)
class SpeechGenerationPlan:
    target_words: int
    minimum_words: int
    opening_words: int
    closing_words: int
    body_sections: int
    body_section_words: int
    batches: list[list[int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_words": self.target_words,
            "minimum_words": self.minimum_words,
            "opening_words": self.opening_words,
            "closing_words": self.closing_words,
            "body_sections": self.body_sections,
            "body_section_words": self.body_section_words,
            "batches": self.batches,
        }


class TextProcessingService:
    def prepare_source_text(self, raw_text: str, channel: str = "mitin") -> ExtractedText:
        if raw_text is None:
            raise SourceTextValidationError("No se recibió contenido fuente.")

        trimmed = raw_text.strip()
        if not trimmed:
            raise SourceTextValidationError("El texto fuente está vacío.")

        if len(trimmed) > settings.SOURCE_TEXT_MAX_CHARS:
            raise SourceTextValidationError(
                f"El texto fuente supera el máximo permitido de {settings.SOURCE_TEXT_MAX_CHARS:,} caracteres."
            )

        normalized = self._normalize_text(trimmed)
        cleaned = self._clean_text(normalized)
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        words = self._word_count(cleaned)
        alpha_ratio = self._alpha_ratio(cleaned)

        if words < settings.SOURCE_TEXT_MIN_WORDS:
            raise SourceTextValidationError(
                f"El texto fuente es demasiado corto ({words} palabras). Mínimo: {settings.SOURCE_TEXT_MIN_WORDS}."
            )
        if alpha_ratio < settings.SOURCE_TEXT_MIN_ALPHA_RATIO:
            raise SourceTextValidationError(
                "El texto extraído contiene demasiado ruido o caracteres no lingüísticos."
            )
        if len(paragraphs) == 0:
            raise SourceTextValidationError("No se detectaron párrafos útiles en el texto fuente.")

        segments = self.segment_text(cleaned)
        prompt_ready_text = self._build_prompt_ready_text(segments)
        estimated_minutes = self.estimate_duration(cleaned, channel=channel)

        return ExtractedText(
            raw_text=raw_text,
            cleaned_text=cleaned,
            normalized_text=normalized,
            paragraphs=paragraphs,
            segments=segments,
            word_count=words,
            paragraph_count=len(paragraphs),
            alpha_ratio=alpha_ratio,
            estimated_minutes=estimated_minutes,
            prompt_ready_text=prompt_ready_text,
            metadata={
                "segments_count": len(segments),
                "prompt_ready_word_count": self._word_count(prompt_ready_text),
                "cleaned_char_count": len(cleaned),
            },
        )

    def segment_text(self, text: str, max_words: int | None = None, overlap_words: int | None = None) -> list[TextSegment]:
        max_words = max_words or settings.SOURCE_TEXT_SEGMENT_WORDS
        overlap_words = overlap_words if overlap_words is not None else settings.SOURCE_TEXT_SEGMENT_OVERLAP_WORDS

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        segments: list[TextSegment] = []
        buffer: list[str] = []
        buffer_words = 0
        seg_idx = 1

        for paragraph in paragraphs:
            paragraph_words = self._word_count(paragraph)
            if buffer and buffer_words + paragraph_words > max_words:
                segment_text = "\n\n".join(buffer).strip()
                segments.append(self._make_segment(seg_idx, segment_text))
                seg_idx += 1

                carry_words = max(0, overlap_words)
                carry_text = self._tail_words(segment_text, carry_words)
                buffer = [carry_text] if carry_text else []
                buffer_words = self._word_count(carry_text)

            buffer.append(paragraph)
            buffer_words += paragraph_words

        if buffer:
            segment_text = "\n\n".join(buffer).strip()
            segments.append(self._make_segment(seg_idx, segment_text))

        return segments

    def estimate_duration(self, text: str, channel: str = "mitin") -> float:
        words = self._word_count(text)
        wpm = self._words_per_minute(channel)
        if words <= 0:
            return 0.0
        return words / max(1, wpm)

    def verify_duration(self, text: str, target_minutes: int, channel: str = "mitin") -> DurationVerification:
        actual_words = self._word_count(text)
        wpm = self._words_per_minute(channel)
        estimated_minutes = actual_words / max(1, wpm)
        tolerance = max(
            settings.SPEECH_DURATION_TOLERANCE_MINUTES,
            target_minutes * settings.SPEECH_DURATION_TOLERANCE_PCT,
        )
        lower = max(0.0, target_minutes - tolerance)
        upper = target_minutes + tolerance
        delta = estimated_minutes - target_minutes
        delta_pct = delta / max(1.0, float(target_minutes))
        return DurationVerification(
            target_minutes=target_minutes,
            estimated_minutes=estimated_minutes,
            lower_bound_minutes=lower,
            upper_bound_minutes=upper,
            within_tolerance=lower <= estimated_minutes <= upper,
            delta_minutes=delta,
            delta_pct=delta_pct,
            words_per_minute=wpm,
            actual_word_count=actual_words,
        )

    def build_generation_plan(self, duration_minutes: int) -> SpeechGenerationPlan:
        target_words = max(260, duration_minutes * settings.SPEECH_WORDS_PER_MINUTE)
        minimum_words = int(target_words * settings.SPEECH_MIN_WORDS_FACTOR)

        opening_ratio = 0.12 if duration_minutes <= 10 else 0.1
        closing_ratio = 0.1 if duration_minutes <= 10 else 0.08
        opening_words = max(settings.SPEECH_OPENING_WORDS, int(target_words * opening_ratio))
        closing_words = max(settings.SPEECH_CLOSING_WORDS, int(target_words * closing_ratio))

        remaining = max(220, target_words - opening_words - closing_words)
        section_hint = max(
            settings.SPEECH_DEFAULT_BODY_SECTIONS,
            int(math.ceil(duration_minutes / 4.5)),
        )
        body_sections = max(2, min(settings.SPEECH_LONG_FORM_SECTION_CAP, section_hint))
        body_section_words = max(220, int(math.ceil(remaining / max(1, body_sections))))

        batch_size = max(1, settings.SPEECH_LONG_FORM_BATCH_SIZE)
        batches = [
            list(range(start, min(body_sections, start + batch_size) + 1))
            for start in range(1, body_sections + 1, batch_size)
        ]

        return SpeechGenerationPlan(
            target_words=target_words,
            minimum_words=minimum_words,
            opening_words=opening_words,
            closing_words=closing_words,
            body_sections=body_sections,
            body_section_words=body_section_words,
            batches=batches,
        )

    def _normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", " ")
        return text

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        lines = [self._clean_line(line) for line in text.split("\n")]
        lines = self._drop_repeated_headers(lines)

        cleaned_lines: list[str] = []
        previous_blank = False
        for line in lines:
            if not line:
                if not previous_blank:
                    cleaned_lines.append("")
                previous_blank = True
                continue
            cleaned_lines.append(line)
            previous_blank = False

        cleaned = "\n".join(cleaned_lines)
        cleaned = _MULTI_NL_RE.sub("\n\n", cleaned)
        cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        return cleaned.strip()

    def _clean_line(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        if line.startswith("```"):
            return ""
        if line.lower() == "json":
            return ""
        if _PAGE_NUMBER_RE.match(line):
            return ""
        line = _BULLET_RE.sub("", line)
        line = _WHITESPACE_RE.sub(" ", line)
        if len(line) <= 2 and not any(ch.isalpha() for ch in line):
            return ""
        return line.strip("-–— ")

    def _drop_repeated_headers(self, lines: list[str]) -> list[str]:
        counts: dict[str, int] = {}
        normalized_lines = [self._header_key(line) for line in lines if line.strip()]
        for key in normalized_lines:
            counts[key] = counts.get(key, 0) + 1

        result: list[str] = []
        for line in lines:
            if not line.strip():
                result.append(line)
                continue
            key = self._header_key(line)
            if counts.get(key, 0) >= 3 and len(key.split()) <= 8:
                continue
            result.append(line)
        return result

    def _header_key(self, line: str) -> str:
        line = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", line.lower()).strip()

    def _build_prompt_ready_text(self, segments: list[TextSegment]) -> str:
        budget = settings.SOURCE_TEXT_PROMPT_BUDGET_WORDS
        if not segments:
            return ""

        selected: list[TextSegment] = []
        if sum(seg.word_count for seg in segments) <= budget:
            selected = segments
        else:
            candidate_indices = [0, 1, len(segments) // 2, len(segments) - 2, len(segments) - 1]
            seen = set()
            for idx in candidate_indices:
                if 0 <= idx < len(segments) and idx not in seen:
                    selected.append(segments[idx])
                    seen.add(idx)
            selected.sort(key=lambda seg: seg.index)

            total = 0
            trimmed: list[TextSegment] = []
            for seg in selected:
                if total >= budget:
                    break
                trimmed_text = self._truncate_words(seg.text, max(120, min(seg.word_count, budget - total)))
                trimmed_seg = self._make_segment(seg.index, trimmed_text)
                trimmed.append(trimmed_seg)
                total += trimmed_seg.word_count
            selected = trimmed

        blocks = []
        for seg in selected:
            blocks.append(f"[TRAMO {seg.index} | {seg.word_count} palabras]\n{seg.text}")
        return "\n\n".join(blocks).strip()

    def _make_segment(self, index: int, text: str) -> TextSegment:
        preview = self._truncate_words(text.replace("\n", " "), 24)
        return TextSegment(
            index=index,
            word_count=self._word_count(text),
            preview=preview,
            text=text.strip(),
        )

    def _tail_words(self, text: str, words: int) -> str:
        if words <= 0:
            return ""
        items = text.split()
        if len(items) <= words:
            return text.strip()
        return " ".join(items[-words:]).strip()

    def _truncate_words(self, text: str, words: int) -> str:
        items = text.split()
        if len(items) <= words:
            return text.strip()
        return " ".join(items[:words]).strip()

    def _word_count(self, text: str) -> int:
        return len(_WORD_RE.findall(text or ""))

    def _alpha_ratio(self, text: str) -> float:
        meaningful = [c for c in text if not c.isspace()]
        if not meaningful:
            return 0.0
        alpha = sum(1 for c in meaningful if c.isalpha())
        return alpha / len(meaningful)

    def _words_per_minute(self, channel: str) -> int:
        low = (channel or "mitin").strip().lower()
        channel_map = {
            "mitin": 120,
            "plaza pública": 120,
            "debate": 145,
            "entrevista": 140,
            "radio": 135,
            "televisión": 130,
            "tv": 130,
            "video": 128,
            "redes": 124,
            "asamblea": 122,
        }
        return channel_map.get(low, settings.SPEECH_WORDS_PER_MINUTE)


text_processing_service = TextProcessingService()