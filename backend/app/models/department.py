from sqlalchemy import String, Boolean, Integer, Text, Identity, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (Index("ix_departments_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    employees = relationship("Employee", back_populates="department")
