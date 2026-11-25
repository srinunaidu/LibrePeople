from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime

# Roles that may be granted through the API. Self-service registration can never
# create anything above the least-privileged role (see auth.register).
VALID_ROLES = ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")
SELF_SERVICE_ROLE = "Associate"


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = SELF_SERVICE_ROLE
    is_active: bool = True

    @field_validator("role")
    @classmethod
    def role_must_be_known(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {', '.join(VALID_ROLES)}")
        return v


class UserSelfRegister(BaseModel):
    """Payload accepted by the public self-service registration endpoint.

    Deliberately has no `role` or `is_active` field. Because FastAPI/Pydantic
    ignore unknown keys by default, a caller that sends `"role": "SuperAdmin"`
    cannot escalate: the value is not bound to the model at all, and the
    endpoint additionally constructs the row with hard-coded least privilege.
    """

    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_must_be_sane(cls, v: str) -> str:
        v = v.strip()
        if not (3 <= len(v) <= 100):
            raise ValueError("username must be 3-100 characters")
        if not all(c.isalnum() or c in "._-" for c in v):
            raise ValueError(
                "username may only contain letters, digits, and . _ -"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("password must be at least 12 characters")
        if v.lower() == v or v.upper() == v or not any(c.isdigit() for c in v):
            raise ValueError(
                "password must mix upper case, lower case and digits"
            )
        return v


class UserCreate(UserBase):
    """Privileged user creation (administrators only, not public)."""

    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("role")
    @classmethod
    def role_must_be_known(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"role must be one of {', '.join(VALID_ROLES)}")
        return v


class UserOut(UserBase):
    id: int
    created_at: datetime
    must_change_password: bool = False
    password_changed_at: Optional[datetime] = None
    is_locked: bool = False

    # The email is returned as a plain string, not an `EmailStr`.
    #
    # `EmailStr` is an *input* constraint: it stops a caller creating an
    # account with an address that cannot exist. Applying it to a response
    # model means a stored value that predates the rule — or that came from
    # an import — makes the endpoint fail with a 500 instead of returning
    # the row. A response model must be able to describe what is stored.
    # `UserCreate` keeps the strict validation.
    email: str

    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            must_change_password=bool(getattr(user, "must_change_password", False)),
            password_changed_at=getattr(user, "password_changed_at", None),
            is_locked=bool(user.is_locked()),
            mfa_enabled=bool(getattr(user, "mfa_enabled", False)),
        )


class PasswordChangeRequest(BaseModel):
    """Self-service password change.

    The current password is required even though the caller is already
    authenticated: it proves the session holder is the account holder, which
    matters most exactly when a session was hijacked.
    """

    current_password: str
    new_password: str


class AdminPasswordSetRequest(BaseModel):
    """Administrator-set password.

    The account is left in a ``must_change_password`` state, so the user is
    forced to replace the administrator-chosen password at first sign-in.
    """

    new_password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    role: str
    username: str
    must_change_password: bool = False
    mfa_enabled: bool = False


class MFAEnrollResponse(BaseModel):
    """MFA enrollment data — returned once, at enrollment time.

    The secret and recovery codes are never returned again. If lost, the
    user must re-enroll (disable + enroll) or ask an administrator to reset.
    """

    provisioning_uri: str
    recovery_codes: list[str]
    #: The provisioning URI as a PNG data URI. Rendered by the server so the
    #: TOTP secret is never sent to a third-party image service.
    qr_code_data_uri: str | None = None


class MFAConfirmRequest(BaseModel):
    """Verify a TOTP code to complete MFA enrollment."""

    totp_code: str


class MFADisableRequest(BaseModel):
    """Disable MFA — requires either the current password or a recovery code."""

    password: str | None = None
    recovery_code: str | None = None


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    mfa_enrolled_at: datetime | None = None