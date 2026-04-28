"""
Common PDF building blocks — styles, colors, helpers.
Used by all three PDF builders.
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle, KeepTogether,
)

# ── Palette ───────────────────────────────────────────────────────────────────
EMERALD      = colors.HexColor("#059669")
EMERALD_DK   = colors.HexColor("#047857")
EMERALD_LT   = colors.HexColor("#ecfdf5")
SLATE_900    = colors.HexColor("#0f172a")
SLATE_700    = colors.HexColor("#334155")
SLATE_500    = colors.HexColor("#64748b")
SLATE_200    = colors.HexColor("#e2e8f0")
SLATE_50     = colors.HexColor("#f8fafc")
RED_600      = colors.HexColor("#dc2626")
AMBER_600    = colors.HexColor("#d97706")
AMBER_LT     = colors.HexColor("#fffbeb")
BLUE_600     = colors.HexColor("#2563eb")
WHITE        = colors.white

# ── Layout constants ─────────────────────────────────────────────────────────
W, H    = letter
LM = RM = 0.85 * inch
TM = 0.80 * inch
BM = 0.70 * inch
UW = W - LM - RM   # 6.80"


def styles() -> dict[str, ParagraphStyle]:
    return {
        "h1": ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=20,
            textColor=SLATE_900, spaceAfter=4, leading=24),
        "h2": ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12.5,
            textColor=EMERALD_DK, spaceBefore=16, spaceAfter=6),
        "h3": ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.5,
            textColor=SLATE_700, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("Body", fontName="Helvetica", fontSize=10,
            textColor=SLATE_700, leading=15, spaceAfter=5, alignment=TA_JUSTIFY),
        "body_sm": ParagraphStyle("BodySm", fontName="Helvetica", fontSize=8.5,
            textColor=SLATE_500, leading=12, spaceAfter=3),
        "bullet": ParagraphStyle("Bullet", fontName="Helvetica", fontSize=10,
            textColor=SLATE_700, leftIndent=16, leading=14, spaceAfter=4),
        "bullet_red": ParagraphStyle("BulletR", fontName="Helvetica", fontSize=10,
            textColor=RED_600, leftIndent=16, leading=14, spaceAfter=4),
        "bullet_green": ParagraphStyle("BulletG", fontName="Helvetica", fontSize=10,
            textColor=EMERALD_DK, leftIndent=16, leading=14, spaceAfter=4),
        "caption": ParagraphStyle("Caption", fontName="Helvetica-Oblique", fontSize=8,
            textColor=SLATE_500, spaceAfter=3),
        "tag": ParagraphStyle("Tag", fontName="Helvetica-Bold", fontSize=8,
            textColor=EMERALD, spaceAfter=2, tracking=60),
        "disclaimer": ParagraphStyle("Disc", fontName="Helvetica-Oblique", fontSize=8.5,
            textColor=AMBER_600, leading=13, spaceAfter=4),
        "speech": ParagraphStyle("Speech", fontName="Helvetica", fontSize=10.5,
            textColor=SLATE_700, leading=17, spaceAfter=8, alignment=TA_JUSTIFY),
        "speech_h": ParagraphStyle("SpeechH", fontName="Helvetica-Bold", fontSize=10,
            textColor=EMERALD_DK, spaceBefore=12, spaceAfter=5),
    }


def sp(h: float = 10) -> Spacer:
    return Spacer(1, h)


def rule(color=SLATE_200, thick=0.5, before=4, after=8) -> HRFlowable:
    return HRFlowable(width="100%", thickness=thick, color=color,
                      spaceBefore=before, spaceAfter=after)


def section_bar(s: dict, title: str) -> list:
    bar = Table([[""]], colWidths=[UW], rowHeights=[3])
    bar.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),EMERALD)]))
    return [sp(14), bar, sp(4), Paragraph(title.upper(), s["h2"])]


def highlight_box(inner, bg=EMERALD_LT, border=EMERALD, pad=12) -> Table:
    cells = inner if isinstance(inner, list) else [inner]
    t = Table([cells], colWidths=[UW])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("LINEABOVE",(0,0),(-1,0),2.5,border),
        ("TOPPADDING",(0,0),(-1,-1),pad),
        ("BOTTOMPADDING",(0,0),(-1,-1),pad),
        ("LEFTPADDING",(0,0),(-1,-1),14),
        ("RIGHTPADDING",(0,0),(-1,-1),14),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    return t


def two_col(left: list, right: list) -> Table:
    hw = UW / 2
    rows, mx = [], max(len(left), len(right))
    for i in range(mx):
        rows.append([
            left[i] if i < len(left) else sp(1),
            right[i] if i < len(right) else sp(1),
        ])
    t = Table(rows, colWidths=[hw, hw])
    t.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LINEAFTER",(0,0),(0,-1),0.3,SLATE_200),
        ("RIGHTPADDING",(0,0),(0,-1),10),
        ("LEFTPADDING",(1,0),(1,-1),10),
    ]))
    return t


def quality_disclaimer_block(s: dict, disclaimer: str) -> Table:
    if not disclaimer:
        return None
    t = Table([[Paragraph(disclaimer, s["disclaimer"])]], colWidths=[UW])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),AMBER_LT),
        ("LINEABOVE",(0,0),(-1,0),2,AMBER_600),
        ("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),12),
        ("RIGHTPADDING",(0,0),(-1,-1),12),
    ]))
    return t


def make_doc(buffer, title: str = "") -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM, bottomMargin=BM,
        title=title,
    )


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(SLATE_200)
    canvas.setLineWidth(0.4)
    canvas.line(LM, BM - 8, W - RM, BM - 8)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SLATE_500)
    canvas.drawString(LM, BM - 20, "VoxPolítica Tlaxcala · Documento estratégico confidencial")
    canvas.drawRightString(W - RM, BM - 20, f"Página {doc.page}")
    canvas.restoreState()
