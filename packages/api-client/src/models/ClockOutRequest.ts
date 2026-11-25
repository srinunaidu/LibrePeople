/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Closes the open working period of the caller, or of `employee_id` when an administrator or manager clocks someone out.
 */
export type ClockOutRequest = {
    employee_id?: string;
    /**
     * Explicit entry to close. Defaults to the open entry of the employee.
     */
    entry_id?: string;
    source?: ClockOutRequest.source;
    notes?: string;
};
export namespace ClockOutRequest {
    export enum source {
        TERMINAL = 'terminal',
        MOBILE = 'mobile',
        MANUAL = 'manual',
        IMPORT = 'import',
        CORRECTION = 'correction',
    }
}

