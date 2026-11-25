from sqlalchemy import String, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, Text, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class JobRequisition(Base):
    __tablename__ = "job_requisitions"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    req_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    job_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employment_type: Mapped[str] = mapped_column(String(30), default="Full-time")  # Full-time, Part-time, Contract
    openings: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Open, OnHold, Closed
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    closing_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department")
    applications = relationship("Application", back_populates="requisition")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Referral, LinkedIn, Portal, Agency
    resume_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Applied")  # Applied, Screening, Interview, Offer, Hired, Rejected
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    applications = relationship("Application", back_populates="candidate")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    requisition_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_requisitions.id"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidates.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Applied")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_date: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    requisition = relationship("JobRequisition", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    offers = relationship("Offer", back_populates="application")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    offer_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), nullable=False)
    job_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)
    salary_offered: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    offer_date: Mapped[Date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Sent, Accepted, Declined, Expired
    letter_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="offers")
