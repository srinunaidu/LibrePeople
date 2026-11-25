/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A comparison of the computed run against the source data and the previous period, with the variances that need a human look.
 */
export type ReconciliationReport = {
    run_id: string;
    generated_at?: string;
    totals?: Record<string, any>;
    by_component?: Array<Record<string, any>>;
    variances?: Array<{
        /**
         * Machine readable variance kind, for example `headcount_delta`.
         */
        code: string;
        entity?: string | null;
        amount?: number;
        explanation?: string;
    }>;
    checks: Array<{
        name: string;
        passed: boolean;
        detail?: string;
    }>;
};

