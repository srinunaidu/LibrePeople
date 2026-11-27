from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import record_audit
from app.core.tenancy import DEFAULT_TENANT_SLUG, tenant_id_for, tenant_matches
from app.crud import crud_client_onboarding as crud
from app.models.client_onboarding import Client, OnboardingStep
from app.models.user import User
from app.schemas.client_onboarding import (
    ClientSettingCreate,
    ClientSettingOut,
    FeatureFlagOut,
    FeatureFlagUpdate,
    IntegrationCreate,
    IntegrationOut,
    IntegrationUpdate,
    MigrationJobOut,
    MigrationStart,
    OnboardingProgress,
    OnboardingStepCreate,
    OnboardingStepOut,
)

router = APIRouter()


def _scoped_client_or_404(db: Session, client_id: int) -> Any:
    """Load one client, refusing cross-tenant access fail-closed.

    * Unknown id -> 404 (no existence signal beyond the id itself).
    * No resolved tenant -> 401 tenant_unresolvable (never default to a
      real tenant; the legacy ``default`` slug is the only default and it
      is set explicitly by ``resolve_tenant``).
    * Resolved ``default`` tenant -> the legacy global admin view; every
      registry row is visible so existing SuperAdmin tooling keeps working.
    * Any other resolved tenant -> only the row whose ``slug`` matches the
      tenant; anything else -> 403 (fail-closed: the row itself is never
      disclosed, though the 403-vs-404 distinction confirms it exists to a
      caller who is already authorised for the whole registry — every
      endpoint behind this gate is SuperAdmin-only).
    """
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    tenant_id = tenant_id_for(db)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant could not be resolved",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if tenant_id == DEFAULT_TENANT_SLUG:
        return client
    if not tenant_matches(client.slug, tenant_id):
        raise HTTPException(status_code=403, detail="You do not have access to this tenant")
    return client


def _client_or_404(db: Session, client_id: int) -> Any:
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# --- Single company (single-tenant install) ---------------------------------- #


@router.get("/company", operation_id="onboardingPortalGetCompany")
def get_company(db: Session = Depends(get_db)) -> Any:
    """Return the install's single company (public branding subset).

    Single-tenant installs have exactly one org. This replaces the removed
    per-slug lookup and registry list: the frontend resolves the company id
    and branding from here. Field set mirrors the removed public per-slug lookup
    (plus ``id`` and ``currency``), so no additional exposure.
    Deterministic: the lowest-id Client row is the install's company.
    """
    company = db.query(Client).order_by(Client.id.asc()).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {
        "id": company.id,
        "slug": company.slug,
        "name": company.name,
        "primary_color": company.primary_color,
        "secondary_color": company.secondary_color,
        "logo_url": company.logo_url,
        "timezone": company.timezone,
        "locale": company.locale,
        "currency": company.currency,
        "status": company.status,
    }


# --- Tenant lifecycle: REMOVED (single-tenant install) ------------------------- #
# The client registry CRUD, tenant aliases, and the tenant lifecycle FSM
# were removed. Per-install company settings, feature flags, integrations,
# migrations, and onboarding steps below are unchanged.


# --- Settings --------------------------------------------------------------- #

