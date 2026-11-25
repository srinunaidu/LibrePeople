# Oracle Autonomous Database Wallet

Place your Oracle ADB wallet files here so the backend can connect with mTLS.

> ⚠️ Everything in this folder except this README is **git-ignored**.
> Never commit wallet files or passwords.

## How to get the wallet

1. Oracle Console → **Oracle Database** → **Autonomous Database** → your instance
2. Click **DB Connection**
3. Click **Download wallet** (optionally set a wallet password)
4. Unzip the wallet into this folder

You should end up with files like:

```
backend/wallet/
  cwallet.sso
  ewallet.p12
  ewallet.pem
  keystore.jks
  ojdbc.properties
  sqlnet.ora
  tnsnames.ora
  truststore.jks
  README
```

## Configuration

Environment variables:

```
ORACLE_WALLET_DIR=/etc/secrets        # Render (secret files mount point)
ORACLE_WALLET_DIR=/app/wallet         # Docker / local
DATABASE_URL=oracle+oracledb://admin:<password>@<tns_alias>
```

Get the **TNS alias** from `tnsnames.ora` (the `_high` entry is usually best),
e.g. `karmkathyadb_high`. With `ORACLE_WALLET_DIR` set, the driver resolves the
alias against the wallet's `tnsnames.ora` and uses TLS/mTLS automatically.

The wallet's `cwallet.sso` enables auto-login, so no `wallet_password` is needed.
