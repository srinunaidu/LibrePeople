#!/usr/bin/env python3
"""
Provision Karmathy services on Render via the Render Public API.

Reads secrets from local files (never printed):
  ~/.render/api_key            Render API key            (chmod 600)
  ~/.karmathy/adb_password     Oracle ADB admin password (chmod 600)
  ~/.karmathy/wallet_password  Oracle ADB wallet password (chmod 600, optional)
  <repo>/backend/wallet/       Oracle ADB wallet files

Usage:
  python3 scripts/render_deploy.py            # create + configure + deploy
  python3 scripts/render_deploy.py --dry-run  # show what it would do
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.render.com/v1"
REPO_ROOT = Path(__file__).resolve().parent.parent

KEY_FILE = Path(os.environ.get("RENDER_API_KEY_FILE", Path.home() / ".render" / "api_key"))
ADB_PW_FILE = Path(os.environ.get("ADB_PASSWORD_FILE", Path.home() / ".karmathy" / "adb_password"))
WALLET_PW_FILE = Path(
    os.environ.get("WALLET_PASSWORD_FILE", Path.home() / ".karmathy" / "wallet_password")
)
WALLET_DIR = Path(os.environ.get("WALLET_DIR", REPO_ROOT / "backend" / "wallet"))

REPO = os.environ.get("RENDER_REPO", "https://github.com/srinunaidu/Karmathy")
BRANCH = os.environ.get("RENDER_BRANCH", "main")
REGION = os.environ.get("RENDER_REGION", "singapore")
BACKEND_NAME = os.environ.get("BACKEND_NAME", "karmathy-backend")
FRONTEND_NAME = os.environ.get("FRONTEND_NAME", "karmathy-frontend")
ADB_USER = os.environ.get("ADB_USER", "admin")

WALLET_FILES = [
    # python-oracledb thin mode needs only these text files (mTLS via ewallet.pem).
    # Binary wallet files (cwallet.sso, ewallet.p12, *.jks) are for thick mode /
    # JDBC and can't be stored as plain secret-file content.
    "tnsnames.ora",
    "sqlnet.ora",
    "ewallet.pem",
]

# OCI Object Storage secret files (for STORAGE_BACKEND=oci)
OCI_SECRET_FILES = [
    ("oci_config", None),  # generated from ~/.oci/config
    ("oci_api_key.pem", None),  # copied from ~/.oci/oci_api_key.pem
]

DRY_RUN = "--dry-run" in sys.argv


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def api(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    request.add_header("Authorization", f"Bearer {KEY}")
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:900]
        die(f"HTTP {exc.code} on {method} {path}\n{detail}")


def parse_tnsnames(text: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for block in re.split(r"(?im)^(?=\s*[A-Za-z0-9_]+\s*=)", text):
        m = re.match(r"\s*([A-Za-z0-9_]+)\s*=", block)
        if not m:
            continue
        alias = m.group(1)
        host = re.search(r"host\s*=\s*([^)\s]+)", block, re.I)
        service = re.search(r"service_name\s*=\s*([^)\s]+)", block, re.I)
        entries[alias] = {
            "host": host.group(1) if host else None,
            "service_name": service.group(1) if service else None,
        }
    return entries


def pick_alias(entries: dict[str, dict]) -> str:
    for suffix in ("_high", "_medium", "_low"):
        for alias in entries:
            if alias.endswith(suffix):
                return alias
    if not entries:
        die("No service aliases found in tnsnames.ora")
    return next(iter(entries))


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #
if DRY_RUN:
    print("DRY RUN — no API calls will be made\n")

if not KEY_FILE.exists():
    die(f"Render API key file not found: {KEY_FILE}")
KEY = KEY_FILE.read_text().strip()
if not KEY:
    die(f"Render API key file is empty: {KEY_FILE}")

if not ADB_PW_FILE.exists():
    die(f"ADB password file not found: {ADB_PW_FILE}")
ADB_PASSWORD = ADB_PW_FILE.read_text().strip()
if not ADB_PASSWORD:
    die(f"ADB password file is empty: {ADB_PW_FILE}")

WALLET_PASSWORD = ""
if WALLET_PW_FILE.exists():
    WALLET_PASSWORD = WALLET_PW_FILE.read_text().strip()

tns_candidates = sorted(WALLET_DIR.glob("**/tnsnames.ora"))
if not tns_candidates:
    die(f"tnsnames.ora not found under {WALLET_DIR} — unzip the ADB wallet there first")
tns_file = tns_candidates[0]
wallet_root = tns_file.parent

entries = parse_tnsnames(tns_file.read_text(errors="replace"))
alias = pick_alias(entries)
info = entries[alias]
print(f"Wallet        : {wallet_root}")
print(f"TNS alias     : {alias}")
print(f"ADB host      : {info['host']}")
print(f"Service name  : {info['service_name']}")

# Collect wallet files (searched recursively from the wallet root).
# Render stores secret-file content verbatim as the file bytes, so send text.
secret_files = []
for name in WALLET_FILES:
    for f in wallet_root.glob(f"**/{name}"):
        content = f.read_text(encoding="utf-8", errors="replace")
        secret_files.append({"name": f.name, "content": content})
        print(f"  secret file : {f.name} ({f.stat().st_size} bytes, text)")
if not secret_files:
    die("No wallet files found (expected tnsnames.ora, sqlnet.ora, ewallet.pem)")

# --- OCI Object Storage secret files --------------------------------------- #
OCI_CONFIG_FILE = Path(os.environ.get("OCI_CONFIG_FILE", Path.home() / ".oci" / "config"))
OCI_KEY_FILE = Path(os.environ.get("OCI_KEY_FILE", Path.home() / ".oci" / "oci_api_key.pem"))
OCI_NAMESPACE = os.environ.get("OCI_NAMESPACE", "axkr5pffw199")
OCI_BUCKET_NAME = os.environ.get("OCI_BUCKET_NAME", "karmathy-documents")
OCI_PROFILE = os.environ.get("OCI_PROFILE", "DEFAULT")

oci_secret_files = []
if OCI_CONFIG_FILE.exists() and OCI_KEY_FILE.exists():
    # Read the OCI config and rewrite key_file path for Render's secret files mount
    oci_config_text = OCI_CONFIG_FILE.read_text()
    # Replace the local key_file path with the Render secret files path
    import re as _re
    oci_config_text = _re.sub(
        r"(?m)^key_file\s*=.*$",
        "key_file=/etc/secrets/oci_api_key.pem",
        oci_config_text,
    )
    oci_secret_files.append({"name": "oci_config", "content": oci_config_text})
    oci_secret_files.append({"name": "oci_api_key.pem", "content": OCI_KEY_FILE.read_text()})
    print(f"  secret file : oci_config ({len(oci_config_text)} bytes, text)")
    print(f"  secret file : oci_api_key.pem ({OCI_KEY_FILE.stat().st_size} bytes, text)")

# Combine wallet + OCI secret files
all_secret_files = secret_files + oci_secret_files

# Determine storage backend
storage_backend = "oci" if oci_secret_files else "local"

db_url = None
# Environment for the backend service (password lives only in Render's env vars).
backend_env = [
    {"key": "ORACLE_DSN", "value": alias},
    {"key": "ORACLE_USER", "value": ADB_USER},
    {"key": "ORACLE_PASSWORD", "value": ADB_PASSWORD},
    {"key": "ORACLE_WALLET_DIR", "value": "/etc/secrets"},
    *(
        [{"key": "ORACLE_WALLET_PASSWORD", "value": WALLET_PASSWORD}]
        if WALLET_PASSWORD
        else []
    ),
    {"key": "SECRET_KEY", "generateValue": True},
    {"key": "ALGORITHM", "value": "HS256"},
    {"key": "ACCESS_TOKEN_EXPIRE_MINUTES", "value": "30"},
    {"key": "ENVIRONMENT", "value": "production"},
    {"key": "STORAGE_BACKEND", "value": storage_backend},
    {"key": "RULE_PACK_DIR", "value": "backend/test_fixtures/rule_packs"},
    {"key": "LOCAL_STORAGE_DIR", "value": "/tmp/karmathy-storage"},
    {"key": "ADMIN_INITIAL_USERNAME", "value": "admin"},
    # The bootstrap password is generated by the platform on every deploy
    # and never stored in this repository. Read it from the Render
    # dashboard after the deploy, sign in once, change it immediately, and
    # then remove it from the environment. scripts/seed_admin.py documents
    # the equivalent operator path for other platforms.
    {"key": "ADMIN_INITIAL_PASSWORD", "generateValue": True},
]
if oci_secret_files:
    backend_env.extend([
        {"key": "OCI_NAMESPACE", "value": OCI_NAMESPACE},
        {"key": "OCI_BUCKET_NAME", "value": OCI_BUCKET_NAME},
        {"key": "OCI_CONFIG_FILE", "value": "/etc/secrets/oci_config"},
        {"key": "OCI_PROFILE", "value": OCI_PROFILE},
    ])
print(f"Oracle DSN    : {alias} (user {ADB_USER})")
print(f"Storage       : {storage_backend}")

if DRY_RUN:
    print("Dry run complete.")
    sys.exit(0)

# --------------------------------------------------------------------------- #
# 1. owner / workspace
# --------------------------------------------------------------------------- #
owners = api("GET", "/owners")
owner_id = owners[0]["owner"]["id"]
print(f"Owner ID      : {owner_id}")

existing = {s["service"]["name"]: s["service"] for s in (api("GET", "/services?limit=100") or [])}


def upsert(name: str, body: dict) -> dict:
    if name in existing:
        sid = existing[name]["id"]
        print(f"~ {name} already exists ({sid}) — reusing")
        return existing[name]
    result = api("POST", "/services", body)
    service = result["service"]
    print(f"+ {name} created ({service['id']}) -> {service['serviceDetails'].get('url')}")
    return service


# --------------------------------------------------------------------------- #
# 2. backend web service (Docker)
# --------------------------------------------------------------------------- #
backend = upsert(
    BACKEND_NAME,
    {
        "type": "web_service",
        "name": BACKEND_NAME,
        "ownerId": owner_id,
        "repo": REPO,
        "branch": BRANCH,
        "autoDeployTrigger": "commit",
        "serviceDetails": {
            "runtime": "docker",
            "plan": "free",
            "region": REGION,
            "healthCheckPath": "/health",
            "envSpecificDetails": {
                "dockerfilePath": "./backend/Dockerfile",
                "dockerContext": "./backend",
            },
        },
        "secretFiles": all_secret_files,
        "envVars": backend_env,
    },
)
backend_url = backend["serviceDetails"].get("url") or f"https://{BACKEND_NAME}.onrender.com"
print(f"Backend URL   : {backend_url}")

# --------------------------------------------------------------------------- #
# 3. frontend static site
# --------------------------------------------------------------------------- #
frontend = upsert(
    FRONTEND_NAME,
    {
        "type": "static_site",
        "name": FRONTEND_NAME,
        "ownerId": owner_id,
        "repo": REPO,
        "branch": BRANCH,
        "autoDeployTrigger": "commit",
        "rootDir": "frontend",
        "serviceDetails": {
            "buildCommand": "npm ci && npm run build",
            "publishPath": "./dist",
            "routes": [
                {"type": "rewrite", "source": "/*", "destination": "/index.html"}
            ],
        },
        "envVars": [
            {"key": "VITE_API_URL", "value": f"{backend_url}/api/v1"},
        ],
    },
)
frontend_url = frontend["serviceDetails"].get("url") or f"https://{FRONTEND_NAME}.onrender.com"
print(f"Frontend URL  : {frontend_url}")

# --------------------------------------------------------------------------- #
# 4. finalize env vars now that both URLs are known
# --------------------------------------------------------------------------- #
print("\nSetting final environment variables…")
api(
    "PUT",
    f"/services/{backend['id']}/env-vars",
    backend_env + [{"key": "BACKEND_CORS_ORIGINS", "value": frontend_url}],
)
# Secret files are only set at creation time, so always (re)apply them.
api("PUT", f"/services/{backend['id']}/secret-files", all_secret_files)
print(f"Secret files applied ({len(all_secret_files)})")
api(
    "PUT",
    f"/services/{frontend['id']}/env-vars",
    [{"key": "VITE_API_URL", "value": f"{backend_url}/api/v1"}],
)

# --------------------------------------------------------------------------- #
# 5. trigger deploys
# --------------------------------------------------------------------------- #
for label, service in (("backend", backend), ("frontend", frontend)):
    try:
        api("POST", f"/services/{service['id']}/deploys", {"clearCache": "do_not_clear"})
        print(f"Deploy triggered: {label}")
    except SystemExit:
        print(f"Deploy for {label} may already be in progress")

print(
    f"""
Done.

  Backend  : {backend_url}/health
  API docs : {backend_url}/docs
  Frontend : {frontend_url}

Next: wait for the backend deploy to finish, then seed the admin user from
the Render dashboard Shell for {BACKEND_NAME}:

  python -m scripts.seed_admin
"""
)
