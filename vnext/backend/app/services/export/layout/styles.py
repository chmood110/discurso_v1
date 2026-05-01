"""
Centralised ParagraphStyle factory for the analysis PDF.

Why this module exists:
    The original `_style_map` mutated the dict returned by `pdf_common.styles()`
    (a shared cache) and created new `ParagraphStyle` objects every render.
    Here we build all styles in a fresh dict, derived from a clean copy of
    the base styles, so renders are independent and global state stays clean.

Public entry point: `build_styles() -> dict[str, ParagraphStyle]`.
"""
from __future__ import annotations

from reportlab.lib.styles import ParagraphStyle

from app.services.export.pdf_common import styles as base_styles
from app.services.export.layout.tokens import Palette


def _set_default(target: dict[str, ParagraphStyle], name: str, style: ParagraphStyle) -> None:
    """Set `name` only if it is not already present (additive, never overrides)."""
    if name not in target:
        target[name] = style


def build_styles() -> dict[str, ParagraphStyle]:
    """Build the full style map used by the analysis renderer.

    Returns a *new* dict each call so callers cannot leak mutations back into
    the shared base palette.
    """
    base = dict(base_styles())  # defensive copy

    _set_default(
        base,
        "tag",
        ParagraphStyle(
            "tag",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=Palette.EMERALD,
        ),
    )
    _set_default(
        base,
        "h1",
        ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=Palette.INK_DARK,
        ),
    )
    _set_default(
        base,
        "subtle",
        ParagraphStyle(
            "subtle",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=Palette.SLATE_500,
        ),
    )
    _set_default(
        base,
        "section_title",
        ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=Palette.INK_DARK,
            spaceAfter=2,
        ),
    )
    _set_default(
        base,
        "body",
        ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            textColor=Palette.SLATE_700,
        ),
    )
    _set_default(
        base,
        "body_sm",
        ParagraphStyle(
            "body_sm",
            fontName="Helvetica",
            fontSize=8.2,
            leading=11,
            textColor=Palette.SLATE_500,
        ),
    )
    _set_default(
        base,
        "bullet",
        ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=Palette.SLATE_700,
        ),
    )
    _set_default(
        base,
        "table_h",
        ParagraphStyle(
            "table_h",
            fontName="Helvetica-Bold",
            fontSize=8.4,
            leading=10.5,
            textColor=Palette.INK_DARK,
        ),
    )
    _set_default(
        base,
        "table_h_center",
        ParagraphStyle(
            "table_h_center",
            parent=base["table_h"],
            alignment=1,
        ),
    )
    _set_default(
        base,
        "table_cell",
        ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=8.35,
            leading=10.3,
            textColor=Palette.SLATE_700,
        ),
    )
    _set_default(
        base,
        "table_cell_center",
        ParagraphStyle(
            "table_cell_center",
            parent=base["table_cell"],
            alignment=1,
        ),
    )
    _set_default(
        base,
        "metric_value",
        ParagraphStyle(
            "metric_value",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            alignment=1,
            textColor=Palette.INK_DARK,
        ),
    )
    _set_default(
        base,
        "metric_label",
        ParagraphStyle(
            "metric_label",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=Palette.SLATE_500,
        ),
    )
    _set_default(
        base,
        "kicker",
        ParagraphStyle(
            "kicker",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=Palette.SLATE_500,
        ),
    )
    _set_default(
        base,
        "need_title",
        ParagraphStyle(
            "need_title",
            fontName="Helvetica-Bold",
            fontSize=10.8,
            leading=13,
            textColor=Palette.INK_DARK,
        ),
    )
    _set_default(
        base,
        "need_meta",
        ParagraphStyle(
            "need_meta",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=Palette.SLATE_700,
        ),
    )
    return base
