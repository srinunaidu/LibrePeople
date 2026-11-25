/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JobStatus } from './JobStatus';
/**
 * A background job. Jobs report failures with the same code vocabulary as the HTTP API (see `contracts/errors.md` section 6).
 */
export type Job = {
    id: string;
    /**
     * Job type, for example `import_commit` or `payroll_calculate`.
     */
    type: string;
    state: JobStatus;
    attempts: number;
    max_attempts: number;
    created_at: string;
    updated_at: string;
    started_at?: string;
    last_error_at?: string;
    /**
     * A code from the shared code list in `contracts/errors.md`.
     */
    error_code?: string;
    /**
     * Safe to display. Never contains internals.
     */
    error_message?: string;
    payload?: Record<string, any>;
    result?: Record<string, any>;
};

