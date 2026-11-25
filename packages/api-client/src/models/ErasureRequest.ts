/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A request to erase the personal data of one subject. The request is handled by a background job and never removes rows that are under a legal hold.
 */
export type ErasureRequest = {
    id: string;
    employee_id?: string | null;
    subject_type: ErasureRequest.subject_type;
    status: ErasureRequest.status;
    /**
     * The basis the erasure was made under.
     */
    legal_basis?: string | null;
    requested_at: string;
    completed_at?: string | null;
    job_id?: string | null;
};
export namespace ErasureRequest {
    export enum subject_type {
        EMPLOYEE = 'employee',
        APPLICANT = 'applicant',
        CONTRACTOR = 'contractor',
    }
    export enum status {
        OPEN = 'open',
        PROCESSING = 'processing',
        COMPLETED = 'completed',
        REJECTED = 'rejected',
    }
}

