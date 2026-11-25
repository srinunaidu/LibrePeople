/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $LeaveRequestCreate = {
    properties: {
        leave_type_id: {
            type: 'string',
            isRequired: true,
        },
        start_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        end_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        quantity: {
            type: 'number',
            description: `Optional. When omitted the server derives the quantity from the leave calendar of the employee.`,
        },
        reason: {
            type: 'string',
            maxLength: 500,
        },
        half_day: {
            type: 'boolean',
        },
        notes: {
            type: 'string',
            maxLength: 1000,
        },
    },
} as const;
