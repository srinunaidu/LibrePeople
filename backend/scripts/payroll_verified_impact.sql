-- ============================================================================
-- Impact query: India pay runs processed while in-standard was read "verified"
-- ============================================================================
--
-- READ-ONLY. This file contains a single SELECT. It does not modify rows and
-- must not be edited into a statement that does. Run it inside a read-only
-- transaction where the database supports one (on PostgreSQL:
--   BEGIN; SET TRANSACTION READ ONLY; <this select>; ROLLBACK;).
--
-- NOT RUN. This file was written for the release gate and has not been
-- executed against any database. It must only be run by an authorised person
-- against a restored or read-only copy, never as part of a deployment.
--
-- What it lists
--   Every pay run whose stored rule_pack_id is 'in-standard', whose jurisdiction
--   is 'IN', and which has left the Draft state (Processing, Approved, Finalized
--   or Paid), or which carries a processed_at timestamp. Each row is joined to
--   the audit row that recorded the processing, if one exists.
--
-- What it cannot prove, and why a reviewer must still check it
--   The pay run does not store the status of the pack at the time it was
--   processed. pay_runs holds rule_pack_id and the run status; audit_logs
--   holds the process_pay_run details, which name the pack id and version and
--   not its status. The status can only be established from the history of
--   backend/rule_packs/in-standard.json (git log, the commit that set
--   status to "verified") compared with processed_at. The rows returned are the
--   candidates. A row is affected only if processed_at falls in the period when
--   the pack's stored status was "verified".
--
-- Columns used (all exist in backend/app/models/payroll.py and audit.py):
--   pay_runs:       id, tenant_id, period_id, jurisdiction, rule_pack_id,
--                   status, processed_by, processed_at, finalized_by,
--                   finalized_at, approved_at, warning, created_at
--   payroll_periods: id, name, pay_date
--   audit_logs:     id, action, entity_type, entity_id, actor_name, details,
--                   created_at
-- ============================================================================

SELECT
    pr.id                 AS pay_run_id,
    pr.tenant_id          AS tenant_id,
    pr.jurisdiction       AS jurisdiction,
    pr.rule_pack_id       AS rule_pack_id,
    pr.status             AS run_status,
    pp.name               AS period_name,
    pp.pay_date           AS pay_date,
    pr.processed_by       AS processed_by,
    pr.processed_at       AS processed_at,
    pr.approved_at        AS approved_at,
    pr.finalized_by       AS finalized_by,
    pr.finalized_at       AS finalized_at,
    pr.created_at         AS run_created_at,
    al.id                 AS audit_id,
    al.action             AS audit_action,
    al.actor_name         AS audit_actor_name,
    al.details            AS audit_details,
    al.created_at         AS audit_created_at
FROM pay_runs pr
JOIN payroll_periods pp
    ON pp.id = pr.period_id
LEFT JOIN audit_logs al
    ON al.entity_type = 'PayRun'
   AND al.entity_id = pr.id
   AND al.action = 'process_pay_run'
WHERE pr.rule_pack_id = 'in-standard'
  AND UPPER(pr.jurisdiction) = 'IN'
  AND (
        pr.status IN ('Processing', 'Approved', 'Finalized', 'Paid')
     OR pr.processed_at IS NOT NULL
  )
ORDER BY pr.processed_at, pr.id, al.id;
