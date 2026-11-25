/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One immutable movement of a leave balance. The ledger is the audit trail of the balance; the balance itself is a projection of it.
 */
export type LeaveLedgerEntry = {
    id: string;
    employee_id: string;
    leave_type_id: string;
    effective_date: string;
    direction: LeaveLedgerEntry.direction;
    /**
     * Always positive. The `direction` gives the sign.
     */
    quantity: number;
    reason?: string | null;
    source?: LeaveLedgerEntry.source;
    /**
     * The leave request that caused the movement, when there was one.
     */
    request_id?: string | null;
    /**
     * Balance after this movement was applied.
     */
    running_balance?: number;
};
export namespace LeaveLedgerEntry {
    export enum direction {
        ACCRUAL = 'accrual',
        USAGE = 'usage',
        ADJUSTMENT = 'adjustment',
        CARRY_FORWARD = 'carry_forward',
        EXPIRY = 'expiry',
    }
    export enum source {
        POLICY = 'policy',
        REQUEST = 'request',
        MANUAL = 'manual',
        IMPORT = 'import',
        PAYROLL = 'payroll',
    }
}

