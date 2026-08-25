"""add work intelligence entities

Revision ID: 2a3b4c5d6e7f
Revises: 1f2c3d4e5f6a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2a3b4c5d6e7f"
down_revision: Union[str, None] = "1f2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("action_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_events_workspace_id", "work_events", ["workspace_id"])
    op.create_index("ix_work_events_action_key", "work_events", ["action_key"])
    op.create_index("ix_work_events_occurred_at", "work_events", ["occurred_at"])

    op.create_table(
        "automation_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("frequency_count", sa.Integer(), nullable=False),
        sa.Column("total_minutes", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("workflow", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_candidates_workspace_id", "automation_candidates", ["workspace_id"])
    op.create_index("ix_automation_candidates_action_key", "automation_candidates", ["action_key"])

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["automation_candidates.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approvals_workspace_id", "approvals", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_approvals_workspace_id", table_name="approvals")
    op.drop_table("approvals")
    op.drop_index("ix_automation_candidates_action_key", table_name="automation_candidates")
    op.drop_index("ix_automation_candidates_workspace_id", table_name="automation_candidates")
    op.drop_table("automation_candidates")
    op.drop_index("ix_work_events_occurred_at", table_name="work_events")
    op.drop_index("ix_work_events_action_key", table_name="work_events")
    op.drop_index("ix_work_events_workspace_id", table_name="work_events")
    op.drop_table("work_events")
