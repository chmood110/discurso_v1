from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.services.llm.models import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GroqClient:
    def __init__(self):
        self.base_url = settings.GROQ_BASE_URL.rstrip("/")
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.timeout = settings.GROQ_TIMEOUT_SECONDS

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("GROQ_API_KEY no configurada")

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or settings.GROQ_MAX_TOKENS,
        }

        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        retries = 2
        last_error: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(retries + 1):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    if resp.status_code == 429:
                        logger.warning("Groq status 429 — reintentando (attempt=%d)", attempt + 1)
                        if attempt < retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise LLMProviderError(
                            f"Groq rate limit (429): {resp.text}",
                            status_code=429,
                        )

                    if resp.status_code >= 400:
                        raise LLMProviderError(
                            f"Groq error {resp.status_code}: {resp.text}",
                            status_code=resp.status_code,
                        )

                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    usage = data.get("usage", {}) or {}

                    return LLMResponse(
                        content=content,
                        model=data.get("model", self.model),
                        provider="groq",
                        usage={
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                        raw=data,
                    )

                except httpx.TimeoutException as exc:
                    last_error = exc
                    logger.warning("Groq timeout — reintentando (attempt=%d)", attempt + 1)
                    if attempt < retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise LLMProviderError("Timeout al consultar Groq") from exc

                except httpx.HTTPError as exc:
                    last_error = exc
                    logger.error("Groq HTTP error: %s", exc)
                    raise LLMProviderError(f"HTTP error al consultar Groq: {exc}") from exc

                except LLMProviderError:
                    raise

                except Exception as exc:
                    last_error = exc
                    logger.exception("Error inesperado en GroqClient")
                    raise LLMProviderError(f"Error inesperado en GroqClient: {exc}") from exc

        raise LLMProviderError(f"Groq failed after retries. Last error: {last_error}")