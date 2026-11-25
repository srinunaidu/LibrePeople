-- ==========================================================================
-- Karmathy — Tenant scoping migration (Oracle Autonomous Database)
-- ==========================================================================
--
-- WHY THIS EXISTS
-- ---------------
-- The audit found that no HCM data table carries a tenant/owner column.
-- `users` has no client reference; employees, payroll, leave, time and every
-- other module have no tenant discriminator. Consequence: every authenticated
-- user can read every tenant's data. `/t/:slug/` routing in the frontend is
-- presentation only — it changes branding, not data access.
--
-- This script adds the column and the indexes. It is IDEMPOTENT and does NOT
-- drop or rewrite existing data.
--
-- ROLLOUT ORDER (important — the app must not reference the column until the
-- column exists, or Oracle returns ORA-00904 on every query):
--
--   1. Run this script.                      <- adds columns + indexes
--   2. Deploy application code that reads/writes tenant_id.
--   3. Backfill every tenant_id to the correct client (see step 3 below).
--   4. Verify with scripts/verify_tenant_isolation.py.
--   5. Only then enforce NOT NULL / add the composite unique constraints.
--
-- Until steps 3-5 are done the system is NOT tenant isolated. Do not market
-- it as multi-tenant.
--
-- RUN AS: ADMIN schema owner, connected via mTLS.
-- ==========================================================================

SET SERVEROUTPUT ON

DECLARE
    v_missing  VARCHAR2(4000) := '';
    v_table    VARCHAR2(128);
    v_exists   NUMBER;

    -- Tables that hold tenant-owned HCM data, ordered so that lookup tables
    -- referenced by others are added first (order does not matter for ADD
    -- COLUMN, but it keeps the log readable).
    CURSOR tables IS (
        SELECT table_name FROM user_tables
        ORDER BY table_name
    );
BEGIN
    FOR t IN tables LOOP
        v_table := t.table_name;

        -- Skip the tenancy bookkeeping tables themselves.
        IF v_table IN ('TENANT_MIGRATION_LOG') THEN
            CONTINUE;
        END IF;

        -- Does this table already carry tenant_id?
        SELECT COUNT(*) INTO v_exists
        FROM user_tab_columns
        WHERE table_name = v_table AND column_name = 'TENANT_ID';

        IF v_exists = 0 THEN
            BEGIN
                -- NULLABLE on purpose: adding NOT NULL to a populated table
                -- fails, and step 3 needs to backfill before enforcing.
                EXECUTE IMMEDIATE
                    'ALTER TABLE ' || v_table || ' ADD (tenant_id NUMBER)';
                v_missing := v_missing || v_table || ' ';
                DBMS_OUTPUT.PUT_LINE('added tenant_id to ' || v_table);
            EXCEPTION
                WHEN OTHERS THEN
                    DBMS_OUTPUT.PUT_LINE('SKIP ' || v_table || ' -> ' || SQLERRM);
            END;
        END IF;
    END LOOP;

    DBMS_OUTPUT.PUT_LINE('---');
    DBMS_OUTPUT.PUT_LINE('tables updated: ' || v_missing);
END;
/

-- --------------------------------------------------------------------------
-- users.tenant_id references clients.id so a login resolves to exactly one
-- tenant. Without it there is no way to scope anything.
-- --------------------------------------------------------------------------
DECLARE
    v_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_exists
    FROM user_tab_columns
    WHERE table_name = 'USERS' AND column_name = 'TENANT_ID';

    IF v_exists = 0 THEN
        BEGIN
            EXECUTE IMMEDIATE 'ALTER TABLE users ADD (tenant_id NUMBER)';
            DBMS_OUTPUT.PUT_LINE('added users.tenant_id');
        EXCEPTION WHEN OTHERS THEN
            DBMS_OUTPUT.PUT_LINE('users.tenant_id -> ' || SQLERRM);
        END;
    END IF;

    SELECT COUNT(*) INTO v_exists
    FROM user_constraints
    WHERE constraint_name = 'fk_users_tenant';

    IF v_exists = 0 THEN
        BEGIN
            EXECUTE IMMEDIATE
                'ALTER TABLE users ADD CONSTRAINT fk_users_tenant '
                || 'FOREIGN KEY (tenant_id) REFERENCES clients(id)';
            DBMS_OUTPUT.PUT_LINE('added fk_users_tenant');
        EXCEPTION WHEN OTHERS THEN
            DBMS_OUTPUT.PUT_LINE('fk_users_tenant -> ' || SQLERRM);
        END;
    END IF;
END;
/

-- --------------------------------------------------------------------------
-- Indexes on tenant_id so every scoped query has a supporting index.
-- --------------------------------------------------------------------------
DECLARE
    v_idx VARCHAR2(30);
    CURSOR c IS
        SELECT table_name FROM user_tables ORDER BY table_name;
BEGIN
    FOR t IN c LOOP
        -- Keeps the identifier inside the 30-byte Oracle limit:
        -- 'ix_' (3) + 20 + '_t' (2) = 25.
        v_idx := 'ix_' || SUBSTR(t.table_name, 1, 20) || '_t';
        BEGIN
            EXECUTE IMMEDIATE
                'CREATE INDEX ' || v_idx || ' ON ' || t.table_name || ' (tenant_id)';
            DBMS_OUTPUT.PUT_LINE('created ' || v_idx);
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE = -955 THEN
                    NULL; -- ORA-00955: name already used by an existing object
                ELSE
                    DBMS_OUTPUT.PUT_LINE('idx ' || v_idx || ' -> ' || SQLERRM);
                END IF;
        END;
    END LOOP;
END;
/
/

-- --------------------------------------------------------------------------
-- Readiness report: which tenant-owned tables still have NULL tenant_id.
-- Every non-zero count is unfinished backfill work (step 3).
--
-- Oracle has no CROSS APPLY, so this walks the dictionary and prints one line
-- per table that still needs a backfill.
-- --------------------------------------------------------------------------
DECLARE
    v_total NUMBER;
    v_nulls NUMBER;
    CURSOR c IS
        SELECT table_name FROM user_tables ORDER BY table_name;
BEGIN
    FOR t IN c LOOP
        BEGIN
            EXECUTE IMMEDIATE
                'SELECT COUNT(*), COUNT(CASE WHEN tenant_id IS NULL THEN 1 END) FROM '
                || t.table_name
                INTO v_total, v_nulls;

            IF v_nulls > 0 THEN
                DBMS_OUTPUT.PUT_LINE(
                    RPad(t.table_name, 34) || ' nulls=' || v_nulls
                    || '/' || v_total || '  <-- needs backfill'
                );
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                NULL; -- table has no tenant_id column; nothing to backfill
        END;
    END LOOP;
END;
/

-- Practical per-table alternative for an operator:
--   SELECT COUNT(*) FROM employees WHERE tenant_id IS NULL;
--   -- CONFIRM the correct client id before running:
--   UPDATE employees SET tenant_id = 1 WHERE tenant_id IS NULL;
--   COMMIT;

DBMS_OUTPUT.PUT_LINE('--- migration script finished ---');