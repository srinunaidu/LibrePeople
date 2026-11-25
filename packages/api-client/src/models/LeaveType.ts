/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A leave type configured for this deployment.
 */
export type LeaveType = {
    id: string;
    /**
     * Stable code used in imports and exports.
     */
    code: string;
    name: string;
    unit: LeaveType.unit;
    accrual_method?: LeaveType.accrual_method;
    requires_approval?: boolean;
    max_consecutive_days?: number | null;
    active?: boolean;
};
export namespace LeaveType {
    export enum unit {
        DAYS = 'days',
        HOURS = 'hours',
    }
    export enum accrual_method {
        NONE = 'none',
        ANNUAL = 'annual',
        PER_PERIOD = 'per_period',
        SENIORITY = 'seniority',
    }
}

