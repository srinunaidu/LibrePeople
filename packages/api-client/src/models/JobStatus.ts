/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Lifecycle state of a background job. A job that exhausts `max_attempts` moves to `dead` and stays visible in the dead letter view; a dead job is never silently discarded.
 */
export enum JobStatus {
    PENDING = 'pending',
    RUNNING = 'running',
    SUCCEEDED = 'succeeded',
    FAILED = 'failed',
    DEAD = 'dead',
    CANCELLED = 'cancelled',
    DISCARDED = 'discarded',
}
