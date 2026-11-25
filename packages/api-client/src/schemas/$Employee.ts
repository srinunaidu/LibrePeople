/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Employee = {
    description: `An employee record of this deployment.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_number: {
            type: 'string',
            description: `Stable business key. Unique inside the deployment.`,
            isRequired: true,
        },
        first_name: {
            type: 'string',
            isRequired: true,
        },
        last_name: {
            type: 'string',
            isRequired: true,
        },
        email: {
            type: 'string',
            format: 'email',
        },
        department_id: {
            type: 'string',
            isNullable: true,
        },
        position_id: {
            type: 'string',
            isNullable: true,
        },
        manager_id: {
            type: 'string',
            isNullable: true,
        },
        location_id: {
            type: 'string',
            isNullable: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        employment_type: {
            type: 'Enum',
        },
        hire_date: {
            type: 'string',
            format: 'date',
        },
        termination_date: {
            type: 'string',
            isNullable: true,
            format: 'date',
        },
        created_at: {
            type: 'string',
            format: 'date-time',
        },
        updated_at: {
            type: 'string',
            format: 'date-time',
        },
    },
} as const;
