from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationBlockedError
from app.db.repositories.speech_repo import SpeechRepository
from app.models.db_models import SpeechRunDB
from app.models.schemas import SpeechRunRequest
from app.services.analysis.orchestrator import analysis_orchestrator
from app.services.evidence.orchestrator import evidence_orchestrator
from app.services.llm.groq_client import GroqClient, LLMProviderError
from app.services.llm.output_parser import output_parser
from app.services.prompts.base import PromptContext
from app.services.prompts.builders import PromptBuilder
from app.services.speech.text_processing import (
    ExtractedText,
    SpeechGenerationPlan,
    text_processing_service,
)
from app.services.territory.repository import TerritoryRepository
from app.services.validation.pipeline import output_validator

logger = logging.getLogger(__name__)

_prompt_builder = PromptBuilder()
_groq = GroqClient()


def _speech_param_hash(request: SpeechRunRequest) -> str:
    payload = {
        "municipality_id": request.municipality_id,
        "speech_goal": (request.speech_goal or "").strip().lower(),
        "audience": (request.audience or "").strip().lower(),
        "tone": request.tone or "",
        "channel": request.channel or "",
        "duration_minutes": request.duration_minutes or 10,
        "speech_type": "adaptation" if request.source_text else "creation",
        "priority_topics": sorted(list(request.priority_topics or [])),
        "avoid_topics": sorted(list(request.avoid_topics or [])),
        "electoral_moment": request.electoral_moment or "",
        "source_text_hash": hashlib.sha256((request.source_text or "").encode()).hexdigest()[:12],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


class SpeechOrchestrator:
    async def run(
        self,
        request: SpeechRunRequest,
        db: AsyncSession,
        force_refresh: bool = False,
    ) -> SpeechRunDB:
        normalized_request, source_processing = self._prepare_request(request)
        speech_repo = SpeechRepository(db)
        param_hash = _speech_param_hash(normalized_request)

        if not force_refresh:
            cached = await speech_repo.get_latest_by_params(normalized_request.municipality_id, param_hash)
            if cached:
                logger.debug("Speech cache hit: %s hash=%s", normalized_request.municipality_id, param_hash)
                return cached

        analysis = await analysis_orchestrator.get_latest(normalized_request.municipality_id, db)
        if not analysis:
            logger.info("No analysis for %s — auto-generating", normalized_request.municipality_id)
            analysis = await analysis_orchestrator.run(normalized_request.municipality_id, db)

        evidence = await evidence_orchestrator.get_latest(normalized_request.municipality_id, db)
        can_cite = evidence.can_cite_as_municipal if evidence else False

        territory_text, municipality_name, neighborhood_name = self._build_territory_context(normalized_request, evidence)
        context = self._build_prompt_context(
            normalized_request,
            analysis,
            territory_text,
            municipality_name,
            neighborhood_name,
            source_processing,
        )

        if normalized_request.candidate:
            context.candidate_name = normalized_request.candidate.name
            context.candidate_party = normalized_request.candidate.party
            context.candidate_position = normalized_request.candidate.position
            context.candidate_style = getattr(normalized_request.candidate, "style", None)
            context.candidate_values = list(getattr(normalized_request.candidate, "values", []) or [])

        speech_type = "adaptation" if normalized_request.source_text else "creation"
        plan = text_processing_service.build_generation_plan(normalized_request.duration_minutes)

        ai_generated = False
        total_latency_ms = 0.0
        retry_count = 0

        use_sectioned = self._should_use_sectioned_generation(normalized_request, source_processing)
        if use_sectioned:
            speech_data, generation_latency_ms, retry_count = await self._generate_sectioned_speech(
                request=normalized_request,
                context=context,
                speech_type=speech_type,
                plan=plan,
            )
        else:
            speech_data, generation_latency_ms, retry_count = await self._generate_monolithic_speech(
                request=normalized_request,
                context=context,
                speech_type=speech_type,
                min_words=plan.minimum_words,
                plan=plan,
            )
        total_latency_ms += generation_latency_ms
        ai_generated = True

        speech_data = self._enrich_speech_data(
            speech_data=speech_data,
            context=context,
            request=normalized_request,
            plan=plan,
            source_processing=source_processing,
        )

        speech_data, extra_latency_ms, extra_retry_count = await self._enforce_duration_target(
            request=normalized_request,
            context=context,
            speech_type=speech_type,
            plan=plan,
            speech_data=speech_data,
        )
        total_latency_ms += extra_latency_ms
        retry_count += extra_retry_count

        validation = output_validator.validate_speech(
            speech_data,
            target_minutes=normalized_request.duration_minutes,
            words_per_minute=settings.SPEECH_WORDS_PER_MINUTE,
            can_cite_as_municipal=can_cite,
        )

        if not validation.passed:
            real_blockers = [i for i in validation.blocking_issues if i.code not in {"SPEECH_TOO_SHORT", "DURATION_MISMATCH"}]
            if real_blockers:
                raise ValidationBlockedError(len(real_blockers), real_blockers[0].description)

            speech_data, extra_latency_ms, extra_retry_count = await self._expand_short_sections(
                request=normalized_request,
                context=context,
                speech_data=speech_data,
                missing_words=max(0, plan.minimum_words - len((speech_data.get("full_text") or "").split())),
            )
            total_latency_ms += extra_latency_ms
            retry_count += extra_retry_count
            speech_data = self._enrich_speech_data(
                speech_data=speech_data,
                context=context,
                request=normalized_request,
                plan=plan,
                source_processing=source_processing,
            )
            validation = output_validator.validate_speech(
                speech_data,
                target_minutes=normalized_request.duration_minutes,
                words_per_minute=settings.SPEECH_WORDS_PER_MINUTE,
                can_cite_as_municipal=can_cite,
            )

        if not validation.passed:
            blocking = validation.blocking_issues
            raise ValidationBlockedError(
                len(blocking),
                blocking[0].description if blocking else "Speech blocked by validation",
            )

        full_text = speech_data.get("full_text", "")
        actual_words = len(full_text.split()) if full_text else 0
        duration_meta = speech_data.get("duration_verification") or {}

        run = SpeechRunDB(
            id=str(uuid.uuid4()),
            municipality_id=normalized_request.municipality_id,
            analysis_run_id=analysis.id,
            parameter_hash=param_hash,
            created_at=datetime.now(timezone.utc),
            status="completed",
            speech_type=speech_type,
            parameters={
                "goal": normalized_request.speech_goal,
                "audience": normalized_request.audience,
                "tone": normalized_request.tone,
                "channel": normalized_request.channel,
                "duration_minutes": normalized_request.duration_minutes,
                "municipality_name": municipality_name,
                "neighborhood_name": neighborhood_name,
                "source_processing": source_processing.metadata if source_processing else None,
                "duration_verification": duration_meta,
                "generation_plan": plan.to_dict(),
            },
            speech_data=speech_data,
            target_duration_minutes=normalized_request.duration_minutes,
            target_word_count=plan.target_words,
            actual_word_count=actual_words,
            retry_count=retry_count,
            ai_generated=ai_generated,
            latency_ms=total_latency_ms,
            overall_confidence=evidence.overall_confidence if evidence else 0.0,
            validation_blocked=False,
            validation_passed=validation.passed,
            validation_score=validation.score,
            validation_issues=[i.__dict__ for i in validation.issues],
            validation_rule_version=output_validator.RULE_VERSION,
            model_used=settings.GROQ_MODEL,
        )
        return await speech_repo.save(run)

    async def get_latest(self, municipality_id: str, db: AsyncSession) -> Optional[SpeechRunDB]:
        return await SpeechRepository(db).get_latest_valid(municipality_id)

    def _prepare_request(self, request: SpeechRunRequest) -> tuple[SpeechRunRequest, Optional[ExtractedText]]:
        source_processing: Optional[ExtractedText] = None
        if request.source_text:
            source_processing = text_processing_service.prepare_source_text(
                request.source_text,
                channel=request.channel,
            )
            request = request.model_copy(update={"source_text": source_processing.cleaned_text})
        return request, source_processing

    def _build_territory_context(self, request: SpeechRunRequest, evidence) -> tuple[str, str, str]:
        repo = TerritoryRepository.get_instance()
        municipality = repo.get_municipality(request.municipality_id) or {}
        municipality_name = municipality.get("name", request.municipality_id)

        neighborhood_name = ""
        neighborhood_id = getattr(request, "neighborhood_id", None)
        if neighborhood_id:
            neighborhoods = repo.get_neighborhoods_for(request.municipality_id)
            for n in neighborhoods:
                if n.get("id") == neighborhood_id:
                    neighborhood_name = n.get("name", "")
                    break

        if evidence:
            territory_text = evidence_orchestrator.to_prompt_text(evidence)
        else:
            base_lines = [
                "=== CONTEXTO TERRITORIAL MÍNIMO ===",
                f"Municipio: {municipality_name}",
                f"Municipality ID: {request.municipality_id}",
            ]
            if municipality:
                if municipality.get("region"):
                    base_lines.append(f"Región: {municipality['region']}")
                if municipality.get("profile"):
                    base_lines.append(f"Perfil territorial: {municipality['profile']}")
                if municipality.get("economic_base"):
                    base_lines.append(f"Base económica: {municipality['economic_base']}")
                if municipality.get("notes"):
                    base_lines.append(f"Notas: {municipality['notes']}")
            territory_text = "\n".join(base_lines)

        if neighborhood_name:
            territory_text = f"{territory_text}\n\nZONA / BARRIO OBJETIVO: {neighborhood_name}"

        return territory_text, municipality_name, neighborhood_name

    def _build_prompt_context(
        self,
        request: SpeechRunRequest,
        analysis,
        territory_text: str,
        municipality_name: str,
        neighborhood_name: str,
        source_processing: Optional[ExtractedText],
    ) -> PromptContext:
        prompt_source_text = source_processing.prompt_ready_text if source_processing else request.source_text
        context = PromptContext(
            territory_text=territory_text,
            municipality_name=municipality_name,
            neighborhood_name=neighborhood_name,
            pain_points=self._extract_pain_points(analysis),
            opportunities=self._extract_opportunities(analysis),
            recommended_tone=request.tone,
            speech_goal=request.speech_goal,
            audience=request.audience,
            tone=request.tone,
            channel=request.channel,
            duration_minutes=request.duration_minutes,
            priority_topics=list(request.priority_topics or []),
            avoid_topics=list(request.avoid_topics or []),
            source_text=prompt_source_text,
            electoral_moment=request.electoral_moment,
        )
        return context

    def _should_use_sectioned_generation(
        self,
        request: SpeechRunRequest,
        source_processing: Optional[ExtractedText],
    ) -> bool:
        if request.duration_minutes >= settings.SPEECH_SECTIONED_MIN_MINUTES:
            return True
        if source_processing and source_processing.word_count >= settings.SOURCE_TEXT_SEGMENT_WORDS:
            return True
        return False

    def _enrich_speech_data(
        self,
        speech_data: dict[str, Any],
        context: PromptContext,
        request: SpeechRunRequest,
        plan: SpeechGenerationPlan,
        source_processing: Optional[ExtractedText],
    ) -> dict[str, Any]:
        speech_data = output_parser.validate_and_normalize_speech(speech_data, channel=request.channel)
        full_text = self._join_speech(
            speech_data.get("opening", ""),
            speech_data.get("body_sections", []) or [],
            speech_data.get("closing", ""),
        )
        duration = text_processing_service.verify_duration(
            full_text,
            target_minutes=request.duration_minutes,
            channel=request.channel,
        )
        speech_data["title"] = speech_data.get("title") or self._build_title(context)
        speech_data["speech_objective"] = speech_data.get("speech_objective") or context.speech_goal
        speech_data["target_audience"] = speech_data.get("target_audience") or context.audience
        speech_data["estimated_word_count"] = len(full_text.split())
        speech_data["estimated_duration_minutes"] = round(duration.estimated_minutes, 2)
        speech_data["full_text"] = full_text
        speech_data["local_references"] = speech_data.get("local_references") or self._collect_local_references(context.territory_text)
        speech_data["emotional_hooks"] = speech_data.get("emotional_hooks") or context.pain_points[:3]
        speech_data["rational_hooks"] = speech_data.get("rational_hooks") or context.opportunities[:3]
        speech_data["generation_plan"] = plan.to_dict()
        speech_data["duration_verification"] = duration.to_dict()
        if source_processing:
            speech_data["source_processing"] = {
                "word_count": source_processing.word_count,
                "paragraph_count": source_processing.paragraph_count,
                "segments_count": len(source_processing.segments),
                "estimated_minutes": round(source_processing.estimated_minutes, 2),
                "alpha_ratio": round(source_processing.alpha_ratio, 4),
                "prompt_ready_word_count": source_processing.metadata.get("prompt_ready_word_count", 0),
                "segment_previews": [seg.preview for seg in source_processing.segments[:8]],
            }
            if not speech_data.get("adaptation_notes"):
                speech_data["adaptation_notes"] = [
                    f"Texto fuente limpiado y validado ({source_processing.word_count} palabras).",
                    f"Segmentación aplicada en {len(source_processing.segments)} tramos para preservar contexto.",
                ]
        elif not speech_data.get("adaptation_notes"):
            speech_data["adaptation_notes"] = ["Discurso generado desde contexto territorial y análisis."]
        return speech_data

    async def _generate_monolithic_speech(
        self,
        request: SpeechRunRequest,
        context: PromptContext,
        speech_type: str,
        min_words: int,
        plan: SpeechGenerationPlan,
    ) -> tuple[dict[str, Any], float, int]:
        total_latency_ms = 0.0
        retry_count = 0
        last_error: Optional[Exception] = None
        speech_data: dict[str, Any] | None = None

        for attempt in range(settings.SPEECH_MAX_RETRY_ATTEMPTS + 1):
            t0 = time.monotonic()
            try:
                prompt = (
                    _prompt_builder.build_speech_improver_prompt(context)
                    if speech_type == "adaptation"
                    else _prompt_builder.build_speech_creator_prompt(context)
                )
                if attempt > 0:
                    prompt = self._strengthen_prompt(prompt, min_words=min_words, attempt=attempt)

                resp = await _groq.complete(_prompt_builder.to_llm_request(prompt))
                total_latency_ms += (time.monotonic() - t0) * 1000
                raw, ok = output_parser.parse_json(resp.content)
                if not ok:
                    retry_count = attempt + 1
                    continue

                speech_data = output_parser.validate_and_normalize_speech(raw, channel=request.channel)
                missing_core = [
                    name for name in ("opening", "closing", "full_text", "body_sections")
                    if not speech_data.get(name)
                ]
                if missing_core:
                    sectioned_data, extra_latency_ms, extra_retries = await self._generate_sectioned_speech(
                        request=request,
                        context=context,
                        speech_type=speech_type,
                        plan=plan,
                    )
                    return sectioned_data, total_latency_ms + extra_latency_ms, retry_count + extra_retries + 1

                validation = output_validator.validate_speech(
                    speech_data,
                    target_minutes=request.duration_minutes,
                    words_per_minute=settings.SPEECH_WORDS_PER_MINUTE,
                    can_cite_as_municipal=False,
                )
                if validation.passed:
                    return speech_data, total_latency_ms, retry_count
                retry_count = attempt + 1
            except ValidationBlockedError:
                raise
            except LLMProviderError as exc:
                total_latency_ms += (time.monotonic() - t0) * 1000
                last_error = exc
                retry_count = attempt + 1
                msg = str(exc).lower()
                if getattr(exc, "status_code", None) == 429 or "rate limit" in msg:
                    raise ValidationBlockedError(
                        1,
                        "Groq alcanzó el límite diario de tokens de esta cuenta. Espera a que se reinicie la cuota, usa otra API key/organización o cambia a un proveedor/modelo con cuota disponible.",
                    )
            except Exception as exc:
                total_latency_ms += (time.monotonic() - t0) * 1000
                last_error = exc
                retry_count = attempt + 1
                logger.exception("Monolithic speech generation failed")

        sectioned_data, extra_latency_ms, extra_retries = await self._generate_sectioned_speech(
            request=request,
            context=context,
            speech_type=speech_type,
            plan=plan,
        )
        return sectioned_data, total_latency_ms + extra_latency_ms, retry_count + extra_retries

    async def _generate_sectioned_speech(
        self,
        request: SpeechRunRequest,
        context: PromptContext,
        speech_type: str,
        plan: SpeechGenerationPlan,
    ) -> tuple[dict[str, Any], float, int]:
        total_latency_ms = 0.0
        retry_count = 0

        outline, outline_latency_ms = await self._generate_outline(
            context=context,
            speech_type=speech_type,
            body_sections=plan.body_sections,
            opening_words=plan.opening_words,
            body_section_words=plan.body_section_words,
            closing_words=plan.closing_words,
        )
        total_latency_ms += outline_latency_ms

        opening, lat = await self._generate_text_section(
            _prompt_builder.build_speech_opening_prompt(
                context=context,
                focus=outline["opening_focus"],
                goal_words=plan.opening_words,
            )
        )
        total_latency_ms += lat

        body_sections: list[dict[str, str]] = []
        for batch in plan.batches:
            for section_idx in batch:
                sec = outline["sections"][section_idx - 1]
                content, lat = await self._generate_text_section(
                    _prompt_builder.build_speech_body_section_prompt(
                        context=context,
                        title=sec["title"],
                        focus=sec["focus"],
                        goal_words=sec["goal_words"],
                    )
                )
                total_latency_ms += lat
                ensured, lat, local_retries = await self._ensure_section_length(
                    context=context,
                    title=sec["title"],
                    focus=sec["focus"],
                    content=content,
                    goal_words=sec["goal_words"],
                )
                total_latency_ms += lat
                retry_count += local_retries
                body_sections.append(
                    {
                        "title": sec["title"],
                        "content": ensured,
                        "persuasion_technique": sec.get("persuasion_technique", "desarrollo argumentativo"),
                    }
                )

        closing, lat = await self._generate_text_section(
            _prompt_builder.build_speech_closing_prompt(
                context=context,
                focus=outline["closing_focus"],
                goal_words=plan.closing_words,
            )
        )
        total_latency_ms += lat

        full_text = self._join_speech(opening, body_sections, closing)
        speech_data = {
            "title": self._build_title(context),
            "speech_objective": context.speech_goal,
            "target_audience": context.audience,
            "estimated_duration_minutes": context.duration_minutes,
            "estimated_word_count": len(full_text.split()),
            "opening": opening,
            "body_sections": body_sections,
            "local_references": self._collect_local_references(context.territory_text),
            "emotional_hooks": context.pain_points[:3],
            "rational_hooks": context.opportunities[:3],
            "closing": closing,
            "full_text": full_text,
            "adaptation_notes": (
                ["Discurso adaptado a partir de un texto base segmentado y limpiado."]
                if speech_type == "adaptation"
                else ["Discurso generado desde contexto territorial y análisis."]
            ),
        }
        return speech_data, total_latency_ms, retry_count

    async def _generate_outline(
        self,
        context: PromptContext,
        speech_type: str,
        body_sections: int,
        opening_words: int,
        body_section_words: int,
        closing_words: int,
    ) -> tuple[dict[str, Any], float]:
        total_latency_ms = 0.0
        last_error: Optional[Exception] = None

        fallback_topics: list[str] = []
        for p in list(context.pain_points or []) + list(context.opportunities or []):
            if p and p not in fallback_topics:
                fallback_topics.append(p)
        if not fallback_topics:
            fallback_topics = [
                "empleo local y economía familiar",
                "servicios básicos y calidad de vida",
                "salud y atención oportuna",
                "educación y oportunidades para jóvenes",
                "seguridad y comunidad",
                "infraestructura y movilidad",
            ]

        for attempt in range(settings.SPEECH_OUTLINE_RETRY_ATTEMPTS + 1):
            t0 = time.monotonic()
            try:
                prompt = _prompt_builder.build_speech_outline_prompt(
                    context=context,
                    body_sections=body_sections,
                    opening_words=opening_words,
                    body_section_words=body_section_words,
                    closing_words=closing_words,
                    speech_type=speech_type,
                )
                resp = await _groq.complete(_prompt_builder.to_llm_request(prompt))
                total_latency_ms += (time.monotonic() - t0) * 1000
                raw, ok = output_parser.parse_json(resp.content)
                if not ok:
                    continue

                normalized_sections = []
                raw_sections = raw.get("sections") or []
                if not isinstance(raw_sections, list):
                    raw_sections = []

                for idx in range(body_sections):
                    candidate = raw_sections[idx] if idx < len(raw_sections) and isinstance(raw_sections[idx], dict) else {}
                    topic = fallback_topics[idx % len(fallback_topics)]
                    normalized_sections.append(
                        {
                            "title": candidate.get("title") or f"Propuesta {idx + 1}: {topic}",
                            "focus": candidate.get("focus") or topic,
                            "goal_words": max(220, int(candidate.get("goal_words") or body_section_words)),
                            "persuasion_technique": candidate.get("persuasion_technique") or "desarrollo argumentativo",
                        }
                    )

                return {
                    "opening_focus": raw.get("opening_focus") or f"Conexión emocional con {context.municipality_name}",
                    "sections": normalized_sections,
                    "closing_focus": raw.get("closing_focus") or f"Llamado final a la acción por {context.municipality_name}",
                }, total_latency_ms
            except LLMProviderError as exc:
                total_latency_ms += (time.monotonic() - t0) * 1000
                last_error = exc
                msg = str(exc).lower()
                if getattr(exc, "status_code", None) == 429 or "rate limit" in msg:
                    raise ValidationBlockedError(
                        1,
                        "Groq alcanzó el límite diario de tokens de esta cuenta. Espera a que se reinicie la cuota, usa otra API key/organización o cambia a un proveedor/modelo con cuota disponible.",
                    )
            except Exception as exc:
                total_latency_ms += (time.monotonic() - t0) * 1000
                last_error = exc
                logger.exception("Outline generation failed")

        raise ValidationBlockedError(1, f"Could not generate a valid speech outline. Last: {last_error}")

    async def _generate_text_section(self, prompt) -> tuple[str, float]:
        t0 = time.monotonic()
        try:
            resp = await _groq.complete(_prompt_builder.to_llm_request(prompt))
            latency_ms = (time.monotonic() - t0) * 1000
            return self._clean_generated_text(resp.content), latency_ms
        except LLMProviderError as exc:
            msg = str(exc).lower()
            if getattr(exc, "status_code", None) == 429 or "rate limit" in msg:
                raise ValidationBlockedError(
                    1,
                    "Groq alcanzó el límite diario de tokens de esta cuenta. Espera a que se reinicie la cuota, usa otra API key/organización o cambia a un proveedor/modelo con cuota disponible.",
                )
            raise

    async def _ensure_section_length(
        self,
        context: PromptContext,
        title: str,
        focus: str,
        content: str,
        goal_words: int,
    ) -> tuple[str, float, int]:
        min_words = int(goal_words * settings.SPEECH_SECTION_MIN_FACTOR)
        current = content
        total_latency_ms = 0.0
        retries = 0

        for attempt in range(settings.SPEECH_SECTION_RETRY_ATTEMPTS + 1):
            if len(current.split()) >= min_words:
                return current, total_latency_ms, retries
            retries = attempt + 1
            prompt = _prompt_builder.build_speech_expand_section_prompt(
                context=context,
                title=title,
                focus=focus,
                current_text=current,
                goal_words=goal_words,
                min_words=min_words,
            )
            expanded, lat = await self._generate_text_section(prompt)
            total_latency_ms += lat
            if len(expanded.split()) > len(current.split()):
                current = expanded
        return current, total_latency_ms, retries

    async def _expand_short_sections(
        self,
        request: SpeechRunRequest,
        context: PromptContext,
        speech_data: dict[str, Any],
        missing_words: int,
    ) -> tuple[dict[str, Any], float, int]:
        total_latency_ms = 0.0
        retry_count = 0
        sections = speech_data.get("body_sections") or []
        if not sections or missing_words <= 0:
            return speech_data, total_latency_ms, retry_count

        per_section_boost = max(90, missing_words // max(1, len(sections)))
        new_sections: list[dict[str, str]] = []
        for sec in sections:
            title = sec.get("title", "Sección")
            content = sec.get("content", "")
            prompt = _prompt_builder.build_speech_expand_section_prompt(
                context=context,
                title=title,
                focus=title,
                current_text=content,
                goal_words=len(content.split()) + per_section_boost,
                min_words=len(content.split()) + int(per_section_boost * 0.7),
            )
            expanded, lat = await self._generate_text_section(prompt)
            total_latency_ms += lat
            retry_count += 1
            new_sections.append(
                {
                    "title": title,
                    "content": expanded if len(expanded.split()) > len(content.split()) else content,
                    "persuasion_technique": sec.get("persuasion_technique", "desarrollo argumentativo"),
                }
            )

        speech_data["body_sections"] = new_sections
        speech_data["full_text"] = self._join_speech(
            speech_data.get("opening", ""),
            new_sections,
            speech_data.get("closing", ""),
        )
        speech_data["estimated_word_count"] = len((speech_data.get("full_text") or "").split())
        return speech_data, total_latency_ms, retry_count

    async def _enforce_duration_target(
        self,
        request: SpeechRunRequest,
        context: PromptContext,
        speech_type: str,
        plan: SpeechGenerationPlan,
        speech_data: dict[str, Any],
    ) -> tuple[dict[str, Any], float, int]:
        verification = text_processing_service.verify_duration(
            speech_data.get("full_text", ""),
            target_minutes=request.duration_minutes,
            channel=request.channel,
        )
        if verification.within_tolerance:
            speech_data["duration_verification"] = verification.to_dict()
            return speech_data, 0.0, 0

        if verification.estimated_minutes < verification.lower_bound_minutes:
            speech_data, latency_ms, retries = await self._expand_short_sections(
                request=request,
                context=context,
                speech_data=speech_data,
                missing_words=max(0, plan.minimum_words - verification.actual_word_count),
            )
            verification = text_processing_service.verify_duration(
                speech_data.get("full_text", ""),
                target_minutes=request.duration_minutes,
                channel=request.channel,
            )
            speech_data["duration_verification"] = verification.to_dict()
            return speech_data, latency_ms, retries

        speech_data["duration_verification"] = verification.to_dict()
        return speech_data, 0.0, 0

    def _join_speech(self, opening: str, body_sections: list[dict[str, str]], closing: str) -> str:
        parts = [opening.strip()]
        for sec in body_sections:
            title = sec.get("title", "").strip()
            content = sec.get("content", "").strip()
            if title:
                parts.append(title)
            if content:
                parts.append(content)
        parts.append(closing.strip())
        return "\n\n".join([p for p in parts if p])

    def _clean_generated_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        return cleaned

    def _build_title(self, context: PromptContext) -> str:
        municipality = context.municipality_name or "Tlaxcala"
        neighborhood = f" — {context.neighborhood_name}" if getattr(context, "neighborhood_name", "") else ""
        goal = (context.speech_goal or "Discurso político").strip()
        if len(goal) > 60:
            goal = goal[:57].rstrip() + "..."
        return f"{goal} — {municipality}{neighborhood}"

    def _collect_local_references(self, territory_text: str) -> list[str]:
        refs: list[str] = []
        for line in (territory_text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if any(token in low for token in ["municipio", "región", "sector", "agua", "salud", "empleo", "internet", "zona", "barrio"]):
                refs.append(line)
            if len(refs) >= 8:
                break
        return refs

    def _extract_pain_points(self, analysis) -> list[str]:
        return [
            n.get("title", "")
            for n in (analysis.critical_needs or [])
            if isinstance(n, dict) and n.get("title")
        ]

    def _extract_opportunities(self, analysis) -> list[str]:
        return list(analysis.opportunities or [])

    def _strengthen_prompt(self, prompt, min_words: int, attempt: int):
        from copy import deepcopy

        p = deepcopy(prompt)
        extra = (
            f"\n\nADVERTENCIA CRÍTICA: El discurso anterior fue rechazado por ser demasiado corto. "
            f"INTENTO #{attempt + 1}. Debes entregar un discurso completo de al menos {min_words:,} palabras. "
            "No hagas resumen. No cierres temprano. No uses listas. "
            "Desarrolla ampliamente cada argumento con contexto, impacto cotidiano, propuesta pública, plazos, métricas y llamado a la acción. "
            "Debes ser específico con el municipio y, si existe, con la zona o barrio objetivo."
        )
        p.user_prompt += extra
        return p


speech_orchestrator = SpeechOrchestrator()