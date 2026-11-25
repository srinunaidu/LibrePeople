/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Starts a working period. When `employee_id` is omitted the clock in is attributed to the caller.
 */
export type ClockInRequest = {
    /**
     * Only an administrator or manager may clock in on behalf of someone else.
     */
    employee_id?: string;
    location_id?: string;
    source?: ClockInRequest.source;
    device_id?: string;
    notes?: string;
};
export namespace ClockInRequest {
    export enum source {
        TERMINAL = 'terminal',
        MOBILE = 'mobile',
        MANUAL = 'manual',
        IMPORT = 'import',
        CORRECTION = 'correction',
    }
}

