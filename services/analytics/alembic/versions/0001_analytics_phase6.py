"""Phase 6 analytics tables.

Revision ID: 0001
Revises: None
Create Date: 2026-04-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.create_table(
        "event_store",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_type", sa.String(length=100), nullable=True),
        sa.Column("aggregate_id", sa.String(length=100), nullable=True),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("source_service", sa.String(length=100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "raw_event", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.PrimaryKeyConstraint("id"),
        schema="analytics",
    )
    op.create_index(
        "idx_event_store_event_id", "event_store", ["event_id"], unique=True, schema="analytics"
    )
    op.create_index(
        "idx_event_store_type_time",
        "event_store",
        ["event_type", "occurred_at"],
        schema="analytics",
    )
    op.create_index("idx_event_store_course", "event_store", ["course_id"], schema="analytics")

    op.create_table(
        "daily_metrics",
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("total_students", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrollments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_courses", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("metric_date"),
        schema="analytics",
    )

    op.create_table(
        "course_metrics",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("instructor_id", sa.Uuid(), nullable=True),
        sa.Column("course_title", sa.String(length=300), nullable=True),
        sa.Column("total_enrollments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_completions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_version_id", sa.Uuid(), nullable=True),
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
        sa.PrimaryKeyConstraint("course_id"),
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_table("course_metrics", schema="analytics")
    op.drop_table("daily_metrics", schema="analytics")
    op.drop_index("idx_event_store_course", table_name="event_store", schema="analytics")
    op.drop_index("idx_event_store_type_time", table_name="event_store", schema="analytics")
    op.drop_index("idx_event_store_event_id", table_name="event_store", schema="analytics")
    op.drop_table("event_store", schema="analytics")
