/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $EmployeeCreate = {
    properties: {
        employee_number: {
            type: 'string',
            description: `Optional. When omitted the deployment allocates the next number. A duplicate number returns 409 \`duplicate_natural_key\`.`,
        },
        first_name: {
            type: 'string',
            isRequired: true,
            minLength: 1,
        },
        last_name: {
            type: 'string',
            isRequired: true,
            minLength: 1,
        },
        email: {
            type: 'string',
            format: 'email',
        },
        department_id: {
            type: 'string',
        },
        position_id: {
            type: 'string',
        },
        manager_id: {
            type: 'string',
            description: `Must reference an active employee. A self reference or a cycle returns 422 \`validation_error\`.`,
        },
        location_id: {
            type: 'string',
        },
        status: {
            type: 'Enum',
        },
        employment_type: {
            type: 'Enum',
        },
        hire_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
    },
} as const;
