/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The parts of a document upload. The `file` part carries the bytes, the other parts carry the metadata.
 */
export type EmployeeDocumentUpload = {
    /**
     * The document. The accepted file types and the size limit are deployment settings, reported by the configuration assistant.
     */
    file: Blob;
    /**
     * Free classification, for example `contract` or `id_proof`.
     */
    category?: string;
    description?: string;
    /**
     * Date the document takes effect from.
     */
    effective_from?: string;
};

