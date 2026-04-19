"""Phase 7 notification dead letter queue.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-19
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
    op.create_table(
        "dead_letter_messages",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("partition", sa.Integer(), nullable=False),
        sa.Column("offset", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "raw_message", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
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
        schema="notification",
    )
    op.create_index(
        "idx_dead_letter_topic_created",
        "dead_letter_messages",
        ["topic", "created_at"],
        schema="notification",
    )
    op.create_index(
        "idx_dead_letter_replayed",
        "dead_letter_messages",
        ["replayed_at"],
        schema="notification",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dead_letter_replayed", table_name="dead_letter_messages", schema="notification"
    )
    op.drop_index(
        "idx_dead_letter_topic_created", table_name="dead_letter_messages", schema="notification"
    )
    op.drop_table("dead_letter_messages", schema="notification")
