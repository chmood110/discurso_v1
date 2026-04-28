from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.connection import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MunicipalityDB(Base):
    __tablename__ = "municipalities"
    __table_args__ = (Index("ix_municipalities_region", "region"),)

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    state_id: Mapped[str] = mapped_column(String(10), default="TLX")
    population_2020: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(50))
    region: Mapped[str] = mapped_column(String(100))

    evidence_records: Mapped[list["EvidenceRecordDB"]] = relationship(back_populates="municipality")
    analysis_runs: Mapped[list["AnalysisRunDB"]] = relationship(back_populates="municipality")


class EvidenceRecordDB(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        Index("ix_evidence_municipality", "municipality_id"),
        Index("ix_evidence_snapshot", "snapshot_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    municipality_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("municipalities.id", ondelete="CASCADE"), nullable=False
    )
    municipality_name: Mapped[str] = mapped_column(String(200))
    snapshot_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    collection_method: Mapped[str] = mapped_column(String(50))

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    municipal_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    state_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    can_cite_as_municipal: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_label: Mapped[str] = mapped_column(String(200))
    methodology_disclaimer: Mapped[str] = mapped_column(Text, default="")

    social_data: Mapped[dict] = mapped_column(JSON, default=dict)
    economic_data: Mapped[dict] = mapped_column(JSON, default=dict)
    infrastructure_data: Mapped[dict] = mapped_column(JSON, default=dict)

    sources_used: Mapped[list] = mapped_column(JSON, default=list)
    sources_failed: Mapped[list] = mapped_column(JSON, default=list)
    geographic_fallbacks: Mapped[list] = mapped_column(JSON, default=list)

    municipality: Mapped["MunicipalityDB"] = relationship(back_populates="evidence_records")
    analysis_runs: Mapped[list["AnalysisRunDB"]] = relationship(back_populates="evidence_record")


class AnalysisRunDB(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_municipality", "municipality_id"),
        Index("ix_analysis_status", "status"),
        Index("ix_analysis_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    municipality_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("municipalities.id", ondelete="CASCADE"), nullable=False
    )
    evidence_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_records.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")

    executive_summary: Mapped[str] = mapped_column(Text, default="")
    demographic_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    economic_engine: Mapped[dict] = mapped_column(JSON, default=dict)
    infrastructure_gaps: Mapped[dict] = mapped_column(JSON, default=dict)
    critical_needs: Mapped[list] = mapped_column(JSON, default=list)
    opportunities: Mapped[list] = mapped_column(JSON, default=list)
    kpi_board: Mapped[dict] = mapped_column(JSON, default=dict)

    # Compatibilidad con la base SQLite actual
    speeches: Mapped[dict] = mapped_column(JSON, default=dict)

    # v2.0: strategy section replaces Brief module
    strategy_section: Mapped[dict] = mapped_column(JSON, default=dict)

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    can_cite_as_municipal: Mapped[bool] = mapped_column(Boolean, default=False)

    validation_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_score: Mapped[float] = mapped_column(Float, default=1.0)
    validation_issues: Mapped[list] = mapped_column(JSON, default=list)

    municipality: Mapped["MunicipalityDB"] = relationship(back_populates="analysis_runs")
    evidence_record: Mapped["EvidenceRecordDB"] = relationship(back_populates="analysis_runs")
    speech_runs: Mapped[list["SpeechRunDB"]] = relationship(back_populates="analysis_run")


class SpeechRunDB(Base):
    __tablename__ = "speech_runs"
    __table_args__ = (Index("ix_speech_municipality", "municipality_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    municipality_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("municipalities.id"), nullable=False
    )
    analysis_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("analysis_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="completed")

    speech_type: Mapped[str] = mapped_column(String(20))  # creation | adaptation | improvement
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    speech_data: Mapped[dict] = mapped_column(JSON, default=dict)

    target_duration_minutes: Mapped[int] = mapped_column(Integer, default=10)
    target_word_count: Mapped[int] = mapped_column(Integer, default=1300)
    actual_word_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    parameter_hash: Mapped[str] = mapped_column(String(16), default="")

    # Compatibilidad con la base SQLite actual
    validation_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    validation_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_score: Mapped[float] = mapped_column(Float, default=1.0)
    validation_issues: Mapped[list] = mapped_column(JSON, default=list)
    validation_rule_version: Mapped[str] = mapped_column(String(20), default="2.0.0")

    analysis_run: Mapped[Optional["AnalysisRunDB"]] = relationship(back_populates="speech_runs")