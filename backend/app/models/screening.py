import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    result_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_descriptions.job_id"), nullable=False, index=True
    )

    # Ranking
    rank: Mapped[int] = mapped_column(Integer, default=0)
    fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(20), default="POOR"
    )  # EXCELLENT / GOOD / ADEQUATE / POOR

    # Knockout
    passed_knockouts: Mapped[bool] = mapped_column(Boolean, default=True)
    knockout_failures: Mapped[list] = mapped_column(JSON, default=list)

    # Category scores
    skills_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    experience_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    career_progression_score: Mapped[float] = mapped_column(Float, default=0.0)
    achievements_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Explanation
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    match_explanation: Mapped[str] = mapped_column(Text, default="")

    # Skills
    skills_matched: Mapped[list] = mapped_column(JSON, default=list)
    skills_missing: Mapped[list] = mapped_column(JSON, default=list)

    # Candidate snapshot (denormalised)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_exp_years: Mapped[float] = mapped_column(Float, default=0.0)

    # Actions
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Performance
    screening_time_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ScreeningResult {self.candidate_name} score={self.fit_score}>"
