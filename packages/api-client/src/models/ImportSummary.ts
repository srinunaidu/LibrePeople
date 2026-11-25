/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The record of one import run.
 */
export type ImportSummary = {
    id: string;
    entity: string;
    status: ImportSummary.status;
    counts?: Record<string, any>;
    result_hash?: string | null;
    /**
     * Background job that applied the import.
     */
    job_id?: string | null;
    committed_at?: string | null;
    committed_by?: string | null;
};
export namespace ImportSummary {
    export enum status {
        UPLOADED = 'uploaded',
        DRY_RUN_COMPLETE = 'dry_run_complete',
        COMMITTED = 'committed',
        REJECTED = 'rejected',
        EXPIRED = 'expired',
    }
}

