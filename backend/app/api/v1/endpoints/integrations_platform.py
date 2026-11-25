from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.security import decrypt_secret, encrypt_secret
from app.models.integrations_platform import (
    BackgroundCheck,
    ESignature,
    SSOConfig,
    Webhook,
    WebhookDelivery,
)
from app.models.user import User
from app.schemas.integrations_platform import (
    BackgroundCheckCreate,
    BackgroundCheckOut,
    ESignatureCreate,
    ESignatureOut,
    SSOConfigCreate,
    SSOConfigOut,
    WebhookCreate,
    WebhookDeliveryOut,
    WebhookOut,
)

router = APIRouter()


# --- SSO -------------------------------------------------------------------- #

@router.get("/sso-configs", response_model=list[SSOConfigOut], operation_id="platformListPlatformssoconfigs")
def list_sso(db: Session = Depends(get_db), u: User = Depends(require_roles("SuperAdmin"))):
    return db.query(SSOConfig).order_by(SSOConfig.id.desc()).all()


@router.post("/sso-configs", response_model=SSOConfigOut, status_code=201, operation_id="platformCreatePlatformssoconfigs")
def create_sso(payload: SSOConfigCreate, db: Session = Depends(get_db), u: User = Depends(require_roles("SuperAdmin"))):
    data = payload.model_dump()
    if data.get("client_secret"):
        data["client_secret"] = encrypt_secret(data["client_secret"])
    obj = SSOConfig(**data)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_sso_config", "SSOConfig", obj.id); db.commit()
    return obj


# --- Webhooks --------------------------------------------------------------- #

@router.get("/webhooks", response_model=list[WebhookOut], operation_id="platformListPlatformwebhooks")
def list_webhooks(db: Session = Depends(get_db), u: User = Depends(require_roles("SuperAdmin"))):
    return db.query(Webhook).order_by(Webhook.id.desc()).all()


@router.post("/webhooks", response_model=WebhookOut, status_code=201, operation_id="platformCreatePlatformwebhooks")
def create_webhook(payload: WebhookCreate, db: Session = Depends(get_db), u: User = Depends(require_roles("SuperAdmin"))):
    data = payload.model_dump()
    if data.get("secret"):
        data["secret"] = encrypt_secret(data["secret"])
    obj = Webhook(**data)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_webhook", "Webhook", obj.id); db.commit()
    return obj


@router.get("/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryOut], operation_id="platformListPlatformwebhooksdeliveries")
def list_deliveries(webhook_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles("SuperAdmin"))):
    return db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == webhook_id).order_by(WebhookDelivery.id.desc()).all()


@router.post("/webhooks/{webhook_id}/deliver", response_model=WebhookDeliveryOut, status_code=201, operation_id="platformCreatePlatformwebhooksdeliver")
def deliver_webhook(webhook_id: int, event: str = "test", db: Session = Depends(get_db), u: User = Depends(require_roles("SuperAdmin"))):
    """Deliver a test event to a webhook endpoint (real HTTP POST)."""
    import hashlib
    import hmac
    import json as _json
    from datetime import datetime, timezone

    from app.core.url_guard import fetch

    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    payload = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), "data": {}}
    body = _json.dumps(payload).encode()

    delivery = WebhookDelivery(webhook_id=webhook_id, event=event, payload=body.decode(), status="Pending")
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    # Resolve the signing secret *before* attempting delivery.
    #
    # A secret that cannot be decrypted must not be replaced with an empty
    # string: signing with an empty key would produce a signature the receiver
    # cannot verify, and the delivery would look successful. This raises
    # instead, and the delivery is recorded as failed.
    signature = None
    if webhook.secret:
        from app.core.errors import ErrorCategory, ApiError
        from app.core.security import SecretDecryptionError, decrypt_secret

        try:
            secret = decrypt_secret(webhook.secret)
        except SecretDecryptionError as exc:
            delivery.status = "Failed"
            delivery.attempts = 1
            db.add(delivery)
            db.commit()
            record_audit(
                db,
                u,
                "deliver_webhook_failed",
                "WebhookDelivery",
                delivery.id,
                details="secret_decryption_failed",
            )
            db.commit()
            raise ApiError(
                "secret_decryption_failed",
                "The webhook signing secret could not be decrypted, so the "
                "delivery was not attempted. Check the encryption key "
                "configuration.",
                ErrorCategory.DEPENDENCY,
            ) from exc
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    # Attempt delivery
    try:
        out_headers = {"Content-Type": "application/json"}
        if signature is not None:
            out_headers["X-Webhook-Signature"] = signature
        # Through the outbound guard: https only, blocked destinations refused,
        # every redirect re-validated. A refused URL is a failed delivery.
        resp = fetch(webhook.url, method="POST", headers=out_headers, body=body, timeout=10)
        if resp.status >= 400:
            delivery.status = "Failed"
            delivery.response_code = resp.status
            delivery.attempts = 1
        else:
            delivery.status = "Delivered"
            delivery.response_code = resp.status
            delivery.attempts = 1
    except Exception:
        delivery.status = "Failed"
        delivery.attempts = 1

    webhook.last_triggered_at = datetime.now(timezone.utc)
    db.add(delivery)
    db.add(webhook)
    db.commit()
    db.refresh(delivery)
    record_audit(db, u, "deliver_webhook", "WebhookDelivery", delivery.id, details=event)
    db.commit()
    return delivery


# --- Background checks ------------------------------------------------------ #

@router.get("/background-checks", response_model=list[BackgroundCheckOut], operation_id="platformListPlatformbackgroundchecks")
def list_background_checks(candidate_id: int | None = None, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    q = db.query(BackgroundCheck)
    if candidate_id:
        q = q.filter(BackgroundCheck.candidate_id == candidate_id)
    return q.order_by(BackgroundCheck.id.desc()).all()


@router.post("/background-checks", response_model=BackgroundCheckOut, status_code=201, operation_id="platformCreatePlatformbackgroundchecks")
def create_background_check(payload: BackgroundCheckCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = BackgroundCheck(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_background_check", "BackgroundCheck", obj.id); db.commit()
    return obj


@router.put("/background-checks/{check_id}/complete", response_model=BackgroundCheckOut, operation_id="platformUpdatePlatformbackgroundcheckscomplete")
def complete_background_check(check_id: int, result: str, status: str = "Clear", db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(BackgroundCheck).filter(BackgroundCheck.id == check_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Background check not found")
    obj.status = status
    obj.result = result
    obj.completed_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "complete_background_check", "BackgroundCheck", obj.id); db.commit()
    return obj


# --- E-signatures ----------------------------------------------------------- #

@router.get("/e-signatures", response_model=list[ESignatureOut], operation_id="platformListPlatformesignatures")
def list_signatures(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    return db.query(ESignature).order_by(ESignature.id.desc()).all()


@router.post("/e-signatures", response_model=ESignatureOut, status_code=201, operation_id="platformCreatePlatformesignatures")
def create_signature(payload: ESignatureCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = ESignature(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_e_signature", "ESignature", obj.id); db.commit()
    return obj


@router.put("/e-signatures/{sig_id}/sign", response_model=ESignatureOut, operation_id="platformUpdatePlatformesignaturessign")
def sign_document(sig_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    obj = db.query(ESignature).filter(ESignature.id == sig_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Signature not found")
    obj.status = "Signed"
    obj.signed_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "sign_document", "ESignature", obj.id); db.commit()
    return obj
