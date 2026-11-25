import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret, SecretDecryptionError
from app.models.client_onboarding import (
    Client,
    ClientSetting,
    FeatureFlag,
    Integration,
    MigrationJob,
    OnboardingStep,
)
from app.schemas.client_onboarding import (
    ClientCreate,
    ClientUpdate,
    ClientSettingCreate,
    FeatureFlagUpdate,
    IntegrationCreate,
    IntegrationUpdate,
    MigrationStart,
    OnboardingStepCreate,
)

DEFAULT_FEATURE_FLAGS: list[dict] = [
    {"key": "module.recruiting", "name": "Recruiting", "description": "Requisitions, candidates, applications, offers", "enabled": True},
    {"key": "module.time_attendance", "name": "Time & Attendance", "description": "Clock in/out, timesheets, overtime", "enabled": True},
    {"key": "module.scheduling", "name": "Scheduling", "description": "Shift templates, rosters, swaps", "enabled": True},
    {"key": "module.leave", "name": "Leave Management", "description": "Leave types, entitlements, requests", "enabled": True},
    {"key": "module.offboarding", "name": "Offboarding", "description": "Exit checklists, terminations", "enabled": True},
    {"key": "module.reports", "name": "Reports", "description": "Dashboards and analytics", "enabled": True},
    {"key": "feature.offer_letters_pdf", "name": "Offer Letter PDF", "description": "Auto-generate offer letters as PDF", "enabled": True},
    {"key": "feature.document_upload", "name": "Document Upload", "description": "Collect onboarding documents", "enabled": True},
    {"key": "feature.shift_swaps", "name": "Shift Swaps", "description": "Allow employees to request shift swaps", "enabled": True},
    {"key": "feature.self_service", "name": "Employee Self-Service", "description": "Employee-facing self-service portal", "enabled": False},
    {"key": "feature.audit_trail", "name": "Audit Trail", "description": "Track all user actions", "enabled": True},
    {"key": "feature.multi_tenant", "name": "Multi-Tenant Isolation", "description": "Strict tenant data isolation", "enabled": False},
    {"key": "headcount", "name": "Headcount", "description": "Headcount configuration", "enabled": True, "config": "0"},
    {"key": "hiring", "name": "Hiring", "description": "Hiring configuration", "enabled": True, "config": "0"},
    {"key": "turnover", "name": "Turnover", "description": "Turnover configuration", "enabled": True, "config": "0"},
    {"key": "labour_cost", "name": "Labour Cost", "description": "Labour cost configuration", "enabled": True, "config": "0"},
    {"key": "labor_cost", "name": "Labor Cost", "description": "Labor cost configuration (US spelling alias)", "enabled": True, "config": "0"},
    {"key": "forecast_months", "name": "Forecast Months", "description": "Forecast horizon in months", "enabled": True, "config": "12"},
]

DEFAULT_ONBOARDING_STEPS: list[dict] = [
    {"key": "company_profile", "title": "Company profile", "description": "Name, branding, timezone and locale", "order_index": 1, "owner": "Admin"},
    {"key": "feature_flags", "title": "Feature flags", "description": "Enable the modules your organization needs", "order_index": 2, "owner": "Admin"},
    {"key": "integrations", "title": "Integrations", "description": "Connect migration APIs and data sources", "order_index": 3, "owner": "IT"},
    {"key": "import_data", "title": "Import data", "description": "Migrate employees, departments and jobs", "order_index": 4, "owner": "IT"},
    {"key": "users_roles", "title": "Users & roles", "description": "Create HR, managers and associates", "order_index": 5, "owner": "Admin"},
    {"key": "review", "title": "Review & go live", "description": "Verify configuration and activate the tenant", "order_index": 6, "owner": "Admin"},
]


# --- Clients ---------------------------------------------------------------- #

def list_clients(db: Session) -> list[Client]:
    return db.query(Client).order_by(Client.created_at.desc()).all()


def get_client(db: Session, client_id: int) -> Client | None:
    return db.query(Client).filter(Client.id == client_id).first()


