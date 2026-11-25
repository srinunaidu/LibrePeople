from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import record_audit
from app.core.errors import conflict, forbidden
from app.core.security import decrypt_secret
from app.core.tenancy import DEFAULT_TENANT_SLUG, tenant_id_for, tenant_matches
from app.crud import crud_client_onboarding as crud
from app.models.client_onboarding import Client, OnboardingStep
from app.models.user import User
from app.schemas.client_onboarding import (
    ClientCreate,
    ClientOut,
    ClientSettingCreate,
    ClientSettingOut,
    ClientUpdate,
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


# --- Public tenant lookup (no auth) ---------------------------------------- #


@router.get("/clients/by-slug/{slug}", operation_id="onboardingPortalGetOnboardingportalclientsbyslug")
def get_client_by_slug_public(slug: str, db: Session = Depends(get_db)):
    """Public endpoint: fetch tenant branding by slug (for multi-tenant portals)."""
    client = crud.get_client_by_slug(db, slug)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "slug": client.slug,
        "name": client.name,
        "primary_color": client.primary_color,
        "secondary_color": client.secondary_color,
        "logo_url": client.logo_url,
        "timezone": client.timezone,
        "locale": client.locale,
        "status": client.status,
    }


# --- Clients (admin) -------------------------------------------------------- #


@router.get("/clients", response_model=list[ClientOut], operation_id="onboardingPortalListOnboardingportalclients")
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    return crud.list_clients(db)


@router.post("/clients", response_model=ClientOut, status_code=201, operation_id="onboardingPortalCreateOnboardingportalclients")
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    if crud.get_client_by_slug(db, payload.slug):
        raise HTTPException(status_code=400, detail="Client slug already exists")
    client = crud.create_client(db, payload)
    record_audit(db, current_user, "create_client", "Client", client.id)
    db.commit()
    return client


@router.get("/clients/{client_id}", response_model=ClientOut, operation_id="onboardingPortalGetOnboardingportalclients")
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    return _scoped_client_or_404(db, client_id)


@router.put("/clients/{client_id}", response_model=ClientOut, operation_id="onboardingPortalUpdateOnboardingportalclients")
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    client = _scoped_client_or_404(db, client_id)
    client = crud.update_client(db, client, payload)
    record_audit(db, current_user, "update_client", "Client", client.id)
    db.commit()
    return client


@router.delete("/clients/{client_id}", operation_id="onboardingPortalDeleteOnboardingportalclients")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    client = _scoped_client_or_404(db, client_id)
    crud.delete_client(db, client)
    record_audit(db, current_user, "delete_client", "Client", client_id)
    db.commit()
    return {"msg": "deleted"}


# --- Tenant lifecycle ------------------------------------------------------- #

def _tenant_admin_or_super_admin(db: Session, client: Client, current_user: User) -> None:
    """Allow SuperAdmin for every transition; HR only for their own tenant.

    ``own tenant`` is the tenant resolved from the request's JWT ``tenant``
    claim matching the client's slug. Without a user->client association on
    ``User`` this is the best-effort binding available in B1; SuperAdmin is
    always authoritative.

    ``tenant_id_for`` reads the session value persisted by ``resolve_tenant``,
    because context variables do not cross the thread boundary to the AnyIO
    worker that runs sync endpoints.
    """
    if current_user.role == "SuperAdmin":
        return
    if (
        current_user.role == "HR"
        and tenant_id_for(db)
        and client.slug == tenant_id_for(db)
    ):
        return
    raise forbidden("Your role does not permit this operation.")


def _audit_lifecycle(db, current_user, action, client):
    record_audit(
        db,
        current_user,
        action,
        "Client",
        client.id,
        details=f"slug={client.slug} status={client.status}",
    )
    db.commit()


@router.get("/tenants", response_model=list[ClientOut], operation_id="tenantsListTenants")
def list_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """List every registered tenant (client registry). SuperAdmin only."""
    return crud.list_clients(db)


@router.get(
    "/tenants/{client_id}", response_model=ClientOut, operation_id="tenantsGetTenants"
)
def get_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    return _scoped_client_or_404(db, client_id)


