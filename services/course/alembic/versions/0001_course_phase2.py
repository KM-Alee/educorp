"""Phase 2: create course schema tables.

Revision ID: 0001
Revises: (initial)
Create Date: 2026-04-13
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
    op.execute("CREATE SCHEMA IF NOT EXISTS course")

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instructor_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("slug", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("estimated_duration", sa.Interval(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("is_public_preview", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_capacity", sa.Integer(), nullable=True),
        sa.Column("prerequisites", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint("difficulty IN ('beginner', 'intermediate', 'advanced')", name="ck_courses_difficulty"),
        sa.CheckConstraint("visibility IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name="ck_courses_visibility"),
        schema="course",
    )

    op.create_index("idx_courses_instructor", "courses", ["instructor_id"], schema="course", postgresql_where="deleted_at IS NULL")
    op.create_index("idx_courses_visibility", "courses", ["visibility"], schema="course", postgresql_where="deleted_at IS NULL")
    op.create_index("idx_courses_category", "courses", ["category"], schema="course", postgresql_where="deleted_at IS NULL")
    op.create_index("idx_courses_slug", "courses", ["slug"], schema="course")
    op.create_index("idx_courses_tags", "courses", ["tags"], schema="course", postgresql_using="gin")

    op.create_table(
        "modules",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("estimated_duration", sa.Interval(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "sort_order", name="uq_modules_course_sort"),
        schema="course",
    )

    op.create_index("idx_modules_course", "modules", ["course_id"], schema="course")

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id", sa.Uuid(), sa.ForeignKey("course.modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upload_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("asset_type IN ('pdf', 'docx', 'pptx', 'txt', 'md', 'vtt', 'srt')", name="ck_assets_type"),
        sa.CheckConstraint("upload_status IN ('PENDING', 'UPLOADED', 'FAILED')", name="ck_assets_upload_status"),
        schema="course",
    )

    op.create_index("idx_assets_module", "assets", ["module_id"], schema="course")


def downgrade() -> None:
    op.drop_table("assets", schema="course")
    op.drop_table("modules", schema="course")
    op.drop_table("courses", schema="course")
