from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Identity,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class Client(Base):
    """A tenant (client organization) being onboarded onto Karmathy.

    Lifecycle (FSM)``status``::

        Draft -> Provisioning -> Active -> Suspended -> Active          (suspend/reactivate)
        Active -> Read-only -> Active                                  (read-only / reactivate)
        Active | Suspended | Read-only -> Deprovisioning -> Archived   (deprovision / archive)

    ``Archived`` is terminal. SuperAdmin may trigger every transition; a tenant
    administrator may only ``suspend`` / ``reactivate`` their own tenant.
    Break-glass is never usable for FSM or registry modification (decision 4).
    """

    #: FSM status values.
    STATUS_DRAFT = "Draft"
    STATUS_PROVISIONING = "Provisioning"
    STATUS_ACTIVE = "Active"
    STATUS_SUSPENDED = "Suspended"
    STATUS_READ_ONLY = "Read-only"
    STATUS_DEPROVISIONING = "Deprovisioning"
    STATUS_ARCHIVED = "Archived"

    #: Legal transitions ``from -> {to, ...}``. A transition to the current
    #: state is idempotent (no-op); anything else not listed here is illegal.
    _TRANSITIONS: dict[str, set[str]] = {
        STATUS_DRAFT: {STATUS_PROVISIONING},
        STATUS_PROVISIONING: {STATUS_ACTIVE, STATUS_DRAFT},
        STATUS_ACTIVE: {STATUS_SUSPENDED, STATUS_READ_ONLY, STATUS_DEPROVISIONING},
        STATUS_SUSPENDED: {STATUS_ACTIVE, STATUS_DEPROVISIONING},
        STATUS_READ_ONLY: {STATUS_ACTIVE, STATUS_DEPROVISIONING},
        STATUS_DEPROVISIONING: {STATUS_ARCHIVED},
        STATUS_ARCHIVED: set(),
    }

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(80), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    #: ISO 3166-1 alpha-2 code (IN, US, ...). The rule-pack loader selects a
    #: pack by this code, not by the free-form `country` label. Nullable:
    #: migration 0030 backfilled it only where `country` already held a
    #: two-letter code; anything else stays empty until it is set.
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    timezone: Mapped[str] = mapped_column(String(60), default="UTC")
    locale: Mapped[str] = mapped_column(String(10), default="en")
    # AD-03 tenant settings.
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)  # ISO 4217
    date_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    working_week: Mapped[str | None] = mapped_column(String(40), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(12), default="#2563EB")
    secondary_color: Mapped[str] = mapped_column(String(12), default="#1F2937")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=STATUS_DRAFT,
        nullable=False,
    )
    #: Set when the tenant moves into ``Deprovisioning``; cleared on reactivate.
    deprovisioned_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: Set when the tenant moves into ``Archived``; terminal.
    archived_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            status.in_(
                [
                    STATUS_DRAFT,
                    STATUS_PROVISIONING,
                    STATUS_ACTIVE,
                    STATUS_SUSPENDED,
                    STATUS_READ_ONLY,
                    STATUS_DEPROVISIONING,
                    STATUS_ARCHIVED,
                ]
            ),
            name="ck_client_status_fsm",
        ),
    )

    settings = relationship("ClientSetting", back_populates="client", cascade="all, delete-orphan")
    feature_flags = relationship("FeatureFlag", back_populates="client", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="client", cascade="all, delete-orphan")
    migration_jobs = relationship("MigrationJob", back_populates="client", cascade="all, delete-orphan")
    steps = relationship("OnboardingStep", back_populates="client", cascade="all, delete-orphan")

    # ------------------------------------------------------------------ #
    # FSM transition helper
    # ------------------------------------------------------------------ #

    def can_transition(self, to_state: str) -> bool:
        """True when ``to_state`` is a legal move from the current status."""
        return to_state in self._TRANSITIONS.get(self.status, set())

    def transition_to(
        self,
        to_state: str,
        *,
        actor: str | None = None,
    ) -> "Client":
        """Move the tenant to ``to_state``.

        A move to the current state is idempotent. An illegal move raises
        so the caller can return ``409 invalid_tenant_transition``.
        """
        if to_state == self.status:
            return self
        if not self.can_transition(to_state):
            from app.core.errors import conflict

            raise conflict(
                "invalid_tenant_transition",
                f"Illegal tenant lifecycle move {self.status} -> {to_state}.",
                details={"from": self.status, "to": to_state},
            )
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        self.status = to_state
        if to_state == self.STATUS_DEPROVISIONING:
            self.deprovisioned_at = now
        if to_state == self.STATUS_ACTIVE:
            # Reactivating clears a prior deprovisioning stamp.
            self.deprovisioned_at = None
        if to_state == self.STATUS_ARCHIVED:
            self.archived_at = now
        return self


class ClientSetting(Base):
    """Arbitrary key/value configuration for a client (maximum customization)."""

    __tablename__ = "client_settings"
    __table_args__ = (
        UniqueConstraint("client_id", "key", name="uq_client_setting"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client = relationship("Client", back_populates="settings")


class FeatureFlag(Base):
    """Per-client feature toggle."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("client_id", "key", name="uq_feature_flag"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client = relationship("Client", back_populates="feature_flags")


class Integration(Base):
    """A connection to an external system (migration API, DB, SFTP, webhook)."""

    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # oracle_adb, rest, sftp, csv, webhook
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)  # encrypted
    status: Mapped[str] = mapped_column(String(20), default="unconfigured")  # unconfigured, configured, tested, connected, error
    last_tested_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client = relationship("Client", back_populates="integrations")
    migration_jobs = relationship("MigrationJob", back_populates="integration")


class MigrationJob(Base):
    """A data migration run for one entity."""

    __tablename__ = "migration_jobs"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    integration_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("integrations.id"), nullable=True)
    entity: Mapped[str] = mapped_column(String(40), nullable=False)  # employees, departments, jobs, candidates, leave_balances
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued, running, succeeded, failed, cancelled
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="migration_jobs")
    integration = relationship("Integration", back_populates="migration_jobs")


class OnboardingStep(Base):
    """A step in the client onboarding checklist."""

    __tablename__ = "onboarding_steps"
    __table_args__ = (
        UniqueConstraint("client_id", "key", name="uq_onboarding_step"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="steps")
