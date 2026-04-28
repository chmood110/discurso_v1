"""003_cleanup_v2.py — Remove Brief/Batch/Review/Export tables; add strategy_section."""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop modules eliminated in v2.0
    for tbl in ("brief_runs", "review_runs", "batch_jobs", "export_jobs"):
        try:
            op.drop_table(tbl)
        except Exception:
            pass  # already gone in fresh installs

    # Add strategy_section to analysis_runs
    try:
        op.add_column(
            "analysis_runs",
            sa.Column("strategy_section", sa.JSON(), nullable=True, server_default="{}"),
        )
    except Exception:
        pass  # already exists

    # Rename population_approx → population_2020 on municipalities
    try:
        op.alter_column("municipalities", "population_approx", new_column_name="population_2020")
    except Exception:
        pass


def downgrade() -> None:
    op.drop_column("analysis_runs", "strategy_section")