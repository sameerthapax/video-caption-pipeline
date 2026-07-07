from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_bucket: Mapped[str] = mapped_column(String(255), default="videos")
    video_path: Mapped[str] = mapped_column(String(500))
    upload_content_type: Mapped[str] = mapped_column(String(255), default="application/octet-stream")
    upload_file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending_upload")
    current_step: Mapped[str] = mapped_column(String(64), default="awaiting_upload")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    result: Mapped[VideoCaptionResult] = relationship(
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )


class VideoCaptionResult(Base):
    __tablename__ = "video_caption_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("video_jobs.id", ondelete="CASCADE"), unique=True)
    neutral_summary: Mapped[str] = mapped_column(Text)
    formal_caption: Mapped[str] = mapped_column(Text)
    sarcastic_caption: Mapped[str] = mapped_column(Text)
    humorous_tech_caption: Mapped[str] = mapped_column(Text)
    humorous_non_tech_caption: Mapped[str] = mapped_column(Text)
    raw_output_json: Mapped[dict] = mapped_column("raw_pipeline_json", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job: Mapped[VideoJob] = relationship(back_populates="result")
