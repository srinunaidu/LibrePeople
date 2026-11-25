/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The confirmation of an import. The token and the result hash must match the dry run they refer to.
 */
export type ImportCommitRequest = {
    /**
     * The token returned by the dry run.
     */
    confirmation_token: string;
    /**
     * The result hash returned by the dry run.
     */
    result_hash: string;
    /**
     * Optional note stored with the import record.
     */
    comment?: string;
};

