/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $LeaveRequest = {
    description: `A leave request and its decision state.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
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
        },
        unit: {
            type: 'Enum',
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        reason: {
            type: 'string',
            isNullable: true,
        },
        created_at: {
            type: 'string',
            format: 'date-time',
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
        decision_note: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
