/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The payslip of one employee for one run. Amounts are in the run currency and are only final once the run is finalised.
 */
export type Payslip = {
    id: string;
    run_id: string;
    employee_id: string;
    period_id?: string;
    currency?: string;
    gross?: number;
    deductions?: number;
    net?: number;
    lines?: Array<{
        code: string;
        name: string;
        amount: number;
        category?: string;
    }>;
    issued_at?: string | null;
};

