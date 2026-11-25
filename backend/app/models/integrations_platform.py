from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Identity,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class SSOConfig(Base):
    """SSO/SAML/OIDC configuration for a client (tenant)."""

    __tablename__ = "sso_configs"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)  # SAML, OIDC, OAuth2
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sso_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    certificate: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_id_ext: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)  # encrypted
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SCIMToken(Base):
    """A SCIM provisioning bearer token."""

    __tablename__ = "scim_tokens"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Webhook(Base):
    """An outbound webhook subscription."""

    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[str] = mapped_column(Text, nullable=False)  # comma-separated event names
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)  # encrypted
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookDelivery(Base):
    """A delivery attempt for a webhook event."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    webhook_id: Mapped[int] = mapped_column(Integer, ForeignKey("webhooks.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Delivered, Failed
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    webhook = relationship("Webhook")


class BackgroundCheck(Base):
    """A background check request for a candidate."""

    __tablename__ = "background_checks"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidates.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(60), default="manual")  # manual, checkr, hireright
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, In Progress, Clear, Consider, Failed
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate")


class ESignature(Base):
    """An electronic signature request on a document."""

    __tablename__ = "e_signatures"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)  # Offer, Contract, Policy, NDA
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Sent, Signed, Declined, Expired
    provider: Mapped[str] = mapped_column(String(40), default="internal")  # internal, docusign, adobe
    provider_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    signed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
