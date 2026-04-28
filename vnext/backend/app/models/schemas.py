"""Pydantic schemas — VoxPolítica 2.0 API contracts."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class CandidateContext(BaseModel):
    name: Optional[str] = None
    party: Optional[str] = None
    position: Optional[str] = None
    style: Optional[str] = None
    values: list[str] = Field(default_factory=list)


class DataQualityBrief(BaseModel):
    overall_confidence: float
    can_cite_as_municipal: bool


class DataQualitySummary(BaseModel):
    overall_confidence: float
    municipal_coverage_pct: float
    state_coverage_pct: float
    estimated_coverage_pct: float
    can_cite_as_municipal: bool
    quality_label: str
    methodology_disclaimer: str


class DataQualityEvidence(BaseModel):
    overall_confidence: float
    can_cite_as_municipal: bool
    quality_label: str


class ValidationIssueOut(BaseModel):
    code: str
    severity: str
    field: Optional[str] = None
    description: str
    value_excerpt: Optional[str] = None


class ValidationReportOut(BaseModel):
    passed: bool
    score: float
    checks_run: int
    checks_failed: int
    blocking_count: int
    warning_count: int
    rule_version: str
    issues: list[ValidationIssueOut] = Field(default_factory=list)


# ── Strategic section (replaces Brief) ───────────────────────────────────────

class MessagingAxis(BaseModel):
    axis: str
    message: str
    rationale: str = ""
    emotional_hook: str = ""
    data_anchor: str = ""


class StrategySection(BaseModel):
    """LLM-generated strategic layer integrated into AnalysisDetail."""
    executive_strategic: str = ""
    messaging_axes: list[MessagingAxis] = Field(default_factory=list)
    pain_points_ranked: list[str] = Field(default_factory=list)
    opportunities_ranked: list[str] = Field(default_factory=list)
    candidate_positioning: str = ""
    recommended_tone: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    framing_suggestions: list[str] = Field(default_factory=list)
    communication_channels_priority: list[str] = Field(default_factory=list)
    ai_generated: bool = False
    latency_ms: Optional[float] = None


# ── Evidence ─────────────────────────────────────────────────────────────────

class EvidenceResolveRequest(BaseModel):
    force_refresh: bool = False


class EvidenceSummary(BaseModel):
    id: str
    municipality_id: str
    municipality_name: str
    created_at: datetime
    collection_method: str
    data_quality: DataQualityEvidence


class EvidenceDetail(BaseModel):
    id: str
    municipality_id: str
    municipality_name: str
    snapshot_version: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    collection_method: str
    data_quality: DataQualitySummary
    sources_used: list[str]
    geographic_fallbacks: list[str]


# ── Analysis ─────────────────────────────────────────────────────────────────

class AnalysisRunRequest(BaseModel):
    municipality_id: str = Field(..., description="e.g. TLX-APZ")
    objective: Optional[str] = Field(None, max_length=500)
    force_refresh: bool = False


class AnalysisSummary(BaseModel):
    id: str
    municipality_id: str
    evidence_record_id: str
    created_at: datetime
    status: str
    objective: Optional[str] = None
    executive_summary: str
    data_quality: DataQualityBrief
    validation: ValidationReportOut


class AnalysisDetail(BaseModel):
    id: str
    municipality_id: str
    evidence_record_id: str
    created_at: datetime
    status: str
    objective: Optional[str] = None
    executive_summary: str
    demographic_profile: dict[str, Any] = Field(default_factory=dict)
    economic_engine: dict[str, Any] = Field(default_factory=dict)
    infrastructure_gaps: dict[str, Any] = Field(default_factory=dict)
    critical_needs: list[dict[str, Any]] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    kpi_board: dict[str, Any] = Field(default_factory=dict)
    strategy_section: StrategySection = Field(default_factory=StrategySection)
    data_quality: DataQualityBrief
    validation: ValidationReportOut


# ── Speech ────────────────────────────────────────────────────────────────────

class SpeechRunRequest(BaseModel):
    municipality_id: str
    speech_goal: str = Field(..., min_length=10, max_length=500)
    audience: str = Field(..., min_length=5, max_length=300)
    tone: str
    channel: str
    duration_minutes: int = Field(default=10, ge=1, le=120)
    force_refresh: bool = False
    source_text: Optional[str] = Field(None, max_length=200_000)
    priority_topics: list[str] = Field(default_factory=list)
    avoid_topics: list[str] = Field(default_factory=list)
    candidate: Optional[CandidateContext] = None
    electoral_moment: Optional[str] = None
    neighborhood_id: Optional[str] = None


class SpeechSummary(BaseModel):
    id: str
    municipality_id: str
    analysis_run_id: Optional[str] = None
    created_at: datetime
    status: str
    speech_type: str
    target_duration_minutes: int
    target_word_count: int
    actual_word_count: int
    retry_count: int
    parameter_hash: str
    data_quality: DataQualityBrief
    validation: ValidationReportOut


class SpeechDetail(SpeechSummary):
    speech_data: dict[str, Any]
    ai_generated: bool
    latency_ms: Optional[float] = None