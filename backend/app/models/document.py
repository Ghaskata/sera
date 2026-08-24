import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True)
    connector_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connectors.id"), index=True)
    external_id: Mapped[str] = mapped_column(String, index=True)  # Drive file id
    title: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    drive_link: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
