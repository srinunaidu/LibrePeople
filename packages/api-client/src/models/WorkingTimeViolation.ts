/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A detected breach of the configured working time rules, for example a missing break or a daily maximum overrun.
 */
export type WorkingTimeViolation = {
    id: string;
    employee_id: string;
    work_date: string;
    /**
     * Machine readable violation kind, for example `missing_break` or `max_daily_exceeded`.
     */
    kind: string;
    severity: WorkingTimeViolation.severity;
    /**
     * Minutes involved in the violation.
     */
    minutes?: number;
    detected_at?: string;
    resolved?: boolean;
};
export namespace WorkingTimeViolation {
    export enum severity {
        INFO = 'info',
        WARNING = 'warning',
        CRITICAL = 'critical',
    }
}

