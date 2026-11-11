from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from infra.database import Base


class UTCDateTime(TypeDecorator):
    """Stores UTC and always returns timezone-aware datetimes (SQLite drops the tzinfo)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime cannot be stored; use timezone-aware values")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class PromptModel(Base):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), index=True)
    active_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_before_deletion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    # lazy="raise": async sessions cannot lazy-load, so every query must eager-load explicitly.
    versions: Mapped[list["PromptVersionModel"]] = relationship(
        back_populates="prompt",
        order_by="PromptVersionModel.number",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class PromptVersionModel(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("prompt_id", "number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)

    prompt: Mapped[PromptModel] = relationship(back_populates="versions", lazy="raise")
