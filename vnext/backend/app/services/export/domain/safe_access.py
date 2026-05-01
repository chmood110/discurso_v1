"""
Defensive accessors for raw JSON-like fields stored in the DB.

These helpers replace the original ``_as_dict``, ``_as_list``, ``_text``
and ``_num`` private functions. They keep the same lenient semantics
(return a safe default instead of raising) but emit a debug log when
they detect an unexpected type — that way silent N/D values in the PDF
become observable in production logs.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

log = logging.getLogger(__name__)


def as_dict(value: Any, *, context: str = "") -> dict[str, Any]:
    """Return ``value`` if it is a dict; ``{}`` otherwise. Logs unexpected types."""
    if isinstance(value, dict):
        return value
    if value is not None:
        log.debug(
            "as_dict: expected dict, got %s%s",
            type(value).__name__,
            f" ({context})" if context else "",
        )
    return {}


def as_list(value: Any, *, context: str = "") -> list[Any]:
    """Return ``value`` if it is a list; ``[]`` otherwise. Logs unexpected types."""
    if isinstance(value, list):
        return value
    if value is not None:
        log.debug(
            "as_list: expected list, got %s%s",
            type(value).__name__,
            f" ({context})" if context else "",
        )
    return []


def as_text(value: Any, default: str = "") -> str:
    """Return ``value`` as a stripped string, or ``default`` if blank/None."""
    if value is None:
        return default
    if isinstance(value, str):
        clean = value.strip()
        return clean if clean else default
    clean = str(value).strip()
    return clean if clean else default


def as_float(value: Any) -> float | None:
    """Coerce to float, returning ``None`` on failure (None, '', non-numeric)."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        log.debug("as_float: could not coerce %r", value)
        return None


def truncate(text: str, limit: int) -> str:
    """Trim ``text`` to ``limit`` chars, appending an ellipsis if truncated."""
    clean = as_text(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def dedupe_preserving_order(items: Iterable[str]) -> list[str]:
    """Deduplicate strings case-insensitively, preserving insertion order.

    Empty/whitespace-only items are dropped. The first occurrence's casing
    is the one kept.
    """
    seen: dict[str, str] = {}
    for item in items:
        clean = as_text(item)
        if not clean:
            continue
        key = clean.casefold()
        if key not in seen:
            seen[key] = clean
    return list(seen.values())
