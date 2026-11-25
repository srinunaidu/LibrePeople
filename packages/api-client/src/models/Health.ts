/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthCheck } from './HealthCheck';
/**
 * Deployment health. The deployment holds exactly one customer's data in exactly one Oracle schema; the health probe never reveals the schema name or the DSN.
 */
export type Health = {
    status: Health.status;
    /**
     * Running application version.
     */
    version: string;
    checks?: Array<HealthCheck>;
};
export namespace Health {
    export enum status {
        OK = 'ok',
        DEGRADED = 'degraded',
        UNHEALTHY = 'unhealthy',
    }
}

