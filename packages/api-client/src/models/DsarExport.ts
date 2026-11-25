/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A data subject access export: the whole record the platform holds about one subject, in one file.
 */
export type DsarExport = {
    id: string;
    employee_id?: string | null;
    subject_type: DsarExport.subject_type;
    status: DsarExport.status;
    format?: DsarExport.format;
    requested_at: string;
    completed_at?: string | null;
    /**
     * Short lived URL of the export file.
     */
    download_url?: string | null;
    expires_at?: string | null;
    file_sha256?: string | null;
    job_id?: string | null;
};
export namespace DsarExport {
    export enum subject_type {
        EMPLOYEE = 'employee',
        APPLICANT = 'applicant',
        CONTRACTOR = 'contractor',
    }
    export enum status {
        QUEUED = 'queued',
        BUILDING = 'building',
        READY = 'ready',
        EXPIRED = 'expired',
        FAILED = 'failed',
    }
    export enum format {
        JSON = 'json',
        ZIP = 'zip',
    }
}

