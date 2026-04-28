"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('municipalities',
        sa.Column('id', sa.String(20), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('state_id', sa.String(10), default='TLX'),
        sa.Column('population_approx', sa.Integer, default=0),
        sa.Column('category', sa.String(50)),
        sa.Column('region', sa.String(100)),
    )
    op.create_index('ix_municipalities_region', 'municipalities', ['region'])

    op.create_table('evidence_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('municipality_id', sa.String(20), sa.ForeignKey('municipalities.id'), nullable=False),
        sa.Column('municipality_name', sa.String(200)),
        sa.Column('snapshot_version', sa.String(32)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collection_method', sa.String(50)),
        sa.Column('overall_confidence', sa.Float, default=0.0),
        sa.Column('municipal_coverage_pct', sa.Float, default=0.0),
        sa.Column('state_coverage_pct', sa.Float, default=0.0),
        sa.Column('estimated_coverage_pct', sa.Float, default=0.0),
        sa.Column('can_cite_as_municipal', sa.Boolean, default=False),
        sa.Column('quality_label', sa.String(200)),
        sa.Column('methodology_disclaimer', sa.Text, default=''),
        sa.Column('social_data', sa.JSON, default=dict),
        sa.Column('economic_data', sa.JSON, default=dict),
        sa.Column('infrastructure_data', sa.JSON, default=dict),
        sa.Column('sources_used', sa.JSON, default=list),
        sa.Column('sources_failed', sa.JSON, default=list),
        sa.Column('geographic_fallbacks', sa.JSON, default=list),
    )
    op.create_index('ix_evidence_municipality', 'evidence_records', ['municipality_id'])
    op.create_index('ix_evidence_snapshot', 'evidence_records', ['snapshot_version'])

    op.create_table('analysis_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('municipality_id', sa.String(20), sa.ForeignKey('municipalities.id'), nullable=False),
        sa.Column('evidence_record_id', sa.String(36), sa.ForeignKey('evidence_records.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('objective', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), default='completed'),
        sa.Column('executive_summary', sa.Text, default=''),
        sa.Column('demographic_profile', sa.JSON, default=dict),
        sa.Column('economic_engine', sa.JSON, default=dict),
        sa.Column('infrastructure_gaps', sa.JSON, default=dict),
        sa.Column('critical_needs', sa.JSON, default=list),
        sa.Column('opportunities', sa.JSON, default=list),
        sa.Column('kpi_board', sa.JSON, default=dict),
        sa.Column('speeches', sa.JSON, default=dict),
        sa.Column('overall_confidence', sa.Float, default=0.0),
        sa.Column('can_cite_as_municipal', sa.Boolean, default=False),
        sa.Column('validation_passed', sa.Boolean, default=True),
        sa.Column('validation_score', sa.Float, default=1.0),
        sa.Column('validation_issues', sa.JSON, default=list),
    )
    op.create_index('ix_analysis_municipality', 'analysis_runs', ['municipality_id'])
    op.create_index('ix_analysis_status', 'analysis_runs', ['status'])

    op.create_table('brief_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('municipality_id', sa.String(20), sa.ForeignKey('municipalities.id'), nullable=False),
        sa.Column('analysis_run_id', sa.String(36), sa.ForeignKey('analysis_runs.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(20), default='completed'),
        sa.Column('campaign_objective', sa.Text),
        sa.Column('candidate_context', sa.JSON, default=dict),
        sa.Column('brief_data', sa.JSON, default=dict),
        sa.Column('ai_generated', sa.Boolean, default=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('latency_ms', sa.Float, nullable=True),
        sa.Column('overall_confidence', sa.Float, default=0.0),
        sa.Column('can_cite_as_municipal', sa.Boolean, default=False),
        sa.Column('validation_passed', sa.Boolean, default=True),
        sa.Column('validation_score', sa.Float, default=1.0),
        sa.Column('validation_issues', sa.JSON, default=list),
    )
    op.create_index('ix_brief_municipality', 'brief_runs', ['municipality_id'])

    op.create_table('speech_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('municipality_id', sa.String(20), sa.ForeignKey('municipalities.id'), nullable=False),
        sa.Column('analysis_run_id', sa.String(36), sa.ForeignKey('analysis_runs.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(20), default='completed'),
        sa.Column('speech_type', sa.String(20)),
        sa.Column('parameters', sa.JSON, default=dict),
        sa.Column('speech_data', sa.JSON, default=dict),
        sa.Column('target_duration_minutes', sa.Integer, default=10),
        sa.Column('target_word_count', sa.Integer, default=1300),
        sa.Column('actual_word_count', sa.Integer, default=0),
        sa.Column('retry_count', sa.Integer, default=0),
        sa.Column('ai_generated', sa.Boolean, default=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('latency_ms', sa.Float, nullable=True),
        sa.Column('overall_confidence', sa.Float, default=0.0),
        sa.Column('validation_passed', sa.Boolean, default=True),
        sa.Column('validation_score', sa.Float, default=1.0),
        sa.Column('validation_issues', sa.JSON, default=list),
    )
    op.create_index('ix_speech_municipality', 'speech_runs', ['municipality_id'])

    op.create_table('batch_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('job_type', sa.String(30)),
        sa.Column('municipality_ids', sa.JSON, default=list),
        sa.Column('parameters', sa.JSON, default=dict),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('total', sa.Integer, default=0),
        sa.Column('completed', sa.Integer, default=0),
        sa.Column('failed', sa.Integer, default=0),
        sa.Column('results', sa.JSON, default=dict),
        sa.Column('errors', sa.JSON, default=dict),
    )
    op.create_index('ix_batch_status', 'batch_jobs', ['status'])

    op.create_table('export_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('export_type', sa.String(30)),
        sa.Column('run_ids', sa.JSON, default=list),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('pdf_size_bytes', sa.Integer, default=0),
        sa.Column('validation_passed', sa.Boolean, default=True),
        sa.Column('error_message', sa.Text, nullable=True),
    )


def downgrade() -> None:
    for tbl in ('export_jobs','batch_jobs','speech_runs','brief_runs','analysis_runs',
                'evidence_records','municipalities'):
        op.drop_table(tbl)
