/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One payroll run. A run moves `draft` to `calculated` to `approved` to `finalised`; a finalised run can no longer be edited and returns 409 `pay_run_already_finalised`.
 */
export type PayRun = {
    id: string;
    period_id?: string;
    status: PayRun.status;
    /**
     * Jurisdiction whose rule pack applies to this run. The run may not be calculated unless the pack for this jurisdiction is `verified`.
     */
    jurisdiction: string;
    rule_pack_id?: string | null;
    employee_count?: number;
    currency?: string;
    /**
     * Aggregates of the run. Amounts are in the run currency.
     */
    totals?: Record<string, any>;
    calculated_at?: string | null;
    approved_at?: string | null;
    approved_by?: string | null;
    finalised_at?: string | null;
};
export namespace PayRun {
    export enum status {
        DRAFT = 'draft',
        CALCULATED = 'calculated',
        APPROVED = 'approved',
        FINALISED = 'finalised',
    }
}

