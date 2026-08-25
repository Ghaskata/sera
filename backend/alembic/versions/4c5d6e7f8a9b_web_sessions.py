"""add web sessions and allow unauthenticated OAuth states

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4c5d6e7f8a9b"
down_revision: Union[str, None] = "3b4c5d6e7f8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("oauth_states", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.create_table(
        "web_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_hash"),
    )
    op.create_index("ix_web_sessions_session_hash", "web_sessions", ["session_hash"])
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])
    op.create_index("ix_web_sessions_workspace_id", "web_sessions", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_web_sessions_workspace_id", table_name="web_sessions")
    op.drop_index("ix_web_sessions_user_id", table_name="web_sessions")
    op.drop_index("ix_web_sessions_session_hash", table_name="web_sessions")
    op.drop_table("web_sessions")
    op.alter_column("oauth_states", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
