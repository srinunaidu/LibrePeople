from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Identity,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # The role is a constrained value, not a free string.
    #
    # The column is a VARCHAR(50) — the same type it has always been — with a
    # CHECK constraint that admits only the five roles the platform defines.
    # The constraint is the database's, so a row cannot hold anything else
    # however it was written; the enum additionally refuses an unknown value
    # before the statement is sent, so the API answers 422 rather than
    # letting the database raise an integrity error.
    #
    # `native_enum=False` keeps the column a VARCHAR on every dialect, so
    # this does not introduce a database-specific type. On Oracle the
    # constraint is added by the migration that introduced it; on a fresh
    # database `create_all()` emits the same DDL.
    role: Mapped[str] = mapped_column(
        SAEnum(
            "SuperAdmin",
            "HR",
            "Manager",
            "Associate",
            "PayrollViewer",
            name="user_role",
            native_enum=False,
            create_constraint=True,
            length=50,
        ),
        default="Associate",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    #: SCIM provisioning external identifier (``externalId``). Nullable: only
    #: SCIM-provisioned rows carry one. Uniqueness is enforced in the SCIM
    #: router (idempotent create on ``externalId``), not by a DB constraint,
    #: so a pre-existing database with ad-hoc values still migrates.
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    employee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), unique=True, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Credential lifecycle ------------------------------------------------
    #
    # Set when the account is created or its password is reset by an
    # administrator. While it is true the account can do exactly three
    # things: read its own profile, change its password, and sign out.
    # See `app.api.deps.get_current_active_user`.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # When the password was last changed. Used by the reuse policy and shown
    # to an administrator reviewing an account.
    password_changed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Consecutive failed logins and the lockout expiry. Reset on a successful
    # login. The lockout is per account; the per-IP rate limit in
    # `app.core.rate_limit` is a separate, complementary control.
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: When the current failure window opened. A failure more than
    #: LOGIN_FAILURE_WINDOW_SECONDS after this starts a new window, so five
    #: failures must fall inside one 15-minute window to lock the account.
    failed_login_window_started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # The last N password hashes, newest first, as a JSON array. Used to
    # refuse reuse. Stored as hashes (never plaintext) and compared by
    # verifying the candidate against each entry.
    password_history: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Multi-factor authentication ---------------------------------------
    #
    # MFA is mandatory for SuperAdmin and HR roles. When enabled, the account
    # must present a valid TOTP code (or a single-use recovery code) before
    # performing privileged operations.
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # The encrypted TOTP secret envelope (``ENCv1:<key_id>:<fernet token>``,
    # ~150-160 chars) — never the plaintext secret. Sized as TEXT on
    # purpose: VARCHAR(64) truncated the envelope on PostgreSQL (see
    # migration 0048_mfa_secret_envelope).
    mfa_secret_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When MFA was enrolled.
    mfa_enrolled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # bcrypt hashes of single-use recovery codes, as a JSON array. Consumed
    # codes are removed from the list.
    recovery_codes_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee")

    # -- helpers ----------------------------------------------------------- #

    def is_locked(self, now=None) -> bool:
        """True while the account is inside a lockout window."""
        from datetime import timezone

        if self.locked_until is None:
            return False
        now = now or datetime_now_utc()
        until = self.locked_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > now

    def password_history_hashes(self) -> list[str]:
        """The stored password history as a list of hashes, newest first."""
        import json

        if not self.password_history:
            return []
        try:
            data = json.loads(self.password_history)
        except (TypeError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, str)]

    def recovery_code_hashes(self) -> list[str]:
        """The stored recovery-code hashes as a list, newest first."""
        import json

        if not self.recovery_codes_hash:
            return []
        try:
            data = json.loads(self.recovery_codes_hash)
        except (TypeError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, str)]

    def record_password_change(self, new_hash: str, history_depth: int = 5) -> None:
        """Store the new hash and push the previous one into the history."""
        import json
        from datetime import datetime, timezone

        history = self.password_history_hashes()
        if self.hashed_password:
            history.insert(0, self.hashed_password)
        self.hashed_password = new_hash
        self.password_history = json.dumps(history[:history_depth])
        self.password_changed_at = datetime.now(timezone.utc)
        self.must_change_password = False
        self.failed_login_count = 0
        self.locked_until = None


def datetime_now_utc():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
