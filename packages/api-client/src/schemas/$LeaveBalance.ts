/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $LeaveBalance = {
    description: `The leave balance of one employee for one leave type and one year. Balances are derived from the ledger; the numbers here are the projection at the reporting date.`,
    properties: {
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        leave_type_id: {
            type: 'string',
            isRequired: true,
        },
        leave_type_code: {
            type: 'string',
        },
        year: {
            type: 'number',
            isRequired: true,
        },
        entitled: {
            type: 'number',
            isRequired: true,
        },
        taken: {
            type: 'number',
        },
        pending: {
            type: 'number',
        },
        available: {
            type: 'number',
            isRequired: true,
        },
        as_of: {
            type: 'string',
            description: `Date the balance was computed.`,
            format: 'date',
        },
    },
} as const;
