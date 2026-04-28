"""
Typed API response envelope.

Usage:
    @router.post("/run", response_model=APIResponse[AnalysisDetail])
    async def run_analysis(...) -> APIResponse[AnalysisDetail]:
        return APIResponse[AnalysisDetail].ok(data=AnalysisDetail(...))

FastAPI 0.115 + Pydantic v2 resolve generics correctly in OpenAPI.
The `data` field is typed to the concrete schema, giving precise validation
and accurate OpenAPI output.
"""
from __future__ import annotations
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: str = ""
    meta: Optional[dict] = None
    errors: Optional[list[dict]] = None

    @classmethod
    def ok(
        cls,
        data: Optional[T] = None,
        message: str = "",
        meta: Optional[dict] = None,
    ) -> "APIResponse[T]":
        return cls(success=True, data=data, message=message, meta=meta)

    @classmethod
    def fail(
        cls,
        message: str,
        errors: Optional[list[dict]] = None,
    ) -> "APIResponse[T]":
        return cls(success=False, data=None, message=message, errors=errors)
