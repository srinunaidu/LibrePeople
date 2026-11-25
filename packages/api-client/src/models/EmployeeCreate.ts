/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type EmployeeCreate = {
    /**
     * Optional. When omitted the deployment allocates the next number. A duplicate number returns 409 `duplicate_natural_key`.
     */
    employee_number?: string;
    first_name: string;
    last_name: string;
    email?: string;
    department_id?: string;
    position_id?: string;
    /**
     * Must reference an active employee. A self reference or a cycle returns 422 `validation_error`.
     */
    manager_id?: string;
    location_id?: string;
    status?: EmployeeCreate.status;
    employment_type?: EmployeeCreate.employment_type;
    hire_date: string;
};
export namespace EmployeeCreate {
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

