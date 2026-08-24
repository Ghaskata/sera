import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConnectorStatus:
    PENDING = "pending"
    CONNECTED = "connected"
    NEEDS_REAUTH = "needs_reauth"


class Connector(Base):
    __tablename__ = "connectors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True)
    provider: Mapped[str] = mapped_column(String)  # 'google_drive'
    oauth_tokens_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String, default=ConnectorStatus.PENDING)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    drive_start_page_token: Mapped[str | None] = mapped_column(String, nullable=True)
