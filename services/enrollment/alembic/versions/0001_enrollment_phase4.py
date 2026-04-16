from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_enrollment_phase4"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrollments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'ENROLLED'")),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('ENROLLED', 'CANCELLED', 'COMPLETED')",
            name="ck_enrollments_status",
        ),
        sa.UniqueConstraint("student_id", "course_id", name="uq_enrollments_student_course"),
        schema="enrollment",
    )
    op.create_index("idx_enrollments_student", "enrollments", ["student_id"], schema="enrollment")
    op.create_index("idx_enrollments_course", "enrollments", ["course_id"], schema="enrollment")
    op.create_index("idx_enrollments_status", "enrollments", ["status"], schema="enrollment")
    op.create_index(
        "idx_enrollments_idempotency",
        "enrollments",
        ["idempotency_key"],
        unique=True,
        schema="enrollment",
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "enrollment_audit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "enrollment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enrollment.enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="enrollment",
    )
    op.create_index(
        "idx_enrollment_audit_enrollment",
        "enrollment_audit",
        ["enrollment_id"],
        schema="enrollment",
    )
    op.create_index(
        "idx_enrollment_audit_correlation",
        "enrollment_audit",
        ["correlation_id"],
        schema="enrollment",
    )

    op.create_table(
        "outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        schema="enrollment",
    )
    op.create_index(
        "idx_outbox_unpublished",
        "outbox",
        ["created_at"],
        schema="enrollment",
        postgresql_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_outbox_unpublished", table_name="outbox", schema="enrollment")
    op.drop_table("outbox", schema="enrollment")
    op.drop_index(
        "idx_enrollment_audit_correlation",
        table_name="enrollment_audit",
        schema="enrollment",
    )
    op.drop_index(
        "idx_enrollment_audit_enrollment",
        table_name="enrollment_audit",
        schema="enrollment",
    )
    op.drop_table("enrollment_audit", schema="enrollment")
    op.drop_index("idx_enrollments_idempotency", table_name="enrollments", schema="enrollment")
    op.drop_index("idx_enrollments_status", table_name="enrollments", schema="enrollment")
    op.drop_index("idx_enrollments_course", table_name="enrollments", schema="enrollment")
    op.drop_index("idx_enrollments_student", table_name="enrollments", schema="enrollment")
    op.drop_table("enrollments", schema="enrollment")