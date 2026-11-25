/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The parts of an import upload. The `file` part carries the bytes, the other parts carry the metadata.
 */
export type ImportUploadRequest = {
    /**
     * The CSV file to import.
     */
    file: Blob;
    /**
     * The entity the file targets, for example `employee`. When it is omitted the server derives it from the headers of the file.
     */
    entity?: string;
    /**
     * The version of the template the caller built the file from. It is reported back on the upload so a mismatch can be spotted.
     */
    template_version?: string;
    /**
     * Validate the file as soon as it is uploaded instead of waiting for an explicit dry run.
     */
    dry_run?: boolean;
};

