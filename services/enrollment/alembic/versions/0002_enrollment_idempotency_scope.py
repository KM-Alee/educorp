from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_enrollment_idempotency"
down_revision = "0001_enrollment_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_enrollments_idempotency", table_name="enrollments", schema="enrollment")
    op.create_index(
        "idx_enrollments_idempotency",
        "enrollments",
        ["student_id", "idempotency_key"],
        schema="enrollment",
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_enrollments_idempotency", table_name="enrollments", schema="enrollment")
    op.create_index(
        "idx_enrollments_idempotency",
        "enrollments",
        ["idempotency_key"],
        schema="enrollment",
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
