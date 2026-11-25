from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, Identity, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    min_salary: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_salary: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    department = relationship("Department")
    employees = relationship("Employee", back_populates="job")
