from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Identity,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="General")  # Documents, IT, Facilities, Training, General
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, InProgress, Completed
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")


class OnboardingDocument(Base):
    __tablename__ = "onboarding_documents"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)  # IDProof, TaxForm, BankDetails, Contract, Certificate
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Verified, Rejected
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")


class TenantPresetState(Base):
    """The deployment's preset state.

    One deployment serves one customer, so this state is deployment level:
    there is one row, and it is the row whose ``scope`` is
    ``deployment``.

    It holds three things:

    * **the preset the deployment uses**, with the version it uses, so that
      a preset that is later corrected does not silently change what the
      deployment is running;
    * **the modules the deployment switched on**, and
    * **the settings it configured**, each with where the value came from:
      the preset's default, the customer's own value, or the customer's
      change to a value the preset suggested.

    The provenance is the point of the table. A customer who overrode a
    preset is a customer whose configuration is theirs, and the product has
    to be able to say so later without asking them.
    """

    __tablename__ = "tenant_preset_state"
    __table_args__ = (
        UniqueConstraint("scope", name="uq_tenant_preset_state_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    scope: Mapped[str] = mapped_column(String(40), default="deployment", nullable=False)
    preset_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preset_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    modules_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    preset_document: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
