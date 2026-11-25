/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A document attached to an employee. The file itself is not returned by this endpoint; only its metadata.
 */
export type EmployeeDocument = {
    id: string;
    employee_id: string;
    filename: string;
    content_type?: string;
    size_bytes?: number;
    /**
     * Free classification, for example `contract` or `id_proof`.
     */
    category?: string;
    /**
     * SHA-256 of the stored object.
     */
    checksum?: string;
    uploaded_at: string;
    uploaded_by?: string;
};

