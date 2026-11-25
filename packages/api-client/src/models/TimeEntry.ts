/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single recorded working period.
 */
export type TimeEntry = {
    id: string;
    employee_id: string;
    work_date: string;
    clock_in?: string | null;
    clock_out?: string | null;
    /**
     * Worked minutes, already reduced by breaks.
     */
    minutes: number;
    break_minutes?: number;
    source?: TimeEntry.source;
    status?: TimeEntry.status;
    shift_template_id?: string | null;
};
export namespace TimeEntry {
    export enum source {
        TERMINAL = 'terminal',
        MOBILE = 'mobile',
        MANUAL = 'manual',
        IMPORT = 'import',
        CORRECTION = 'correction',
    }
    export enum status {
        OPEN = 'open',
        COMPLETE = 'complete',
        APPROVED = 'approved',
        REJECTED = 'rejected',
    }
}