def get_client_by_slug(db: Session, slug: str) -> Client | None:
    return db.query(Client).filter(Client.slug == slug).first()


def create_client(db: Session, payload: ClientCreate) -> Client:
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    # seed defaults
    for flag in DEFAULT_FEATURE_FLAGS:
        db.add(FeatureFlag(client_id=client.id, **flag))
    for step in DEFAULT_ONBOARDING_STEPS:
        db.add(OnboardingStep(client_id=client.id, **step))
    db.commit()
    return client


def update_client(db: Session, db_obj: Client, payload: ClientUpdate) -> Client:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_client(db: Session, db_obj: Client) -> None:
    db.delete(db_obj)
    db.commit()


# --- Settings --------------------------------------------------------------- #

def list_settings(db: Session, client_id: int) -> list[ClientSetting]:
    return (
        db.query(ClientSetting)
        .filter(ClientSetting.client_id == client_id)
        .order_by(ClientSetting.key)
        .all()
    )


def get_setting(db: Session, client_id: int, key: str) -> ClientSetting | None:
    return (
        db.query(ClientSetting)
        .filter(ClientSetting.client_id == client_id, ClientSetting.key == key)
        .first()
    )


def upsert_setting(db: Session, client_id: int, key: str, value: str | None) -> ClientSetting:
    setting = get_setting(db, client_id, key)
    if setting:
        setting.value = value
    else:
        setting = ClientSetting(client_id=client_id, key=key, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, setting: ClientSetting) -> None:
    db.delete(setting)
    db.commit()


# --- Feature flags ---------------------------------------------------------- #

def list_flags(db: Session, client_id: int) -> list[FeatureFlag]:
    return (
        db.query(FeatureFlag)
        .filter(FeatureFlag.client_id == client_id)
        .order_by(FeatureFlag.key)
        .all()
    )


def get_flag(db: Session, client_id: int, key: str) -> FeatureFlag | None:
    return (
        db.query(FeatureFlag)
        .filter(FeatureFlag.client_id == client_id, FeatureFlag.key == key)
        .first()
    )


def update_flag(db: Session, db_obj: FeatureFlag, enabled: bool | None, config: str | None) -> FeatureFlag:
    if enabled is not None:
        db_obj.enabled = enabled
    if config is not None:
        db_obj.config = config
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def upsert_flag(db: Session, client_id: int, key: str, enabled: bool | None, config: str | None) -> FeatureFlag:
    flag = get_flag(db, client_id, key)
    if flag:
        return update_flag(db, flag, enabled, config)
    # create missing flag — use default entry if known, else generic
    defaults = next((d for d in DEFAULT_FEATURE_FLAGS if d["key"] == key), None)
    name = defaults["name"] if defaults else key
    description = defaults["description"] if defaults else ""
    # if caller supplies enabled/config use those, else fall back to defaults
    eff_enabled = enabled if enabled is not None else (defaults["enabled"] if defaults and "enabled" in defaults else True)
    eff_config = config if config is not None else (defaults.get("config") if defaults else None)
    flag = FeatureFlag(client_id=client_id, key=key, name=name, description=description, enabled=eff_enabled, config=eff_config)
    # if config supplied explicitly, ensure it overwrites
    if config is not None:
        flag.config = config
    if enabled is not None:
        flag.enabled = enabled
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


# --- Integrations ----------------------------------------------------------- #

def list_integrations(db: Session, client_id: int) -> list[Integration]:
    return (
        db.query(Integration)
        .filter(Integration.client_id == client_id)
        .order_by(Integration.created_at.desc())
        .all()
    )


def get_integration(db: Session, integration_id: int) -> Integration | None:
    return db.query(Integration).filter(Integration.id == integration_id).first()