@router.patch(
    "/tenants/{client_id}", response_model=ClientOut, operation_id="tenantsPatchTenants"
)
def update_tenant(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    client = _scoped_client_or_404(db, client_id)
    client = crud.update_client(db, client, payload)
    _audit_lifecycle(db, current_user, "update_tenant", client)
    return client


@router.post(
    "/tenants/{client_id}/provision",
    response_model=ClientOut,
    operation_id="tenantsProvisionTenants",
)
def provision_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """Advance a tenant through provisioning: Draft -> Provisioning -> Active."""
    client = _client_or_404(db, client_id)
    _tenant_admin_or_super_admin(db, client, current_user)
    if client.status == Client.STATUS_DRAFT:
        client.transition_to(Client.STATUS_PROVISIONING, actor=current_user.username)
    elif client.status == Client.STATUS_PROVISIONING:
        client.transition_to(Client.STATUS_ACTIVE, actor=current_user.username)
    # Active is idempotent; anything else is an illegal transition.
    elif client.status != Client.STATUS_ACTIVE:
        raise conflict(
            "invalid_tenant_transition",
            f"Cannot provision a tenant in {client.status} status.",
            details={"from": client.status, "to": Client.STATUS_ACTIVE},
        )
    db.add(client)
    _audit_lifecycle(db, current_user, "provision_tenant", client)
    return client


@router.post(
    "/tenants/{client_id}/suspend",
    response_model=ClientOut,
    operation_id="tenantsSuspendTenants",
)
def suspend_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin", "HR")),
) -> Any:
    """Suspend a tenant: Active -> Suspended. SuperAdmin any tenant; HR own."""
    client = _client_or_404(db, client_id)
    _tenant_admin_or_super_admin(db, client, current_user)
    client.transition_to(Client.STATUS_SUSPENDED, actor=current_user.username)
    db.add(client)
    _audit_lifecycle(db, current_user, "suspend_tenant", client)
    return client


@router.post(
    "/tenants/{client_id}/reactivate",
    response_model=ClientOut,
    operation_id="tenantsReactivateTenants",
)
def reactivate_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin", "HR")),
) -> Any:
    """Reactivate a tenant: Suspended -> Active or Read-only -> Active."""
    client = _client_or_404(db, client_id)
    _tenant_admin_or_super_admin(db, client, current_user)
    if client.status not in (Client.STATUS_SUSPENDED, Client.STATUS_READ_ONLY):
        raise conflict(
            "invalid_tenant_transition",
            f"Cannot reactivate a tenant in {client.status} status.",
            details={"from": client.status, "to": Client.STATUS_ACTIVE},
        )
    client.transition_to(Client.STATUS_ACTIVE, actor=current_user.username)
    db.add(client)
    _audit_lifecycle(db, current_user, "reactivate_tenant", client)
    return client


@router.post(
    "/tenants/{client_id}/read-only",
    response_model=ClientOut,
    operation_id="tenantsReadOnlyTenants",
)
def set_read_only_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """Set a tenant read-only: Active -> Read-only. SuperAdmin only."""
    client = _client_or_404(db, client_id)
    if client.status != Client.STATUS_ACTIVE:
        raise conflict(
            "invalid_tenant_transition",
            f"Cannot set read-only on a tenant in {client.status} status.",
            details={"from": client.status, "to": Client.STATUS_READ_ONLY},
        )
    client.transition_to(Client.STATUS_READ_ONLY, actor=current_user.username)
    db.add(client)
    _audit_lifecycle(db, current_user, "set_read_only_tenant", client)
    return client


@router.post(
    "/tenants/{client_id}/deprovision",
    response_model=ClientOut,
    operation_id="tenantsDeprovisionTenants",
)
def deprovision_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """Deprovision a tenant: Active / Suspended / Read-only -> Deprovisioning."""
    client = _client_or_404(db, client_id)
    if client.status not in (
        Client.STATUS_ACTIVE,
        Client.STATUS_SUSPENDED,
        Client.STATUS_READ_ONLY,
    ):
        raise conflict(
            "invalid_tenant_transition",
            f"Cannot deprovision a tenant in {client.status} status.",
            details={"from": client.status, "to": Client.STATUS_DEPROVISIONING},
        )
    client.transition_to(Client.STATUS_DEPROVISIONING, actor=current_user.username)
    db.add(client)
    _audit_lifecycle(db, current_user, "deprovision_tenant", client)
    return client


@router.post(
    "/tenants/{client_id}/archive",
    response_model=ClientOut,
    operation_id="tenantsArchiveTenants",
)
def archive_tenant(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """Archive a tenant: Deprovisioning -> Archived (terminal). SuperAdmin only."""
    client = _client_or_404(db, client_id)
    if client.status != Client.STATUS_DEPROVISIONING:
        raise conflict(
            "invalid_tenant_transition",
            f"Cannot archive a tenant in {client.status} status.",
            details={"from": client.status, "to": Client.STATUS_ARCHIVED},
        )
    client.transition_to(Client.STATUS_ARCHIVED, actor=current_user.username)
    db.add(client)
    _audit_lifecycle(db, current_user, "archive_tenant", client)
    return client


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
