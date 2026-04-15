"""Phase 3 foundation: manifest and review artifacts.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "idx_one_publishing_per_course",
        table_name="course_versions",
        schema="publishing",
    )

    op.add_column(
        "course_versions",
        sa.Column("approval_state", sa.String(length=20), nullable=False, server_default="PENDING"),
        schema="publishing",
    )
    op.add_column(
        "course_versions",
        sa.Column("manifest_hash", sa.String(length=64), nullable=False, server_default=""),
        schema="publishing",
    )
    op.add_column(
        "course_versions",
        sa.Column("preflight_summary_json", postgresql.JSONB(), nullable=True),
        schema="publishing",
    )
    op.add_column(
        "course_versions",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        schema="publishing",
    )
    op.add_column(
        "course_versions",
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        schema="publishing",
    )

    op.execute(
        "UPDATE publishing.course_versions "
        "SET approval_state = CASE WHEN status = 'READY' THEN 'APPROVED' ELSE 'PENDING' END"
    )
    op.execute("ALTER TABLE publishing.course_versions DROP CONSTRAINT ck_course_versions_status")
    op.create_check_constraint(
        "ck_course_versions_status",
        "course_versions",
        "status IN ('PREPARING', 'REVIEW_REQUIRED', 'PUBLISHING', 'READY', 'FAILED', 'CANCELLED', 'SUPERSEDED')",
        schema="publishing",
    )
    op.create_check_constraint(
        "ck_course_versions_approval_state",
        "course_versions",
        "approval_state IN ('PENDING', 'APPROVED', 'REJECTED')",
        schema="publishing",
    )
    op.alter_column(
        "course_versions",
        "status",
        schema="publishing",
        server_default="PREPARING",
    )
    op.create_index(
        "idx_one_publishing_per_course",
        "course_versions",
        ["course_id"],
        unique=True,
        schema="publishing",
        postgresql_where=sa.text("status IN ('PREPARING', 'REVIEW_REQUIRED', 'PUBLISHING')"),
    )

    op.create_table(
        "version_manifests",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.course_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("instructor_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("slug", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("estimated_duration", sa.String(length=32), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", name="uq_version_manifests_version_id"),
        schema="publishing",
    )
    op.create_index(
        "idx_version_manifests_version",
        "version_manifests",
        ["version_id"],
        schema="publishing",
    )

    op.create_table(
        "version_manifest_modules",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.course_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "manifest_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.version_manifests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("estimated_duration", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="publishing",
    )
    op.create_index(
        "idx_version_manifest_modules_version",
        "version_manifest_modules",
        ["version_id"],
        schema="publishing",
    )
    op.create_index(
        "idx_version_manifest_modules_manifest",
        "version_manifest_modules",
        ["manifest_id"],
        schema="publishing",
    )

    op.create_table(
        "version_manifest_assets",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.course_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "manifest_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.version_manifests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "manifest_module_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.version_manifest_modules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("page_estimate", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="publishing",
    )
    op.create_index(
        "idx_version_manifest_assets_version",
        "version_manifest_assets",
        ["version_id"],
        schema="publishing",
    )
    op.create_index(
        "idx_version_manifest_assets_manifest",
        "version_manifest_assets",
        ["manifest_id"],
        schema="publishing",
    )
    op.create_index(
        "idx_version_manifest_assets_module",
        "version_manifest_assets",
        ["manifest_module_id"],
        schema="publishing",
    )

    op.create_table(
        "version_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("publishing.course_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("object_path", sa.String(length=1000), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False, server_default="application/json"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="publishing",
    )
    op.create_index(
        "idx_version_artifacts_version",
        "version_artifacts",
        ["version_id"],
        schema="publishing",
    )
    op.create_index(
        "idx_version_artifacts_type",
        "version_artifacts",
        ["artifact_type"],
        schema="publishing",
    )


def downgrade() -> None:
    op.drop_index("idx_version_artifacts_type", table_name="version_artifacts", schema="publishing")
    op.drop_index("idx_version_artifacts_version", table_name="version_artifacts", schema="publishing")
    op.drop_table("version_artifacts", schema="publishing")
    op.drop_index("idx_version_manifest_assets_module", table_name="version_manifest_assets", schema="publishing")
    op.drop_index("idx_version_manifest_assets_manifest", table_name="version_manifest_assets", schema="publishing")
    op.drop_index("idx_version_manifest_assets_version", table_name="version_manifest_assets", schema="publishing")
    op.drop_table("version_manifest_assets", schema="publishing")
    op.drop_index("idx_version_manifest_modules_manifest", table_name="version_manifest_modules", schema="publishing")
    op.drop_index("idx_version_manifest_modules_version", table_name="version_manifest_modules", schema="publishing")
    op.drop_table("version_manifest_modules", schema="publishing")
    op.drop_index("idx_version_manifests_version", table_name="version_manifests", schema="publishing")
    op.drop_table("version_manifests", schema="publishing")
    op.drop_index("idx_one_publishing_per_course", table_name="course_versions", schema="publishing")
    op.execute("ALTER TABLE publishing.course_versions DROP CONSTRAINT ck_course_versions_approval_state")
    op.execute("ALTER TABLE publishing.course_versions DROP CONSTRAINT ck_course_versions_status")
    op.create_check_constraint(
        "ck_course_versions_status",
        "course_versions",
        "status IN ('DRAFT', 'PUBLISHING', 'READY', 'FAILED', 'CANCELLED')",
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
    op.drop_column("course_versions", "superseded_at", schema="publishing")
    op.drop_column("course_versions", "activated_at", schema="publishing")
    op.drop_column("course_versions", "preflight_summary_json", schema="publishing")
    op.drop_column("course_versions", "manifest_hash", schema="publishing")
    op.drop_column("course_versions", "approval_state", schema="publishing")