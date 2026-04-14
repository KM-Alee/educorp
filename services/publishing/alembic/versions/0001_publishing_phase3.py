"""Phase 3: create publishing schema tables.

Revision ID: 0001
Revises: (initial)
Create Date: 2026-04-14
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
    op.execute("CREATE SCHEMA IF NOT EXISTS publishing")

    op.create_table(
        "course_versions",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PUBLISHING"),
        sa.Column("initiated_by", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.String(255), nullable=True),
        sa.Column("run_id", sa.String(255), nullable=True),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("total_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_assets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHING', 'READY', 'FAILED', 'CANCELLED')",
            name="ck_course_versions_status",
        ),
        schema="publishing",
    )

    op.create_index("idx_versions_course", "course_versions", ["course_id"], schema="publishing")
    op.create_index("idx_versions_status", "course_versions", ["status"], schema="publishing")
    op.create_index(
        "idx_versions_course_number",
        "course_versions",
        ["course_id", "version_number"],
        unique=True,
        schema="publishing",
    )
    op.create_index(
        "idx_one_publishing_per_course",
        "course_versions",
        ["course_id"],
        unique=True,
        schema="publishing",
        postgresql_where=sa.text("status = 'PUBLISHING'"),
    )

    op.create_table(
        "publishing_steps",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.course_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="ck_publishing_steps_status",
        ),
        schema="publishing",
    )

    op.create_index(
        "idx_pub_steps_version",
        "publishing_steps",
        ["version_id"],
        schema="publishing",
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.course_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("text_preview", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="publishing",
    )

    op.create_index("idx_chunks_version", "chunks", ["version_id"], schema="publishing")
    op.create_index("idx_chunks_course", "chunks", ["course_id"], schema="publishing")


def downgrade() -> None:
    op.drop_table("chunks", schema="publishing")
    op.drop_table("publishing_steps", schema="publishing")
    op.drop_table("course_versions", schema="publishing")
