/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A manual correction of a recorded working period. A correction is never applied directly: it is recorded as a pending request and the entry keeps its original value until a manager approves it.
 */
export type EntryCorrectionRequest = {
    work_date?: string;
    clock_in?: string;
    clock_out?: string;
    /**
     * Total worked minutes after correction.
     */
    minutes?: number;
    /**
     * Why the correction is needed. Stored on the audit trail.
     */
    reason: string;
};

