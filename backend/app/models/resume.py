import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey, func, Enum as SAEnum, LargeBinary, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    batch_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "processing", "completed", "failed", name="batch_status"),
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("upload_batches.batch_id"), nullable=True
    )

    # Multi-unit collaboration fields (Gap 11.11 + 11.12)
    unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("business_units.id"), nullable=True, index=True
    )
    job_position_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("job_descriptions.job_id"), nullable=True, index=True
    )

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # deprecated — use resume_file
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # PostgreSQL BYTEA storage (Gap 11.14)
    resume_file: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    file_mimetype: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # SHA-256 hash for deduplication (scoped per job_position_id)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Parsing status
    upload_status: Mapped[str] = mapped_column(
        SAEnum("pending", "processing", "completed", "failed", name="upload_status"),
        default="pending",
    )
    parse_status: Mapped[str] = mapped_column(
        SAEnum("pending", "processing", "completed", "failed", name="parse_status"),
        default="pending",
    )

    # Parsed data (JSON blob)
    parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Candidate info (denormalised for fast querying)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_exp_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    all_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Pinecone vector ID
    pinecone_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Compound index for unit-scoped job position queries
    __table_args__ = (
        Index("ix_resumes_unit_job", "unit_id", "job_position_id"),
    )

    def __repr__(self) -> str:
        return f"<Resume {self.filename}>"
