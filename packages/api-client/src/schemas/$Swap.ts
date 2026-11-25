/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Swap = {
    description: `The state of a shift swap.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        roster_entry_id: {
            type: 'string',
        },
        from_employee_id: {
            type: 'string',
        },
        to_employee_id: {
            type: 'string',
        },
        requester_id: {
            type: 'string',
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        violations: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
        decided_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        decided_by: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
