/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The single error object. Mirrors `contracts/errors.md` section 1; the two must be changed together.
 */
export type Error = {
    /**
     * Stable machine readable identifier. Snake case. Clients branch on this and never on `message`. Renaming a published code is a breaking change.
     */
    code: string;
    /**
     * Drives generic client behaviour (retry, re-authenticate, render a permission state).
     */
    category: Error.category;
    /**
     * Safe to display to a user. No stack traces, no SQL, no hostnames, no record ids that would confirm an object exists. May be reworded at any time, so clients must not parse it.
     */
    message: string;
    /**
     * Whether the identical request may succeed later. True only for `dependency`, `rate_limit` and `internal`.
     */
    retryable: boolean;
    /**
     * Structured, machine readable context. Empty object when there is nothing to add. Must never contain personal data, amounts or identifiers copied from a record.
     */
    details: Record<string, any>;
    /**
     * Correlates the response with the server log line. Echoed in the `X-Request-ID` response header.
     */
    request_id: string;
};
export namespace Error {
    /**
     * Drives generic client behaviour (retry, re-authenticate, render a permission state).
     */
    export enum category {
        VALIDATION = 'validation',
        AUTH = 'auth',
        PERMISSION = 'permission',
        NOT_FOUND = 'not_found',
        CONFLICT = 'conflict',
        CONCURRENCY = 'concurrency',
        DEPENDENCY = 'dependency',
        RATE_LIMIT = 'rate_limit',
        INTERNAL = 'internal',
    }
}

