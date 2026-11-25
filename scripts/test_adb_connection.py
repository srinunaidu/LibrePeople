#!/usr/bin/env python3
"""
Test the Oracle Autonomous Database connection using the local wallet.

Reads the password from a file; never prints secrets.

  ADB_PASSWORD_FILE=~/.karmathy/adb_password
  WALLET_DIR=<repo>/backend/wallet
  ADB_USER=admin
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WALLET_DIR = Path(os.environ.get("WALLET_DIR", REPO_ROOT / "backend" / "wallet"))
PW_FILE = Path(os.environ.get("ADB_PASSWORD_FILE", Path.home() / ".karmathy" / "adb_password"))
WALLET_PW_FILE = Path(
    os.environ.get("WALLET_PASSWORD_FILE", Path.home() / ".karmathy" / "wallet_password")
)
USER = os.environ.get("ADB_USER", "admin")

try:
    import oracledb
except ImportError:
    sys.exit("oracledb not installed. Run: pip install oracledb")

tns = next(WALLET_DIR.glob("**/tnsnames.ora"), None)
if not tns:
    sys.exit(f"tnsnames.ora not found under {WALLET_DIR}")
wallet_root = tns.parent

text = tns.read_text(errors="replace")
aliases = re.findall(r"(?im)^\s*([A-Za-z0-9_]+)\s*=", text)
if not aliases:
    sys.exit("No TNS aliases found")
alias = next((a for a in aliases if a.endswith("_high")), aliases[0])

if not PW_FILE.exists():
    sys.exit(f"Password file not found: {PW_FILE}")
password = PW_FILE.read_text().strip()

wallet_password = None
if WALLET_PW_FILE.exists():
    wallet_password = WALLET_PW_FILE.read_text().strip() or None

print(f"driver      : oracledb {oracledb.__version__} (thin={oracledb.is_thin_mode()})")
print(f"alias       : {alias}")
print(f"wallet      : {wallet_root}")
print(f"user        : {USER}")
print(f"password    : {len(password)} characters (value not shown)")
print(f"wallet pw   : {'set' if wallet_password else 'not set'}")
print("-" * 50)

try:
    conn = oracledb.connect(
        user=USER,
        password=password,
        dsn=alias,
        config_dir=str(wallet_root),
        wallet_location=str(wallet_root),
        wallet_password=wallet_password,
    )
except Exception as exc:  # noqa: BLE001
    print(f"CONNECTION FAILED: {type(exc).__name__}")
    print(str(exc)[:500])
    sys.exit(1)

cur = conn.cursor()
cur.execute("SELECT banner FROM v$version FETCH FIRST 1 ROWS ONLY")
print("connected   : OK")
print("version     :", cur.fetchone()[0][:80])
cur.execute("SELECT COUNT(*) FROM user_tables")
print("user_tables :", cur.fetchone()[0])
conn.close()
print("\nADB connection works.")
