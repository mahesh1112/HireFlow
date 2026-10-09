import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BusinessUnit(Base):
    __tablename__ = "business_units"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    unit_slug: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    unit_name: Mapped[str] = mapped_column(String(200), nullable=False)

    def __repr__(self) -> str:
        return f"<BusinessUnit {self.unit_slug}>"


class UserUnit(Base):
    __tablename__ = "user_units"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), primary_key=True
    )
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("business_units.id"), primary_key=True
    )

    def __repr__(self) -> str:
        return f"<UserUnit user={self.user_id} unit={self.unit_id}>"
