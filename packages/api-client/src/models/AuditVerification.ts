/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The result of walking the audit chain. When the chain is broken the first broken link is reported, with the index it was found at.
 */
export type AuditVerification = {
    verified: boolean;
    checked_entries: number;
    /**
     * Where the chain stopped holding.
     */
    first_broken?: {
        id?: string | null;
        index: number;
        /**
         * Machine readable reason, for example `hash_mismatch` or `missing_predecessor`.
         */
        reason: string;
    } | null;
    verified_at?: string;
};

