from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_progress_phase4_snapshot_fields"
down_revision = "0001_progress_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_progress",
        sa.Column("student_name", sa.String(length=200), nullable=False, server_default=""),
        schema="progress",
    )
    op.add_column(
        "student_progress",
        sa.Column("course_title", sa.String(length=300), nullable=False, server_default=""),
        schema="progress",
    )
    op.add_column(
        "module_progress",
        sa.Column("module_title", sa.String(length=300), nullable=False, server_default=""),
        schema="progress",
    )
    op.add_column(
        "module_progress",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        schema="progress",
    )
    op.add_column(
        "module_progress",
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="progress",
    )

    op.drop_constraint("ck_student_progress_status", "student_progress", schema="progress")
    op.create_check_constraint(
        "ck_student_progress_status",
        "student_progress",
        "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
        schema="progress",
    )


def downgrade() -> None:
    op.drop_constraint("ck_student_progress_status", "student_progress", schema="progress")
    op.create_check_constraint(
        "ck_student_progress_status",
        "student_progress",
        "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
        schema="progress",
    )

    op.drop_column("module_progress", "is_required", schema="progress")
    op.drop_column("module_progress", "sort_order", schema="progress")
    op.drop_column("module_progress", "module_title", schema="progress")
    op.drop_column("student_progress", "course_title", schema="progress")
    op.drop_column("student_progress", "student_name", schema="progress")
