"""Hardening: add parameter_hash, retry_count, validation_rule_version,
   ReviewRunDB table

Revision ID: 002
Revises: 001
Create Date: 2024-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── brief_runs: new columns ────────────────────────────────────────────
    op.add_column('brief_runs',
        sa.Column('parameter_hash', sa.String(16), nullable=False, server_default=''))
    op.add_column('brief_runs',
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'))
    op.add_column('brief_runs',
        sa.Column('validation_rule_version', sa.String(20), nullable=False, server_default='1.0.0'))
    op.create_index('ix_brief_param_hash', 'brief_runs', ['municipality_id', 'parameter_hash'])

    # ── speech_runs: new columns ───────────────────────────────────────────
    op.add_column('speech_runs',
        sa.Column('parameter_hash', sa.String(16), nullable=False, server_default=''))
    op.add_column('speech_runs',
        sa.Column('validation_rule_version', sa.String(20), nullable=False, server_default='1.0.0'))
    op.create_index('ix_speech_param_hash', 'speech_runs', ['municipality_id', 'parameter_hash'])

    # ── analysis_runs: add validation_rule_version ─────────────────────────
    op.add_column('analysis_runs',
        sa.Column('validation_rule_version', sa.String(20), nullable=False, server_default='1.0.0'))

    # ── review_runs: new table ─────────────────────────────────────────────
    op.create_table(
        'review_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('municipality_id', sa.String(20),
                  sa.ForeignKey('municipalities.id'), nullable=False),
        sa.Column('speech_run_id', sa.String(36),
                  sa.ForeignKey('speech_runs.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False, server_default='completed'),
        sa.Column('speech_text_excerpt', sa.Text, nullable=False, server_default=''),
        sa.Column('speech_text_length', sa.Integer, nullable=False, server_default='0'),
        sa.Column('review_data', sa.JSON, nullable=False),
        sa.Column('overall_score', sa.Float, nullable=True),
        sa.Column('ai_generated', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('latency_ms', sa.Float, nullable=True),
    )
    op.create_index('ix_review_municipality', 'review_runs', ['municipality_id'])


def downgrade() -> None:
    op.drop_table('review_runs')
    op.drop_index('ix_brief_param_hash', 'brief_runs')
    op.drop_column('brief_runs', 'parameter_hash')
    op.drop_column('brief_runs', 'retry_count')
    op.drop_column('brief_runs', 'validation_rule_version')
    op.drop_index('ix_speech_param_hash', 'speech_runs')
    op.drop_column('speech_runs', 'parameter_hash')
    op.drop_column('speech_runs', 'validation_rule_version')
    op.drop_column('analysis_runs', 'validation_rule_version')
