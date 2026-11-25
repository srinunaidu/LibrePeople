/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type HealthCheck = {
    /**
     * Name of the dependency that was probed.
     */
    name: string;
    status: HealthCheck.status;
    /**
     * Safe to display detail. No DSN, no host, no path.
     */
    detail?: string;
};
export namespace HealthCheck {
    export enum status {
        OK = 'ok',
        DEGRADED = 'degraded',
        UNHEALTHY = 'unhealthy',
        SKIPPED = 'skipped',
    }
}

