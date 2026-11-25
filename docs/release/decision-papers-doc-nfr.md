# Decision Papers — DOC-003 / NFR-012 / NFR-013 — HEAD a5dea90 (`feature/librepeople-production`)

> Status: RECOMMENDATIONS ONLY. No approval claimed. Owner decision pending per `decision-register.md`.

## DP-1 — DOC-003: Document storage (local + OCI vs S3)

- **Required:** Owner approval of storage backend + matrix scope (Class A blocker).
- **Recommended:** Local filesystem for dev/single-node + OCI Object Storage as primary production backend (S3-compatible API, IAM + bucket policy, versioning + lifecycle, KMS-managed encryption).
- **Alternatives:** (a) S3-direct as primary; (b) local-only; (c) DB BLOB storage. (a) viable if AWS is residency-approved; (b)/(c) rejected for scale/backup reasons.
- **Cost:** OCI egress/storage generally lower; S3 adds cross-cloud transfer if app lives elsewhere. Local cheapest but no durability SLA.
- **Security:** OCI: private buckets, presigned URLs, KMS, audit logs. S3: equivalent via IAM/KMS/CloudTrail. Both need no public buckets + short-lived URLs + virus-scan hook.
- **Ops:** OCI SDK + S3-compat fallback keeps portability; lifecycle → archive tier; backup via versioning + cross-region copy.
- **Compat:** Abstract storage interface so backends swap without app changes; S3-compat keeps migration path open.
- **Reversibility:** HIGH — interface + object-copy migration; reversible before data gravity grows.
- **Deferral:** Can defer backend choice; ship interface + local now, cut over before production data load.
- **Recommendation:** Approve OCI-primary / S3-compat portable; defer only the cutover, not the interface.

## DP-2 — NFR-012: Deployment (Docker + PG vs Cloudflare) + browser matrix + upgrade policy

- **Required:** Owner approvals on deployment target, residency, Cloudflare usage, browser matrix, upgrade cadence.
- **Recommended:** Docker Compose + self-managed PostgreSQL as production baseline (reproducible, residency-clear); Cloudflare optional edge (DNS/CDN/WAF) only if data-residency + DPA approved. Browser matrix: latest 2 Chrome/Edge/Firefox/Safari + explicit mobile decision. Upgrades: pinned images, monthly patch window, tested minor PG upgrades.
- **Alternatives:** (a) Cloudflare-first (Workers/R2/D1); (b) managed PG (RDS/Cloud SQL); (c) K8s. (a) rejected as default without residency approval; (b) acceptable if residency OK; (c) overkill now.
- **Cost:** Docker+PG: infra + ops time, no per-seat edge fees. Cloudflare adds plan + egress-dependent costs.
- **Security:** Baseline: TLS, secrets manager, PG auth + PITR, image scanning. Cloudflare adds WAF/DDoS but expands subprocessor surface — needs DPA.
- **Ops:** Compose + backup/restore runbook + restore rehearsal (ties to all-lost OPEN item); Cloudflare adds tunnel/zero-trust ops.
- **Compat:** Keep app portable (no Workers-only APIs) so Cloudflare stays optional.
- **Reversibility:** MEDIUM — Docker→managed PG easy; Cloudflare-first refactor harder. Keep edge optional to stay reversible.
- **Deferral:** Can defer Cloudflare + K8s; cannot defer browser matrix + upgrade policy (needed for acceptance).
- **Recommendation:** Approve Docker+PG baseline, Cloudflare optional-pending-DPA, proposed browser matrix + monthly upgrades.

## DP-3 — NFR-013: Readiness (foundation vs full packs)

- **Required:** Owner sign-off on what "production-ready" means for initial release.
- **Recommended:** Foundation-gate for initial: hardening (NFR-014 scope), backup/restore rehearsed, perf baseline (NFR-009/010 profile measured), RPO/RTO per-profile approved + tested, all-lost rehearsal done. Full packs (licence review, brand/legal, migration plan, FY26-27 payroll verification) gate GA, not initial.
- **Alternatives:** (a) Full packs before any release; (b) no gates (ship now). (a) delays value; (b) accepts unquantified risk — both not recommended.
- **Cost:** Foundation: rehearsal + perf-run time. Full packs: specialist reviews + payroll-verifier time — deferred cost, not avoided.
- **Security:** Foundation covers backup integrity, quarantine, secrets; full packs add licence/compliance assurance.
- **Ops:** Foundation produces runbooks + rehearsed restore; full packs produce audit artefacts.
- **Compat:** Foundation gates are additive; full-pack criteria layer on without rework.
- **Reversibility:** HIGH — phased gates don't lock scope; deferred items stay in backlog per surplus rule.
- **Deferral:** Explicit: defer full packs post-initial with backlog preserved; do not defer restore rehearsal + RPO/RTO approval.
- **Recommendation:** Approve foundation-gate for initial, full packs as GA gate; record in decision register.
