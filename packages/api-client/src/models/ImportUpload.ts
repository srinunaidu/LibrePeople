/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * An uploaded import file, before it is dry run or committed. The upload expires if it is not used.
 */
export type ImportUpload = {
    id: string;
    /**
     * The entity the file targets, for example `employee`.
     */
    entity: string;
    filename: string;
    content_type?: string;
    size_bytes?: number;
    checksum?: string;
    status: ImportUpload.status;
    /**
     * Version of the template the file was validated against.
     */
    template_version?: string;
    uploaded_at: string;
    uploaded_by?: string;
    expires_at?: string;
};
export namespace ImportUpload {
    export enum status {
        UPLOADED = 'uploaded',
        DRY_RUN_COMPLETE = 'dry_run_complete',
        COMMITTED = 'committed',
        REJECTED = 'rejected',
        EXPIRED = 'expired',
    }
}

