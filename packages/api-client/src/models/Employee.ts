/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * An employee record of this deployment.
 */
export type Employee = {
    id: string;
    /**
     * Stable business key. Unique inside the deployment.
     */
    employee_number: string;
    first_name: string;
    last_name: string;
    email?: string;
    department_id?: string | null;
    position_id?: string | null;
    manager_id?: string | null;
    location_id?: string | null;
    status: Employee.status;
    employment_type?: Employee.employment_type;
    hire_date?: string;
    termination_date?: string | null;
    created_at?: string;
    updated_at?: string;
};
export namespace Employee {
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