@router.get("/clients/{client_id}/settings", response_model=list[ClientSettingOut], operation_id="onboardingPortalListOnboardingportalclientssettings")
def list_settings(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    return crud.list_settings(db, client_id)


@router.put("/clients/{client_id}/settings/{key}", response_model=ClientSettingOut, operation_id="onboardingPortalUpdateOnboardingportalclientssettings")
def upsert_setting(
    client_id: int,
    key: str,
    payload: ClientSettingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    setting = crud.upsert_setting(db, client_id, key, payload.value)
    record_audit(db, current_user, "upsert_setting", "ClientSetting", setting.id, details=key)
    db.commit()
    return setting


# --- Feature flags ---------------------------------------------------------- #

@router.get("/clients/{client_id}/feature-flags", response_model=list[FeatureFlagOut], operation_id="onboardingPortalListOnboardingportalclientsfeatureflags")
def list_flags(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    return crud.list_flags(db, client_id)


@router.put("/clients/{client_id}/feature-flags/{key}", response_model=FeatureFlagOut, operation_id="onboardingPortalUpdateOnboardingportalclientsfeatureflags")
def update_flag(
    client_id: int,
    key: str,
    payload: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    flag = crud.upsert_flag(db, client_id, key, payload.enabled, payload.config)
    record_audit(db, current_user, "update_feature_flag", "FeatureFlag", flag.id, details=key)
    db.commit()
    return flag


# --- Integrations ----------------------------------------------------------- #

@router.get("/clients/{client_id}/integrations", response_model=list[IntegrationOut], operation_id="onboardingPortalListOnboardingportalclientsintegrations")
def list_integrations(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    integrations = crud.list_integrations(db, client_id)
    out = []
    for i in integrations:
        data = IntegrationOut.from_orm(i) if False else None
        out.append(
            IntegrationOut(
                id=i.id,
                client_id=i.client_id,
                name=i.name,
                kind=i.kind,
                endpoint=i.endpoint,
                username=i.username,
                status=i.status,
                last_tested_at=i.last_tested_at,
                last_sync_at=i.last_sync_at,
                last_error=i.last_error,
                notes=i.notes,
                has_secret=bool(i.secret),
            )
        )
    return out


@router.post("/clients/{client_id}/integrations", response_model=IntegrationOut, status_code=201, operation_id="onboardingPortalCreateOnboardingportalclientsintegrations")
def create_integration(
    client_id: int,
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    integration = crud.create_integration(db, client_id, payload)
    record_audit(db, current_user, "create_integration", "Integration", integration.id)
    db.commit()
    return IntegrationOut(
        id=integration.id,
        client_id=integration.client_id,
        name=integration.name,
        kind=integration.kind,
        endpoint=integration.endpoint,
        username=integration.username,
        status=integration.status,
        last_tested_at=integration.last_tested_at,
        last_sync_at=integration.last_sync_at,
        last_error=integration.last_error,
        notes=integration.notes,
        has_secret=bool(integration.secret),
    )


@router.put("/clients/{client_id}/integrations/{integration_id}", response_model=IntegrationOut, operation_id="onboardingPortalUpdateOnboardingportalclientsintegrations")
def update_integration(
    client_id: int,
    integration_id: int,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    integration = crud.get_integration(db, integration_id)
    if not integration or integration.client_id != client_id:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = crud.update_integration(db, integration, payload)
    record_audit(db, current_user, "update_integration", "Integration", integration.id)
    db.commit()
    return IntegrationOut(
        id=integration.id,
        client_id=integration.client_id,
        name=integration.name,
        kind=integration.kind,
        endpoint=integration.endpoint,
        username=integration.username,
        status=integration.status,
        last_tested_at=integration.last_tested_at,
        last_sync_at=integration.last_sync_at,
        last_error=integration.last_error,
        notes=integration.notes,
        has_secret=bool(integration.secret),
    )


@router.delete("/clients/{client_id}/integrations/{integration_id}", operation_id="onboardingPortalDeleteOnboardingportalclientsintegrations")
def delete_integration(
    client_id: int,
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    integration = crud.get_integration(db, integration_id)
    if not integration or integration.client_id != client_id:
        raise HTTPException(status_code=404, detail="Integration not found")
    crud.delete_integration(db, integration)
    record_audit(db, current_user, "delete_integration", "Integration", integration_id)
    db.commit()
    return {"msg": "deleted"}


@router.post("/clients/{client_id}/integrations/{integration_id}/test", response_model=IntegrationOut, operation_id="onboardingPortalCreateOnboardingportalclientsintegrationstest")
def test_integration(
    client_id: int,
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _scoped_client_or_404(db, client_id)
    integration = crud.get_integration(db, integration_id)
    if not integration or integration.client_id != client_id:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = crud.test_integration(db, integration)
    record_audit(db, current_user, "test_integration", "Integration", integration.id)
    db.commit()
    return IntegrationOut(
        id=integration.id,
        client_id=integration.client_id,
        name=integration.name,
        kind=integration.kind,
        endpoint=integration.endpoint,
        username=integration.username,
        status=integration.status,
        last_tested_at=integration.last_tested_at,
        last_sync_at=integration.last_sync_at,
        last_error=integration.last_error,
        notes=integration.notes,
        has_secret=bool(integration.secret),
    )


# --- Migration jobs --------------------------------------------------------- #

@router.get("/clients/{client_id}/migrations", response_model=list[MigrationJobOut], operation_id="onboardingPortalListOnboardingportalclientsmigrations")
def list_migrations(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    return crud.list_jobs(db, client_id)


@router.post("/clients/{client_id}/migrations", response_model=MigrationJobOut, status_code=201, operation_id="onboardingPortalCreateOnboardingportalclientsmigrations")
def start_migration(
    client_id: int,
    payload: MigrationStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    job = crud.start_job(db, client_id, payload)
    record_audit(db, current_user, "start_migration", "MigrationJob", job.id, details=payload.entity)
    db.commit()
    return job


@router.post("/clients/{client_id}/migrations/{job_id}/run", response_model=MigrationJobOut, operation_id="onboardingPortalCreateOnboardingportalclientsmigrationsrun")
def run_migration(
    client_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    job = crud.get_job(db, job_id)
    if not job or job.client_id != client_id:
        raise HTTPException(status_code=404, detail="Migration job not found")
    job = crud.run_job(db, job)
    record_audit(db, current_user, "run_migration", "MigrationJob", job.id)
    db.commit()
    return job


@router.post("/clients/{client_id}/migrations/{job_id}/cancel", response_model=MigrationJobOut, operation_id="onboardingPortalCreateOnboardingportalclientsmigrationscancel")
def cancel_migration(
    client_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    job = crud.get_job(db, job_id)
    if not job or job.client_id != client_id:
        raise HTTPException(status_code=404, detail="Migration job not found")
    job = crud.cancel_job(db, job)
    record_audit(db, current_user, "cancel_migration", "MigrationJob", job.id)
    db.commit()
    return job


# --- Onboarding steps ------------------------------------------------------- #

@router.get("/clients/{client_id}/onboarding", response_model=OnboardingProgress, operation_id="onboardingPortalGetOnboardingportalclientsonboarding")
def onboarding_progress(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    return crud.progress(db, client_id)


@router.post("/clients/{client_id}/onboarding/steps", response_model=OnboardingStepOut, status_code=201, operation_id="onboardingPortalCreateOnboardingportalclientsonboardingsteps")
def create_step(
    client_id: int,
    payload: OnboardingStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    step = OnboardingStep(client_id=client_id, **payload.model_dump())
    db.add(step)
    db.commit()
    db.refresh(step)
    record_audit(db, current_user, "create_onboarding_step", "OnboardingStep", step.id)
    db.commit()
    return step


@router.post("/clients/{client_id}/onboarding/steps/{step_id}/complete", response_model=OnboardingStepOut, operation_id="onboardingPortalCreateOnboardingportalclientsonboardingstepscomplete")
def complete_step(
    client_id: int,
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    _client_or_404(db, client_id)
    step = crud.get_step(db, step_id)
    if not step or step.client_id != client_id:
        raise HTTPException(status_code=404, detail="Step not found")
    step = crud.complete_step(db, step)
    record_audit(db, current_user, "complete_onboarding_step", "OnboardingStep", step.id)
    db.commit()
    return step


# --- Documentation ---------------------------------------------------------- #

@router.get("/docs/migration-api", operation_id="onboardingPortalGetOnboardingportaldocsmigrationapi")
def migration_api_docs(current_user: User = Depends(require_roles("SuperAdmin"))) -> Any:
    """Serve the migration API connection documentation."""
    from pathlib import Path

    for candidate in (
        Path(__file__).resolve().parents[5] / "docs" / "CLIENT_ONBOARDING.md",
        Path(__file__).resolve().parents[4] / "docs" / "CLIENT_ONBOARDING.md",
        Path(__file__).resolve().parents[3] / "docs" / "CLIENT_ONBOARDING.md",
        Path("/app/docs/CLIENT_ONBOARDING.md"),
    ):
        if candidate.exists():
            return {"content": candidate.read_text()}
    return {"content": "Documentation not found."}
