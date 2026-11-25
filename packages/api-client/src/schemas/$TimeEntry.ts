/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TimeEntry = {
    description: `A single recorded working period.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        work_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        clock_in: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        clock_out: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        minutes: {
            type: 'number',
            description: `Worked minutes, already reduced by breaks.`,
            isRequired: true,
        },
        break_minutes: {
            type: 'number',
        },
        source: {
            type: 'Enum',
        },
        status: {
            type: 'Enum',
        },
        shift_template_id: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