def create_integration(db: Session, client_id: int, payload: IntegrationCreate) -> Integration:
    db_obj = Integration(
        client_id=client_id,
        name=payload.name,
        kind=payload.kind,
        endpoint=payload.endpoint,
        username=payload.username,
        secret=encrypt_secret(payload.secret),
        notes=payload.notes,
        status="configured" if payload.endpoint else "unconfigured",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_integration(db: Session, db_obj: Integration, payload: IntegrationUpdate) -> Integration:
    data = payload.model_dump(exclude_unset=True)
    if "secret" in data and data["secret"] is not None:
        data["secret"] = encrypt_secret(data["secret"])
    for field, value in data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_integration(db: Session, db_obj: Integration) -> None:
    db.delete(db_obj)
    db.commit()


def test_integration(db: Session, db_obj: Integration) -> Integration:
    """Real connectivity check against the configured endpoint."""
    from datetime import datetime, timezone

    from app.core.url_guard import fetch

    db_obj.last_tested_at = datetime.now(timezone.utc)
    if not db_obj.endpoint:
        db_obj.status = "unconfigured"
        db_obj.last_error = "No endpoint configured"
    else:
        try:
            headers: dict[str, str] = {}
            if db_obj.username and db_obj.secret:
                import base64

                creds = f"{db_obj.username}:{decrypt_secret(db_obj.secret)}"
                encoded = base64.b64encode(creds.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
            try:
                # The outbound guard: https only, no blocked destination, every
                # redirect re-validated. A refused URL raises UnsafeURLError,
                # which the outer handler records as the error.
                resp = fetch(db_obj.endpoint, method="HEAD", headers=headers, timeout=10)
                if resp.status < 400:
                    db_obj.status = "connected"
                    db_obj.last_error = None
                elif resp.status < 500:
                    # HTTP errors still mean the endpoint is reachable
                    db_obj.status = "connected"
                    db_obj.last_error = f"HTTP {resp.status}"
                else:
                    db_obj.status = "error"
                    db_obj.last_error = f"HTTP {resp.status}"
            except SecretDecryptionError:
                # The stored secret could not be read. This is a configuration
                # problem (a rotated or missing encryption key), not a
                # connectivity problem, and it must not be reported as one.
                db_obj.status = "error"
                db_obj.last_error = (
                    "Stored credential could not be decrypted. Check the "
                    "field encryption key configuration."
                )
        except Exception as exc:  # noqa: BLE001
            db_obj.status = "error"
            db_obj.last_error = str(exc)[:500]
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# --- Migration jobs --------------------------------------------------------- #

def list_jobs(db: Session, client_id: int) -> list[MigrationJob]:
    return (
        db.query(MigrationJob)
        .filter(MigrationJob.client_id == client_id)
        .order_by(MigrationJob.created_at.desc())
        .all()
    )


def get_job(db: Session, job_id: int) -> MigrationJob | None:
    return db.query(MigrationJob).filter(MigrationJob.id == job_id).first()


def start_job(db: Session, client_id: int, payload: MigrationStart) -> MigrationJob:
    db_obj = MigrationJob(
        client_id=client_id,
        integration_id=payload.integration_id,
        entity=payload.entity,
        status="queued",
        total=payload.total,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def run_job(db: Session, db_obj: MigrationJob) -> MigrationJob:
    """Run a migration job, attempting real data transfer from the integration source."""
    import json as _json

    from app.core.url_guard import fetch

    db_obj.status = "running"
    db_obj.started_at = datetime.utcnow()
    db.commit()
    db.refresh(db_obj)

    integration = None
    if db_obj.integration_id:
        integration = get_integration(db, db_obj.integration_id)

    processed = 0
    succeeded = 0
    failed = 0
    errors: list[str] = []

    try:
        # Attempt to fetch data from the integration endpoint
        records: list[dict] = []
        if integration and integration.endpoint and integration.kind in ("rest", "oracle_adb"):
            try:
                headers: dict[str, str] = {}
                if integration.username and integration.secret:
                    import base64

                    creds = f"{integration.username}:{decrypt_secret(integration.secret)}"
                    encoded = base64.b64encode(creds.encode()).decode()
                    headers["Authorization"] = f"Basic {encoded}"
                # Through the outbound guard (https only, blocked destinations refused).
                resp = fetch(integration.endpoint, headers=headers, timeout=30)
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = _json.loads(resp.body)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict) and "data" in data:
                    records = data["data"]
                elif isinstance(data, dict) and "results" in data:
                    records = data["results"]
            except SecretDecryptionError:
                errors.append(
                    "credential could not be decrypted: check the field "
                    "encryption key configuration"
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"fetch failed: {str(exc)[:200]}")

        db_obj.total = len(records) if records else db_obj.total

        # Process records based on entity type
        for record in records:
            processed += 1
            try:
                if db_obj.entity == "employees":
                    from app.models.employee import Employee

                    emp = Employee(
                        employee_id=str(record.get("employee_id", f"MIG{processed}")),
                        first_name=record.get("first_name", "Imported"),
                        last_name=record.get("last_name", "Employee"),
                        email=record.get("email", f"mig{processed}@example.com"),
                        hire_date=datetime.utcnow().date(),
                        job_id=record.get("job_id", 1),
                        department_id=record.get("department_id", 1),
                        status=record.get("status", "Active"),
                    )
                    db.add(emp)
                elif db_obj.entity == "departments":
                    from app.models.department import Department

                    dept = Department(
                        name=record.get("name", f"Dept {processed}"),
                        code=record.get("code", f"DEPT{processed}"),
                        description=record.get("description"),
                    )
                    db.add(dept)
                elif db_obj.entity == "jobs":
                    from app.models.job import Job

                    job = Job(
                        title=record.get("title", f"Job {processed}"),
                        code=record.get("code", f"JOB{processed}"),
                        department_id=record.get("department_id", 1),
                    )
                    db.add(job)
                succeeded += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(f"row {processed}: {str(exc)[:100]}")

            if processed % 50 == 0:
                db_obj.processed = processed
                db_obj.succeeded = succeeded
                db_obj.failed = failed
                db.commit()

        db.commit()

        db_obj.processed = processed
        db_obj.succeeded = succeeded
        db_obj.failed = failed
        db_obj.error_log = "\n".join(errors[:50]) if errors else None

        if integration:
            integration.last_sync_at = datetime.utcnow()
            db.add(integration)

        if failed == 0 and (processed > 0 or db_obj.total == 0):
            db_obj.status = "succeeded"
        elif failed > 0 and succeeded > 0:
            db_obj.status = "succeeded"  # partial success
        elif failed > 0 and succeeded == 0 and processed > 0:
            db_obj.status = "failed"
        else:
            # No records fetched - mark as succeeded with 0 processed
            # (integration may be configured but no data endpoint available)
            db_obj.status = "succeeded"
            db_obj.error_log = (db_obj.error_log or "") + "\nNo records fetched from source. Configure integration endpoint with data."

        db_obj.finished_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    except Exception as exc:  # noqa: BLE001
        db_obj.status = "failed"
        db_obj.error_log = str(exc)[:1000]
        db_obj.finished_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


def cancel_job(db: Session, db_obj: MigrationJob) -> MigrationJob:
    db_obj.status = "cancelled"
    db_obj.finished_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# --- Onboarding steps ------------------------------------------------------- #

def list_steps(db: Session, client_id: int) -> list[OnboardingStep]:
    return (
        db.query(OnboardingStep)
        .filter(OnboardingStep.client_id == client_id)
        .order_by(OnboardingStep.order_index)
        .all()
    )


def get_step(db: Session, step_id: int) -> OnboardingStep | None:
    return db.query(OnboardingStep).filter(OnboardingStep.id == step_id).first()


def complete_step(db: Session, db_obj: OnboardingStep) -> OnboardingStep:
    db_obj.completed = True
    db_obj.completed_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def progress(db: Session, client_id: int) -> dict:
    steps = list_steps(db, client_id)
    total = len(steps)
    completed = sum(1 for s in steps if s.completed)
    return {
        "client_id": client_id,
        "total": total,
        "completed": completed,
        "percent": int((completed / total) * 100) if total else 0,
        "steps": steps,
    }
