"""Remove cross-schema enrollment foreign keys.

Revision ID: 0002_rm_enroll_fks
Revises: 0001_progress_phase4
Create Date: 2026-04-19
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0002_rm_enroll_fks"
down_revision = "0001_progress_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "student_progress_enrollment_id_fkey",
        "student_progress",
        schema="progress",
        type_="foreignkey",
    )
    op.drop_constraint(
        "certificates_enrollment_id_fkey",
        "certificates",
        schema="progress",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "student_progress_enrollment_id_fkey",
        "student_progress",
        "enrollments",
        ["enrollment_id"],
        ["id"],
        source_schema="progress",
        referent_schema="enrollment",
    )
    op.create_foreign_key(
        "certificates_enrollment_id_fkey",
        "certificates",
        "enrollments",
        ["enrollment_id"],
        ["id"],
        source_schema="progress",
        referent_schema="enrollment",
    )
