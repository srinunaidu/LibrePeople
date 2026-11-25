/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Partial update. Changes that affect employment are recorded as effective dated history rows rather than overwriting the record.
 */
export type EmployeeUpdate = {
    first_name?: string;
    last_name?: string;
    email?: string;
    department_id?: string;
    position_id?: string;
    manager_id?: string;
    location_id?: string;
    status?: EmployeeUpdate.status;
    employment_type?: EmployeeUpdate.employment_type;
    /**
     * Date the change takes effect. Defaults to today.
     */
    effective_from?: string;
    /**
     * Free text reason stored on the history row.
     */
    reason?: string;
};
export namespace EmployeeUpdate {
    export enum status {
        ACTIVE = 'active',
        ON_LEAVE = 'on_leave',
        SUSPENDED = 'suspended',
        TERMINATED = 'terminated',
    }
    export enum employment_type {
        FULL_TIME = 'full_time',
        PART_TIME = 'part_time',
        CONTRACT = 'contract',
        INTERN = 'intern',
    }
}

