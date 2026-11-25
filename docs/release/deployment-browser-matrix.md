# NFR-012 — Deployment / Browser / Upgrade Matrix (Recommendation only)

Status: PROPOSED — owner approval pending. No owner approvals granted (see `decision-papers-doc-nfr.md` DP-2, `blocker-register.md` LP-NFR-012 BLOCKED Class A). Nothing here authorises Cloudflare, residency, or production cutover.

## 1. Recommended v1 reference: Docker Compose + PostgreSQL 16 on Linux

Self-managed Compose stack per `docker-compose.yml`: `db` on `postgres:16-alpine` with `pgdata` volume and `pg_isready` healthcheck; `backend` built from `backend/Dockerfile` (`python:3.11-slim`, Alembic migrations as release step, `MIGRATE_ON_STARTUP=false`, uvicorn PID 1, port 8000); `frontend` built from `frontend/Dockerfile` (`node:20-alpine` build → `nginx:alpine` serving static `dist/`, port 80). Single Linux host is the reproducible, residency-clear baseline. Managed Postgres (RDS/Cloud SQL) acceptable only if residency approved. K8s out of scope for v1.

## 2. Cloudflare: assess-only + compatibility checklist

Cloudflare (DNS/CDN/WAF/Tunnel) is optional edge only, pending DPA + residency approval. Keep app portable — no Workers-only APIs, no D1/R2 dependency. Before any adoption confirm: backend stateless behind proxy (real-IP, session affinity none); DB unreachable directly, backups/PITR unaffected; background jobs/schedulers run origin-side, no edge cron lock-in; object/file storage origin-owned with signed URLs intact through cache (no private-data caching).

## 3. Browser matrix

Latest two evergreen Chrome, Edge, Firefox, plus current Safari; responsive baseline (desktop + mobile viewport, no horizontal scroll, usable touch targets). No native mobile/desktop apps in v1.

## 4. Upgrade policy

Pinned images, monthly patch window. Each release ships a config-compat report (env/config changes, breaking vs additive) and a migration path (Alembic revision range, backup-before-migrate, rollback to prior image + restore point).
