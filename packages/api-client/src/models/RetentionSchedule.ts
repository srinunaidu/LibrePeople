/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * How long the records of one entity are kept, and what happens to them afterwards. The schedule is the customer policy; the platform does not impose statutory retention values.
 */
export type RetentionSchedule = {
    entity: string;
    retention_days: number;
    action: RetentionSchedule.action;
    /**
     * While a hold is in place the schedule does not run, whatever it says.
     */
    legal_hold?: boolean;
    updated_at?: string;
    updated_by?: string;
    last_run_at?: string | null;
};
export namespace RetentionSchedule {
    export enum action {
        PURGE = 'purge',
        ANONYMISE = 'anonymise',
        ARCHIVE = 'archive',
    }
}

