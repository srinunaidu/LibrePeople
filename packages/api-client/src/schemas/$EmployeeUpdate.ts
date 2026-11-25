/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $EmployeeUpdate = {
    description: `Partial update. Changes that affect employment are recorded as effective dated history rows rather than overwriting the record.`,
    properties: {
        first_name: {
            type: 'string',
        },
        last_name: {
            type: 'string',
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
        effective_from: {
            type: 'string',
            description: `Date the change takes effect. Defaults to today.`,
            format: 'date',
        },
        reason: {
            type: 'string',
            description: `Free text reason stored on the history row.`,
            maxLength: 500,
        },
    },
} as const;
