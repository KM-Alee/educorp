from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_progress_phase4"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_progress",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "enrollment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_name", sa.String(200), nullable=False, server_default=sa.text("''")),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_title", sa.String(300), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "progress_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'NOT_STARTED'"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_student_progress_status",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollment.enrollments.id"],
        ),
        schema="progress",
    )
    op.create_index(
        "idx_student_progress_student",
        "student_progress",
        ["student_id"],
        schema="progress",
    )
    op.create_index(
        "idx_student_progress_course",
        "student_progress",
        ["course_id"],
        schema="progress",
    )

    op.create_table(
        "module_progress",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "student_progress_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_title", sa.String(300), nullable=False, server_default=sa.text("''")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "is_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "progress_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_progress_id",
            "module_id",
            name="uq_module_progress_module",
        ),
        sa.ForeignKeyConstraint(
            ["student_progress_id"],
            ["progress.student_progress.id"],
            ondelete="CASCADE",
        ),
        schema="progress",
    )
    op.create_index(
        "idx_module_progress_parent",
        "module_progress",
        ["student_progress_id"],
        schema="progress",
    )

    op.create_table(
        "certificates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "enrollment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_title", sa.String(300), nullable=False),
        sa.Column("student_name", sa.String(200), nullable=False),
        sa.Column("certificate_number", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollment.enrollments.id"],
        ),
        schema="progress",
    )
    op.create_index(
        "idx_certificates_student",
        "certificates",
        ["student_id"],
        schema="progress",
    )
    op.create_index(
        "idx_certificates_number",
        "certificates",
        ["certificate_number"],
        schema="progress",
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
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        schema="progress",
    )
    op.create_index(
        "idx_outbox_unpublished",
        "outbox",
        ["created_at"],
        schema="progress",
        postgresql_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_outbox_unpublished", table_name="outbox", schema="progress")
    op.drop_table("outbox", schema="progress")

    op.drop_index("idx_certificates_number", table_name="certificates", schema="progress")
    op.drop_index("idx_certificates_student", table_name="certificates", schema="progress")
    op.drop_table("certificates", schema="progress")

    op.drop_index("idx_module_progress_parent", table_name="module_progress", schema="progress")
    op.drop_table("module_progress", schema="progress")

    op.drop_index(
        "idx_student_progress_course",
        table_name="student_progress",
        schema="progress",
    )
    op.drop_index(
        "idx_student_progress_student",
        table_name="student_progress",
        schema="progress",
    )
    op.drop_table("student_progress", schema="progress")
