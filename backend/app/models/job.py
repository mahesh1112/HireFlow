from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    job_id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    job_title: Mapped[str] = mapped_column(String(500), nullable=False, default="Untitled")
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Parsed requirements
    required_min_exp_years: Mapped[float] = mapped_column(Float, default=0)
    preferred_min_exp_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    nice_to_have_skills: Mapped[list] = mapped_column(JSON, default=list)
    education_required: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locations_accepted: Mapped[list] = mapped_column(JSON, default=list)
    willingness_to_relocate: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Full JD text
    job_description_full: Mapped[str] = mapped_column(Text, nullable=False)

    # Screening stats
    screening_count: Mapped[int] = mapped_column(Integer, default=0)
    screening_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None
    )  # "processing" | "completed" | "failed" | None (idle)
    screening_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )

    # ── Job lifecycle / metadata ─────────────────────────────────────────────
    business_unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("business_units.id"), nullable=True, index=True
    )
    experience: Mapped[str | None] = mapped_column(String(20), nullable=True)
    employee_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location_office: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remote_job: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    hiring_leads: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    recruiter_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    valid_till: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<JobDescription {self.job_title}>"
